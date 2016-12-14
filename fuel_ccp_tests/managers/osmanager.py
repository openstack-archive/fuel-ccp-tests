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
from fuel_ccp_tests.helpers import post_os_deploy_checks

LOG = logger.logger


class OSManager(object):
    """docstring for K8SManager"""

    __config = None
    __underlay = None

    def __init__(self, config, underlay, k8s_actions, ccpcluster):
        self.__config = config
        self.__underlay = underlay
        self.__k8s_actions = k8s_actions
        self.__ccpcluster = ccpcluster

    def install_os(self, topology=None,
                   check_os_ready=True):
        """Action to deploy openstack by ccp tool

        Additional steps:
            TODO

        :param env: EnvManager
        :param custom_yaml: False if deploy with kargo default, None if deploy
            with environment settings, or put you own
        :rtype: None
        """
        LOG.info("Trying to install k8s")

        """
        Deploy openstack with stacklight topology
        """
        LOG.info("Preparing openstack log collector fixture...")
        if settings.REGISTRY == "127.0.0.1:31500":
            LOG.info("Creating registry...")
            self.__k8s_actions.create_registry()
            LOG.info("Building images...")
            self.__ccpcluster.build()
        if topology:
            LOG.info("Pushing topology yaml...")
            with open(topology, 'r') as f:
                self.__ccpcluster.put_raw_config(
                    path=settings.CCP_DEPLOY_TOPOLOGY,
                    content=f.read())
            
            #self.__underlay.remote(
            #    host=self.__config.k8s.kube_host).upload(
            #    topology,
            #    settings.CCP_DEPLOY_TOPOLOGY)
        LOG.info("Deploy openstack")
        self.__ccpcluster.deploy()
        if check_os_ready:
            self.check_os_ready()
        self.__config.os.running = True

    def check_os_ready(self,
                       check_jobs_ready=True,
                       check_pods_ready=True):
        if check_jobs_ready:
            LOG.info("Checking openstack jobs statuses...")
            post_os_deploy_checks.check_jobs_status(self.__k8s_actions.api,
                                                    timeout=3600)
        if check_pods_ready:
            LOG.info("Checking openstack pods statuses...")
            post_os_deploy_checks.check_pods_status(self.__k8s_actions.api,
                                                    timeout=3600)
