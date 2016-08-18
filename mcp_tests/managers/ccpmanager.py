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
from mcp_tests import settings
from mcp_tests import logger


LOG = logger.logger


class CCPManager(object):
    """docstring for CCPManager"""

    __config = None
    __underlay = None

    def __init__(self, config, underlay):
        self.__config = config
        self.__underlay = underlay
        super(CCPManager, self).__init__()

    def install_ccp(self):
        """Base action to deploy k8s by external deployment script"""
        LOG.info("Trying to install fuel-ccp on admin node")
        with self.__underlay.remote(
                host=self.__config.k8s.kube_host) as remote:

            ccp_repo_url = settings.CCP_REPO
            cmd = ('pip install --upgrade git+{}'.format(ccp_repo_url))
            with remote.get_sudo(remote):
                # TODO(ddmitriev): log output
                remote.check_call(cmd, verbose=True)
