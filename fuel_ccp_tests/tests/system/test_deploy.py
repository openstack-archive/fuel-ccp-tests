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
import os
import pytest
import yaml

import base_test
from fuel_ccp_tests import logger
from fuel_ccp_tests import settings
from fuel_ccp_tests.helpers import post_install_k8s_checks
from fuel_ccp_tests.helpers import post_os_deploy_checks
from fuel_ccp_tests.helpers import ext
from fuel_ccp_tests.managers import k8smanager
from fuel_ccp_tests.managers import ccpmanager

LOG = logger.logger


@pytest.mark.deploy_openstack
class TestDeployOpenstack(base_test.SystemBaseTest):
    """Deploy OpenStack with CCP

       pytest.mark: deploy_openstack
    """

    snapshot_microservices_deployed = 'snapshot_microservices_deployed'
    kube_settings = {
        "kube_network_plugin": "calico",
        "kube_proxy_mode": "iptables",
        "hyperkube_image_repo": "quay.io/coreos/hyperkube",
        "hyperkube_image_tag": "{0}_coreos.0".format(settings.KUBE_VERSION),
        "kube_version": settings.KUBE_VERSION,
        "ipip": settings.IPIP_USAGE,
        "images_namespace": settings.IMAGES_NAMESPACE,
        "docker_options": settings.REGISTRY,
        "docker_options": "--insecure-registry={0}".format(settings.REGISTRY),
        "upstream_dns_servers": settings.UPSTREAM_DNS,
    }

    def get_params(self, params_list, exclude_list):
        params = [param for param in params_list if param not in exclude_list]
        return params

    def create_registry(self, remote):
        registry_pod = os.path.join(
            os.getcwd(),
            '/fuel_ccp_tests/templates/registry_templates/registry-pod.yaml')
        service_registry = os.path.join(
            os.getcwd(),
            '/fuel_ccp_tests/templates/registry_templates/'
            'service-registry.yaml')
        for item in registry_pod, service_registry:
            remote.upload(item, './')
        command = [
            'kubectl create -f ~/{0}'.format(registry_pod.split('/')[-1]),
            'kubectl create -f ~/{0}'.format(
                service_registry.split('/')[-1]),
        ]
        for cmd in command:
            LOG.info(
                "Running command '{cmd}' on node {node}".format(
                    cmd=cmd,
                    node=remote.hostname
                )
            )
            result = remote.execute(cmd)
            assert result['exit_code'] == 0

    def pre_build_deploy_step(self, remote):
        topology_path = os.path.join(
            os.getcwd(),
            '/fuel_ccp_tests/templates/k8s_templates/k8s_topology.yaml')
        remote.upload(topology_path, './')
        command = '>/var/log/microservices.log'
        with remote.get_sudo(remote):
            LOG.info(
                "Running command '{cmd}' on node {node}".format(
                    cmd=command,
                    node=remote.hostname
                )
            )
            result = remote.check_call(command, verbose=True)
            assert result['exit_code'] == 0

    @pytest.mark.snapshot_needed(name=snapshot_microservices_deployed)
    @pytest.mark.revert_snapshot(ext.SNAPSHOT.initial)
    @pytest.mark.fail_snapshot
    def test_fuel_ccp_deploy_microservices(self, config, underlay):
        """Deploy base environment

        Scenario:
        1. Revert snapshot
        2. Install microservices
        3. Deploy environment
        4. Check deployment

        Duration 30 min
        """
        config.k8s.kube_host = k8smanager.K8SManager.install_k8s(
            underlay, custom_yaml=self.kube_settings)
        ccpmanager.CCPManager.install_ccp(underlay, config)
        k8sclient = k8smanager.K8SManager.get_k8sclient(config)

        remote = underlay.remote(host=config.k8s.kube_host)
        self.pre_build_deploy_step(remote)

        registry = None
        if settings.BUILD_IMAGES:
            registry = '127.0.0.1:31500'
            self.create_registry(remote)
            exclude_list = ['deploy']
            yaml_path = os.path.join(
                os.getcwd(),
                '/fuel_ccp_tests/templates/'
                'k8s_templates/build-deploy_cluster.yaml')
            with open(yaml_path, 'r') as yaml_path:
                params_list = yaml.load(yaml_path)['ccp-microservices-options']
                params = self.get_params(params_list, exclude_list)
                data = ' '.join(params)
                data = data.format(registry_address=registry,
                                   images_namespace=settings.IMAGES_NAMESPACE,
                                   images_tag=settings.IMAGES_TAG)
            command = [
                'ccp {0}'.format(data)
            ]
            with remote.get_sudo(remote):
                for cmd in command:
                    LOG.info(
                        "Running command '{cmd}' on node {node}".format(
                            cmd=cmd,
                            node=remote.hostname
                        )
                    )
                    result = remote.execute(cmd)
                    assert result['exit_code'] == 0
            post_install_k8s_checks.check_calico_network(remote, k8sclient)
        else:
            registry = settings.REGISTRY
            if not registry:
                raise ValueError("The REGISTRY variable should be set with "
                                 "external registry address, "
                                 "current value {0}".format(settings.REGISTRY))

        exclude_list = ['build', '--builder-push', '--builder-workers 1']
        yaml_path = os.path.join(
            os.getcwd(),
            '/fuel_ccp_tests/templates/'
            'k8s_templates/build-deploy_cluster.yaml')

        with open(yaml_path, 'r') as yaml_path:
            params_list = yaml.load(yaml_path)['ccp-microservices-options']
            params = self.get_params(params_list, exclude_list)
            data = ' '.join(params)
            data = data.format(
                registry_address=registry,
                images_namespace=settings.IMAGES_NAMESPACE,
                images_tag=settings.IMAGES_TAG)
        command = [
            'ccp {0}'.format(data),
        ]
        with remote.get_sudo(remote):
            for cmd in command:
                LOG.info(
                    "Running command '{cmd}' on node {node}".format(
                        cmd=cmd,
                        node=remote.hostname
                    )
                )
                result = remote.execute(cmd)
                assert result['exit_code'] == 0
        post_os_deploy_checks.check_jobs_status(k8sclient, timeout=1500,
                                                namespace='ccp')
        post_os_deploy_checks.check_pods_status(k8sclient, timeout=1500,
                                                namespace='ccp')
