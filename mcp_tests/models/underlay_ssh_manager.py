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

from devops.helpers.ssh_client import SSHClient
from paramiko import rsakey


class UnderlaySSHManager(object):
    """Keep the list of SSH access credentials to Underlay nodes.

       This object is initialized using config.underlay.ssh.

       :param config_ssh: JSONList of SSH access credentials for nodes:
          [
            {
              node_name: node1,
              address_pool: 'public-pool01',
              host: ,
              port: ,
              keys: [],
              keys_source_host: None,
              login: ,
              password: ,
            },
            {
              node_name: node1,
              address_pool: 'private-pool01',
              host:
              port:
              keys: []
              keys_source_host: None,
              login:
              password:
            },
            {
              node_name: node2,
              address_pool: 'public-pool01',
              keys_source_host: node1
              ...
            }
            ,
            ...
          ]

       self.node_names(): list of node names registered in underlay.
       self.remote(): SSHClient object by a node name (w/wo address pool)
                      or by a hostname.
    """

    config_ssh = None

    def __init__(self, config_ssh):
        """Read config.underlay.ssh object

           Required params:
           :param node_name: string
           :param host: string
           :param login: string
           :param password: string

           Optional params:
           :param address_pool: string or None
           :param port: string or None
           :param keys: list or None
           :param keys_source_host: string or None
        """
        if config_ssh is None:
            config_ssh = []

        if self.config_ssh is None:
            self.config_ssh = []

        for ssh in config_ssh:
            ssh_data = {
                'node_name': ssh['node_name'],
                'address_pool': (ssh['address_pool'] if 'address_pool' in ssh
                                 else None),
                'host': ssh['host'],
                'port': ssh['port'] if 'port' in ssh else None,
                'keys': ssh['keys'] if 'keys' in ssh else [],
                'login': ssh['login'],
                'password': ssh['password'],
            }

            if 'keys_source_host' in ssh:
                node_name = ssh['keys_source_host']
                remote = self.remote(node_name)
                keys = self.__get_keys(remote)
                ssh_data['keys'].extend(keys)

            self.config_ssh.append(ssh_data)

    def __get_keys(self, remote):
        keys = []
        key_string = '/root/.ssh/id_rsa'
        with remote.open(key_string) as f:
            keys.append(rsakey.RSAKey.from_private_key(f))
        return keys

    def __ssh_data(self, node_name=None, host=None, address_pool=None):

        ssh_data = None

        if host is not None:
            for ssh in self.config_ssh:
                if host == ssh['host']:
                    ssh_data = ssh
                    break

        elif node_name is not None:
            for ssh in self.config_ssh:
                if node_name == ssh['node_name']:
                    if address_pool is not None:
                        if address_pool == ssh['address_pool']:
                            ssh_data = ssh
                            break
                    else:
                        ssh_data = ssh
        if ssh_data is None:
            raise Exception('Auth data for node was not found using '
                            'node_name="{}" , host="{}" , address_pool="{}"'
                            .format(node_name, host, address_pool))
        return ssh_data

    def node_names(self):
        """Get list of node names registered in config.underlay.ssh"""

        names = []  # List is used to keep the original order of names
        for ssh in self.config_ssh:
            if ssh['node_name'] not in names:
                names.append(ssh['node_name'])
        return names

    def host_by_node_name(self, node_name, address_pool=None):
        ssh_data = self.__ssh_data(node_name=node_name,
                                   address_pool=address_pool)
        return ssh_data['host']

    def remote(self, node_name=None, host=None, address_pool=None):
        """Get SSHClient by a node name or hostname.

           One of the following arguments should be specified:
           - host (str): IP address or hostname. If specified, 'node_name' is
                         ignored.
           - node_name (str): Name of the node stored to config.underlay.ssh
                              If no address_pool specified, use the first
                              matched name.
        """
        ssh_data = self.__ssh_data(node_name=node_name, host=host,
                                   address_pool=address_pool)
        return SSHClient(
            host=ssh_data['host'],
            port=ssh_data['port'] or 22,
            username=ssh_data['login'],
            password=ssh_data['password'],
            private_keys=ssh_data['keys'])

    def check_call(
            self, cmd,
            node_name=None, host=None, address_pool=None,
            verbose=False, timeout=None,
            error_info=None,
            expected=None, raise_on_err=True):
        """Execute command on the node_name/host and check for exit code

        :type cmd: str
        :type verbose: bool
        :type timeout: int
        :type error_info: str
        :type expected: list
        :type raise_on_err: bool
        :rtype: ExecResult
        :raises: DevopsCalledProcessError
        """
        remote = self.remote(node_name=node_name, host=host,
                             address_pool=address_pool)
        remote.check_call(command=cmd, verbose=verbose, timeout=timeout,
                          error_info=error_info, expected=expected,
                          raise_on_err=raise_on_err)

    def sudo_check_call(
            self, cmd,
            node_name=None, host=None, address_pool=None,
            verbose=False, timeout=None,
            error_info=None,
            expected=None, raise_on_err=True):
        """Execute command with sudo on node_name/host and check for exit code

        :type cmd: str
        :type verbose: bool
        :type timeout: int
        :type error_info: str
        :type expected: list
        :type raise_on_err: bool
        :rtype: ExecResult
        :raises: DevopsCalledProcessError
        """
        remote = self.remote(node_name=node_name, host=host,
                             address_pool=address_pool)
        with remote.get_sudo(remote):
            remote.check_call(command=cmd, verbose=verbose, timeout=timeout,
                              error_info=error_info, expected=expected,
                              raise_on_err=raise_on_err)
