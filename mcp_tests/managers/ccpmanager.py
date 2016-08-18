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

    def __init__(self, arg):
        super(CCPManager, self).__init__()
        self.arg = arg

    @classmethod
    def install_ccp(cls, underlay, config):
        """Base action to deploy k8s by external deployment script"""
        LOG.info("Trying to install fuel-ccp on admin node")
        remote = underlay.remote(host=config.k8s.kube_host)

        ccp_repo_url = settings.CCP_REPO
        cmd = ('pip install --upgrade git+{}'.format(ccp_repo_url))
        with remote.get_sudo(remote):
            remote.check_call(cmd, verbose=True)
        remote.close()
