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

from fuel_ccp_tests import logger
from fuel_ccp_tests import settings


LOG = logger.logger


class RallyManager(object):
    """docstring for RallyManager"""

    image_name = 'rallyforge/rally'
    image_version = '0.5.0'

    def __init__(self, underlay, admin_node_name):
        super(RallyManager, self).__init__()
        self._admin_node_name = admin_node_name
        self._underlay = underlay

    def prepare(self):
        content = """
sed -i 's|#swift_operator_role = Member|swift_operator_role=SwiftOperator|g' /etc/rally/rally.conf  # noqa
source /home/rally/openrc
rally-manage db recreate
rally deployment create --fromenv --name=tempest
rally verify install
rally verify genconfig
rally verify showconfig"""
        cmd = "cat > {path} << EOF\n{content}\nEOF".format(
            path='/home/{user}/rally/install_tempest.sh'.format(
                user=settings.SSH_LOGIN), content=content)
        cmd1 = "chmod +x /home/{user}/rally/install_tempest.sh".format(
            user=settings.SSH_LOGIN)
        cmd2 = "cp /home/{user}/openrc-* /home/{user}/rally/openrc".format(
            user=settings.SSH_LOGIN)

        with self._underlay.remote(node_name=self._admin_node_name) as remote:
            LOG.info("Create rally workdir")
            remote.check_call('mkdir -p /home/{user}/rally'.format(
                user=settings.SSH_LOGIN))
            LOG.info("Create install_tempest.sh")
            remote.check_call(cmd)
            LOG.info("Chmod +x install_tempest.sh")
            remote.check_call(cmd1)
            LOG.info("Copy openstackrc")
            remote.check_call(cmd2)

    def pull_image(self, version=None):
        version = version or self.image_version
        image = self.image_name
        cmd = "docker pull {image}:{version}".format(image=image,
                                                     version=version)
        with self._underlay.remote(node_name=self._admin_node_name) as remote:
            LOG.info("Pull {image}:{version}".format(image=image,
                                                     version=version))
            remote.check_call(cmd)

        with self._underlay.remote(node_name=self._admin_node_name) as remote:
            LOG.info("Getting image id")
            cmd = "docker images | grep 0.5.0| awk '{print $3}'"
            res = remote.check_call(cmd)
            self.image_id = res['stdout'][0].strip()
            LOG.info("Image ID is {}".format(self.image_id))

    def run(self):
        with self._underlay.remote(node_name=self._admin_node_name) as remote:
            cmd = ("docker run --net host -v /home/{user}/rally:/home/rally "
                   "-tid -u root {image_id}".format(
                       user=settings.SSH_LOGIN, image_id=self.image_id))
            LOG.info("Run Rally container")
            remote.check_call(cmd)

            cmd = ("docker ps | grep {image_id} | "
                   "awk '{{print $1}}'| head -1").format(
                       image_id=self.image_id)
            LOG.info("Getting container id")
            res = remote.check_call(cmd)
            self.docker_id = res['stdout'][0].strip()
            LOG.info("Container ID is {}".format(self.docker_id))

    def run_tempest(self, test=''):
        docker_exec = ('source /home/{user}/rally/openrc; '
                       'docker exec -i {docker_id} bash -c "{cmd}"')
        commands = [
            docker_exec.format(cmd="./install_tempest.sh",
                               user=settings.SSH_LOGIN,
                               docker_id=self.docker_id),
            docker_exec.format(
                cmd="source /home/rally/openrc && "
                    "rally verify start {test}".format(test=test),
                user=settings.SSH_LOGIN,
                docker_id=self.docker_id),
            docker_exec.format(
                cmd="rally verify results --json --output-file result.json",
                user=settings.SSH_LOGIN,
                docker_id=self.docker_id),
            docker_exec.format(
                cmd="rally verify results --html --output-file result.html",
                user=settings.SSH_LOGIN,
                docker_id=self.docker_id),
        ]
        with self._underlay.remote(node_name=self._admin_node_name) as remote:
            LOG.info("Run tempest inside Rally container")
            for cmd in commands:
                remote.check_call(cmd, verbose=True)
