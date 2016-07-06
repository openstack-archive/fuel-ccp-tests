#    Copyright 2016 Mirantis, Inc.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from devops import models
from django import db

from mcp_tests.helpers import ext
from mcp_tests.helpers import mcp_tests_exceptions as exc
from mcp_tests import logger
from mcp_tests.models import manager


LOG = logger.logger


class EnvironmentManager(manager.Manager):
    """Class-helper for creating VMs via devops environments"""
    def __init__(self, config_file=None, env_name=None, master_image=None,
                 node_image=None, *args, **kwargs):
        """Initializing class instance

        :param env_name: environment name string
        :param master_image: path to master image string
        :param node_image: path to node image string
        """
        super(EnvironmentManager, self).__init__(*args, **kwargs)
        self.config_file = config_file
        self.env_name = env_name
        self.master_image = master_image
        self.node_image = node_image

    def merge_config_params(self):
        """Merging config with instance defined params"""
        if self.devops_config.config is None:
            raise exc.DevopsConfigIsNone
        conf = self.devops_config
        node_group = conf['groups'][0]
        if self.env_name is not None:
            conf.set_value_by_keypath('env_name', self.env_name)
            LOG.debug('env_name redefined to {0}'.format(self.env_name))
        if self.master_image is not None or self.node_image is not None:
            LOG.debug('Current node_group settings:\n{0}'.format(
                node_group))

            for node in node_group['nodes']:
                volume = node['params']['volumes'][0]
                if (node['role'] == ext.NODE_ROLE.master and
                        self.master_image is not None):
                    volume['source_image'] = self.master_image
                elif (node['role'] == ext.NODE_ROLE.slave and
                      self.node_image is not None):
                    volume['source_image'] = self.node_image

            conf.set_value_by_keypath('group[0]', node_group)
            LOG.debug('Node group updated to:\n{0}'.format(node_group))

    @property
    def d_env_name(self):
        """Get environment name from fuel devops config

        :rtype: string
        """
        return self.devops_config['env_name']

    def get_env_by_name(self, name):
        """Set existing environment by name

        :param name: string
        """
        self._env = models.Environment.get(name=name)

    def create_snapshot(self, name):
        """Create named snapshot of current env.

        :name: string
        """
        LOG.info("Creating snapshot named '{0}'".format(name))
        if self._env is not None:
            self._env.snapshot(name, force=True)
        else:
            raise exc.EnvironmentIsNotSet()

    def revert_snapshot(self, name):
        """Revert snapshot by name

        :param name: string
        """
        LOG.info("Reverting from snapshot named '{0}'".format(name))
        if self._env is not None:
            self._env.revert(name=name)
        else:
            raise exc.EnvironmentIsNotSet()

    def create_environment(self):
        """Create environment and start VMs.

        If config was provided earlier, we simply create and start VMs,
        otherwise we tries to generate config from self.config_file,
        """
        if self.devops_config.config is None:
            LOG.debug('Seems config for fuel-devops is not set.')
            if self.config_file is None:
                raise exc.DevopsConfigPathIsNotSet()
            self.devops_config.load_template(self.config_file)
        self.merge_config_params()
        settings = self.devops_config
        env_name = settings['env_name']
        LOG.debug(
            'Preparing to create environment named "{0}"'.format(env_name)
        )
        if env_name is None:
            LOG.error('Environment name is not set!')
            raise exc.EnvironmentNameIsNotSet()
        try:
            self._env = models.Environment.create_environment(
                settings.config
            )
        except db.IntegrityError:
            LOG.error(
                'Seems like environment {0} already exists.'.format(env_name)
            )
            raise exc.EnvironmentAlreadyExists(env_name)
        self._env.define()
        self.start_environment()
        LOG.info(
            'Environment "{0}" created and started'.format(env_name)
        )

    def start_environment(self):
        """Method for start environment

        """
        if self._env is None:
            raise exc.EnvironmentIsNotSet()
        self._env.start()

    def resume(self):
        """Resume environment"""
        if self._env is None:
            raise exc.EnvironmentIsNotSet()
        self._env.resume()

    def suspend(self):
        """Suspend environment"""
        if self._env is None:
            raise exc.EnvironmentIsNotSet()
        self._env.suspend()

    def stop(self):
        """Stop environment"""
        if self._env is None:
            raise exc.EnvironmentIsNotSet()
        self._env.destroy()

    def has_snapshot(self, name):
        return self._env.has_snapshot(name)

    def delete_environment(self):
        """Delete environment

        """
        LOG.debug("Deleting environment")
        self._env.erase()

    def __get_nodes_by_role(self, node_role):
        """Get node by given role name

        :param node_role: string
        :rtype: devops.models.Node
        """
        LOG.debug('Trying to get nodes by role {0}'.format(node_role))
        return self._env.get_nodes(role=node_role)

    @property
    def master_nodes(self):
        """Get all master nodes

        :rtype: list
        """
        nodes = self.__get_nodes_by_role(node_role=ext.NODE_ROLE.master)
        return nodes

    @property
    def slave_nodes(self):
        """Get all slave nodes

        :rtype: list
        """
        nodes = self.__get_nodes_by_role(node_role=ext.NODE_ROLE.slave)
        return nodes

    @property
    def k8s_nodes(self):
        """Get all k8s nodes

        :rtype: list
        """
        nodes = self.__get_nodes_by_role(node_role=ext.NODE_ROLE.k8s)
        return nodes

    @staticmethod
    def node_ip(node):
        """Determine node's IP

        :param node: devops.models.Node
        :return: string
        """
        LOG.debug('Trying to determine {0} ip.'.format(node.name))
        return node.get_ip_address_by_network_name(
            ext.NETWORK_TYPE.public
        )

    @property
    def admin_ips(self):
        """Property to get ip of admin role VMs

        :return: list
        """
        nodes = self.master_nodes
        return [self.node_ip(node) for node in nodes]

    @property
    def slave_ips(self):
        """Property to get ip(s) of slave role VMs

        :return: list
        """
        nodes = self.slave_nodes
        return [self.node_ip(node) for node in nodes]

    @property
    def k8s_ips(self):
        """Property to get ip(s) of k8s role VMs

        :return: list
        """
        nodes = self.k8s_nodes
        return [self.node_ip(node) for node in nodes]

    @staticmethod
    def node_ssh_client(node, login, password=None, private_keys=None):
        """Return SSHClient for node

        :param node: devops.models.Node
        :param login: string
        :param password: string
        :param private_keys: list
        :rtype: devops.helpers.helpers.SSHClient
        """
        LOG.debug(
            'Creating ssh client for node "{0}"'.format(node.name)
        )
        LOG.debug(
            'Using credentials: login:{0}, password:{1}, keys:{2}'.format(
                login, password, private_keys
            )
        )
        return node.remote(
            network_name=ext.NETWORK_TYPE.public,
            login=login,
            password=password,
            private_keys=private_keys
        )

    @staticmethod
    def send_to_node(node, source, target, login,
                     password=None, private_keys=None):
        """Method for sending some stuff to node

        :param node: devops.models.Node
        :param source: string
        :param target: string
        :param login: string
        :param password: string
        :param private_keys: list
        """
        LOG.debug(
            "Send '{0}' to node '{1}' into target '{2}'.".format(
                source,
                node.name,
                target
            )
        )
        remote = EnvironmentManager.node_ssh_client(
            node=node,
            login=login,
            password=password,
            private_keys=private_keys
        )
        remote.upload(source=source, target=target)

    def send_to_master_nodes(self, source, target, login,
                             password=None, private_keys=None):
        """Send given source to master nodes"""
        nodes = self.master_nodes
        for node in nodes:
            self.send_to_node(
                node,
                source=source, target=target, login=login,
                password=password, private_keys=private_keys
            )

    def send_to_slave_nodes(self, source, target, login,
                            password=None, private_keys=None):
        """Send given source to slave nodes"""
        nodes = self.slave_nodes
        for node in nodes:
            self.send_to_node(
                node,
                source=source, target=target, login=login,
                password=password, private_keys=private_keys
            )

    def send_to_k8s_nodes(self, source, target, login,
                          password=None, private_keys=None):
        """Send given source to slave nodes"""
        nodes = self.k8s_nodes
        for node in nodes:
            self.send_to_node(
                node,
                source=source, target=target, login=login,
                password=password, private_keys=private_keys
            )
