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

import pytest
import yaml

from fuel_ccp_tests import logger
from fuel_ccp_tests import settings
from fuel_ccp_tests.helpers import ext
from fuel_ccp_tests.helpers import utils

LOG = logger.logger


@pytest.yield_fixture(scope='function')
def admin_node(config, underlay):
    LOG.info('Get SSH access to admin node')
    with underlay.remote(host=config.k8s.kube_host) as remote:
        yield remote


class CCPImagesInfo(object):

    def __init__(self, tag=None, namespace=None, maintainer=None):
        self.tag = tag
        self.namespace = namespace
        self.maintainer = maintainer


def get_images_info_from_ccp_config(remote):
    path = settings.CCP_CLI_PARAMS['config-file']
    raw_config = remote.execute(
        'cat {0}'.format(path))['stdout_str']
    ccp_conf = yaml.load(raw_config)
    images_info = CCPImagesInfo()
    for field in vars(images_info).keys():
        setattr(images_info,
                field,
                ccp_conf.get('images', {}).get(field))
    return images_info


def update_ccp_config(conf, remote, yaml_file='./.ccp.yaml'):
    for k, v in conf.items():
        utils.update_yaml([k], v, yaml_file=yaml_file, remote=remote)


def get_registry_content(remote, exclude_base_components=False,
                         secured=False):
    if secured:
        result = remote.execute(
            "curl --cacert {cacert} "
            "https://{user}:{password}@{address}/v2/_catalog".format(
                cacert=settings.REGISTRY_HTTP_TLS_CERTIFICATE,
                user=settings.PRIVATE_REGISTRY_LOGIN,
                password=settings.PRIVATE_REGISTRY_PASSWORD,
                address=settings.REGISTRY))
    else:
        result = remote.execute(
            'curl {}/v2/_catalog'.format(settings.REGISTRY))
    result = result.stdout_json['repositories']
    if exclude_base_components:
        base_components = ['base', 'base-tools']
        namespace = get_images_info_from_ccp_config(remote).namespace
        if namespace:
            base_components = ['/'.join([namespace, v])
                               for v in base_components]
        result = [v for v in result if v not in base_components]
    return result


def build_and_push_base_components(remote, ccpcluster):
    build_config = {
        "builder": {
            "push": True
        },
        "action": {
            "components": ["base", "base-tools"]
        }
    }
    update_ccp_config(build_config, remote)
    ccpcluster.build()


def assert_images_in_registry(images, registry_content,
                              remote, namespace=None):
    if not namespace:
        namespace = get_images_info_from_ccp_config(remote).namespace
    namespace = namespace if namespace else 'ccp'
    images = ['/'.join([namespace, v]) for v in images]
    for image in images:
        assert image in registry_content, \
            "Image '{0}' is not found in the registry".format(image)


def assert_images_info(components, images_info, admin_node):
    def get_image_id(image_name, remote):
        cmd = "docker images | " \
              "grep {image_name} | " \
              "awk '{{print $3}}' | " \
              "head -1".format(image_name=image_name)
        return remote.execute(cmd).stdout_str

    def get_image_author(image_id, remote):
        cmd = "docker inspect -f '{{{{.Author}}}}' {image_id}".format(
            image_id=image_id
        )
        return remote.execute(cmd).stdout_str

    def get_image_repotags(image_id, remote):
        cmd = "docker inspect -f '{{{{.RepoTags}}}}' {image_id}".format(
            image_id=image_id)
        result = remote.execute(cmd).stdout[0].split('/')[-2:]
        namespace, tag = result[0], result[1].split(':')[1][:-2]
        return namespace, tag

    images_info.tag = images_info.tag if images_info.tag else 'latest'
    images_info.namespace = images_info.namespace if images_info.namespace \
        else 'ccp'

    for component in components:
        image_id = get_image_id(component, admin_node)
        if images_info.maintainer:
            image_author = get_image_author(image_id, admin_node)
            assert images_info.maintainer == image_author, \
                "Incorrect image maintainer. Actual: '{0}', " \
                "expected: {1}".format(image_author, images_info.maintainer)
        image_namespace, image_tag = get_image_repotags(image_id, admin_node)
        assert image_namespace == images_info.namespace, \
            "Incorrect image namespace. Actual: '{0}', " \
            "expected: {1}".format(image_namespace, images_info.namespace)
        assert image_tag == images_info.tag, \
            "Incorrect image tag. Actual: '{0}', " \
            "expected: {1}".format(image_tag, images_info.tag)


