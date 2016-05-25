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

from __future__ import division

from mcp_tests.logger import logger


def exec_in_container(container, cmd):
    command = container.create_exec(cmd)
    stdout = container.start_exec(command)
    inspect = container.client.exec_inspect(command['Id'])
    return stdout, inspect['ExitCode']


class ContainerEngine(object):
    def __init__(self,
                 remote=None,
                 image_name=None,
                 container_repo=None,
                 proxy_url=None,
                 user_id=0,
                 container_name=None,
                 dir_for_home='/var/home',
                 ):
        self.remote = remote
        self.container_repo = container_repo
        self.repository_tag = 'latest'
        self.proxy_url = proxy_url or ""
        self.user_id = user_id
        self.image_name = image_name
        self.container_name = container_name
        self.dir_for_home = dir_for_home
        self.home_bind_path = '{0}/{1}'.format(
            self.dir_for_home, self.container_name)
        self.setup()

    def image_exists(self, tag='latest'):
        cmd = "docker images | grep {0}| awk '{{print $1}}'".format(
            self.image_name)
        logger.info('Checking Docker images...')
        result = self.remote.execute(cmd)
        logger.debug(result)
        existing_images = [line.strip().split() for line in result['stdout']]
        return [self.container_repo, tag] in existing_images

    def pull_image(self):
        # TODO: add possibility to load image from local path or
        # remote link provided in settings, in order to speed up downloading
        cmd = 'docker pull {0}'.format(self.container_repo)
        logger.debug('Downloading Rally repository/image from registry...')
        result = self.remote.execute(cmd)
        logger.debug(result)
        return self.image_exists()

    def run_container_command(self, command, in_background=False):
        command = str(command).replace(r"'", r"'\''")
        options = ''
        if in_background:
            options = '{0} -d'.format(options)
        cmd = ("docker run {options} --user {user_id} --net=\"host\"  -e "
               "\"http_proxy={proxy_url}\" -e \"https_proxy={proxy_url}\" "
               "-v {dir_for_home}:{home_bind_path} {container_repo}:{tag} "
               "/bin/bash -c '{command}'".format(
                   options=options,
                   user_id=self.user_id,
                   proxy_url=self.proxy_url,
                   dir_for_home=self.dir_for_home,
                   home_bind_path=self.home_bind_path,
                   container_repo=self.container_repo,
                   tag=self.repository_tag,
                   command=command))
        logger.debug('Executing command "{0}" in Rally container {1}..'.format(
            cmd, self.container_repo))
        result = self.remote.execute(cmd)
        logger.debug(result)
        return result

    def setup_utils(self):
        utils = ['gawk', 'vim', 'curl']
        cmd = ('unset http_proxy https_proxy; apt-get update; '
               'apt-get install -y {0}'.format(' '.join(utils)))
        logger.debug('Installing utils "{0}" to the  container...'.format(
            utils))
        result = self.run_container_command(cmd)
        assert(result['exit_code'] == 0,
               'Utils installation failed in container: '
               '{0}'.format(result))

    def prepare_image(self):
        self.setup_utils()
        last_container_cmd = "docker ps -lq"
        result = self.remote.execute(last_container_cmd)
        assert(result['exit_code'] == 0,
               "Unable to get last container ID: {0}!".format(result))
        last_container = ''.join([line.strip() for line in result['stdout']])
        commit_cmd = 'docker commit {0} {1}:ready'.format(last_container,
                                                          self.container_repo)
        result = self.remote.execute(commit_cmd)
        assert(result['exit_code'] == 0,
               'Commit to Docker image "{0}" failed: {1}.'.format(
                   self.container_repo, result))
        return self.image_exists(tag='ready')

    def setup_bash_alias(self):
        alias_name = '{}_docker'.format(self.image_name)
        check_alias_cmd = '. /root/.bashrc && alias {0}'.format(alias_name)
        result = self.remote.execute(check_alias_cmd)
        if result['exit_code'] == 0:
            return
        logger.debug('Creating bash alias for {} inside container...'.format(
            self.image_name))
        create_alias_cmd = ("alias {alias_name}='docker run --user {user_id} "
                            "--net=\"host\"  -e \"http_proxy={proxy_url}\" -t "
                            "-i -v {dir_for_home}:{home_bind_path}  "
                            "{container_repo}:{tag} {image_name}'".format(
                                alias_name=alias_name,
                                user_id=self.user_id,
                                proxy_url=self.proxy_url,
                                dir_for_home=self.dir_for_home,
                                home_bind_path=self.home_bind_path,
                                container_repo=self.container_repo,
                                tag=self.repository_tag,
                                image_name=self.image_name))
        result = self.remote.execute('echo "{0}">> /root/.bashrc'.format(
            create_alias_cmd))
        assert (result['exit_code'] == 0,
                "Alias creation for running {0} from container failed: "
                "{1}.".format(self.image_name, result))
        result = self.remote.execute(check_alias_cmd)
        assert(result['exit_code'] == 0,
               "Alias creation for running {} from container failed: "
               "{1}.".format(self.image_name, result))

    def setup(self):
        if not self.image_exists():
            assert (self.pull_image(),
                    "Docker image for {} not found!".format(self.image_name))
        if not self.image_exists(tag='ready'):
            assert(self.prepare_image(),
                   "Docker image for {} is not ready!".format(self.image_name))
        self.repository_tag = 'ready'
        self.setup_bash_alias()