@pytest.mark.revert_snapshot(ext.SNAPSHOT.ccp_deployed)
class TestCCPBuild(object):
    def test_build_default(
            self, ccpcluster, k8scluster, show_step, admin_node):
        """Build images and push to insecure registry as service on k8s

        Scenario:
            1. Create registry
            2. Build and push images to registry:
            3. Check that images were built and pushed to registry
        """
        # STEP #1
        show_step(1)
        k8scluster.create_registry()

        # STEP #2
        show_step(2)
        ccpcluster.build()

        # STEP #3
        show_step(3)
        registry_content = get_registry_content(admin_node)
        LOG.info("Registry contains the following images: {}".format(
            registry_content))
        # TODO(dzapeka): add assertion for step #3

    def test_build_and_push_one_image_to_insecure_registry(
            self, ccpcluster, k8scluster, show_step, admin_node):
        """Build 1 image and push to insecure registry as service on k8s,
        use custom tag, namespace and maintainer

        Scenario:
            1. Create registry
            2. Build and push one image to registry:
            3. Check that images were built and pushed to registry
            4. Check tag, namespace and maintainer of image
        """

        # STEP #1
        show_step(1)
        k8scluster.create_registry()

        # STEP #2
        show_step(2)
        # TODO (dzapeka): build will be skipped due to parent image (base)
        # build failure if custom tag is used. Not sure that cpp build works as
        # intended with custom tags.
        images_info = CCPImagesInfo(
            namespace="testnamespace",
            maintainer="testmaintainer"
        )

        components = ["rabbitmq"]

        build_config = {
            "builder": {
                "push": True
            },
            "action": {
                "components": components
            },
            "images": {
                "namespace": images_info.namespace,
                "maintainer": images_info.maintainer
            }
        }

        update_ccp_config(build_config, admin_node)
        ccpcluster.build()

        # STEP #3
        show_step(3)
        registry_content = get_registry_content(admin_node)
        LOG.info("Registry contains the following images: {}".format(
            registry_content))
        assert_images_in_registry(components, registry_content, admin_node)

        # STEP #4
        show_step(4)
        assert_images_info(components, images_info, admin_node)

    def test_rebuild_and_push_one_image_to_insecure_registry(
            self, ccpcluster, k8scluster, show_step, admin_node):
        """Rebuild one image and push it to the insecure registry

        Scenario:
            1. Create registry
            2. Build and push images to the registry
            3. Re-build one image and push it to the registry
            4. Check that image id is changed after rebuild
        """
        # STEP #1
        show_step(1)
        k8scluster.create_registry()

        # STEP #2
        show_step(2)
        component = "rabbitmq"
        build_config = {
            "builder": {
                "push": True
            },
            "action": {
                "components": [component]
            }
        }
        update_ccp_config(build_config, admin_node)
        ccpcluster.build()
        images_info = get_images_info_from_ccp_config(admin_node)
        cmd = "docker images | " \
              "grep -E '{component}.*{tag}' | " \
              "awk '{{ print $3 }}'".format(component=component,
                                            tag=images_info.tag)
        image_id = admin_node.execute(cmd)['stdout_str']
        LOG.info("ImageId for '{0}': '{1}'".format(component, image_id))

        # STEP #3
        show_step(3)
        build_config = {
            "builder": {
                "push": True,
                "no_cache": True
            }
        }
        update_ccp_config(build_config, admin_node)
        ccpcluster.build()

        # STEP #4
        show_step(4)
        image_id_rebuild = admin_node.execute(cmd)['stdout_str']
        LOG.info("ImageId for '{0}' after rebuild: '{1}'".format(
            component, image_id_rebuild))
        assert image_id != image_id_rebuild, \
            "ImageId is not changed after rebuild"

    def test_build_images_and_push_them_separately_to_insecure_registry(
            self, ccpcluster, k8scluster, show_step, admin_node):
        """Build images and push them separately to the insecure registry

        Scenario:
        1. Create registry
        2. Build and push base images: ["base", "base-tools"]
        3. Build images
        4. Check that images were built and were not pushed to registry
        5. Push images to registry
        6. Check that images were pushed to registry
        """
        # STEP #1
        show_step(1)
        k8scluster.create_registry()

        # STEP #2
        show_step(2)
        build_and_push_base_components(admin_node, ccpcluster)

        # STEP #3
        show_step(3)
        components = ["rabbitmq"]
        build_config = {
            "builder": {
                "push": False,
                "workers": 1
            },
            "action": {
                "components": components
            }
        }
        update_ccp_config(build_config, admin_node)
        ccpcluster.build()

        # STEP #4
        show_step(4)
        result = get_registry_content(admin_node,
                                      exclude_base_components=True)
        LOG.info("Registry contains the following images: {}".format(result))

        assert not result, \
            "Registry is not empty. Images should not be pushed to the " \
            "registry"

        # STEP #5
        show_step(5)
        build_config = {
            "builder": {
                "push": True
            },
            "action": {
                "components": components
            }
        }
        update_ccp_config(build_config, admin_node)
        ccpcluster.build()

        # STEP #6
        show_step(6)
        registry_content = get_registry_content(admin_node)
        LOG.info("Registry contains the following images: {}".format(
            registry_content))
        assert_images_in_registry(components, result, admin_node)

    def test_builder_push_to_secure_registry_as_service_on_k8s(
            self, ccpcluster, k8scluster, underlay, config, show_step):
        """Build images and push to insecure registry as service on k8s

        Scenario:
        1. Create secured registry
        2. Build and push images to registry:
        3. Check that images were built and pushed to registry
        """

        # STEP #1
        show_step(1)
        k8scluster.create_secured_registry(config, underlay)

        # STEP #2
        show_step(2)
        ccpcluster.build()
        registry_content = get_registry_content(admin_node, secured=True)
        LOG.info("Registry contains the following images: {}".format(
            registry_content))

        # STEP #3
        show_step(3)

        # TODO(dzapeka): add assertion for step #3

    def test_builder_push_one_image_to_secure_registry(
            self, ccpcluster, k8scluster, admin_node,
            config, underlay, show_step):
        """Build 1 image and push to insecure registry as service on k8s,
        use custom tag, namespace and maintainer

        Scenario:
        1. Create secured registry
        2. Build and push 1 image to registry
        3. Check that images were built and pushed to the registry
        4. Check tag, namespace and maintainer of image
        """

        # STEP #1
        show_step(1)
        k8scluster.create_secured_registry(config, underlay)

        # STEP #2
        show_step(2)
        # TODO (dzapeka): build will be skipped due to parent image (base)
        # build failure if custom tag is used. Not sure that cpp build works as
        # intended with custom tags.
        images_info = CCPImagesInfo(
            namespace="testnamespace",
            maintainer="testmaintainer"
        )
        components = ["rabbitmq"]
        build_config = {
            "builder": {
                "push": True
            },
            "action": {
                "components": components
            },
            "images": {
                "namespace": images_info.namespace,
                "maintainer": images_info.maintainer
            }
        }
        update_ccp_config(build_config, admin_node)
        ccpcluster.build(components=components)
        registry_content = get_registry_content(admin_node, secured=True)
        LOG.info("Registry contains the following images: {}".format(
            registry_content))

        # STEP #3
        show_step(3)
        assert_images_in_registry(components, registry_content, admin_node)

        # STEP #4
        show_step(4)
        assert_images_info(components, images_info, admin_node)
