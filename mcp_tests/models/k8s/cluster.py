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


import base64
import ssl

from k8sclient.client import api_client
from k8sclient.client.apis import apiv_api
from k8sclient.client.apis import apisextensionsvbeta_api
from k8sclient.client.apis import apisbatchv_api

from mcp_tests.models.k8s.componentstatuses import \
    K8sComponentStatusManager
from mcp_tests.models.k8s.daemonsets import K8sDaemonSetManager
from mcp_tests.models.k8s.deployments import K8sDeploymentManager
from mcp_tests.models.k8s.endpoints import K8sEndpointManager
from mcp_tests.models.k8s.events import K8sEventManager
from mcp_tests.models.k8s.horizontalpodautoscalers import \
    K8sHorizontalPodAutoscalerManager
from mcp_tests.models.k8s.ingresses import K8sIngressManager
from mcp_tests.models.k8s.jobs import K8sJobManager
from mcp_tests.models.k8s.limitranges import K8sLimitRangeManager
from mcp_tests.models.k8s.namespaces import K8sNamespaceManager
from mcp_tests.models.k8s.nodes import K8sNodeManager
from mcp_tests.models.k8s.persistentvolumeclaims import \
    K8sPersistentVolumeClaimManager
from mcp_tests.models.k8s.persistentvolumes import \
    K8sPersistentVolumeManager
from mcp_tests.models.k8s.pods import K8sPodManager
from mcp_tests.models.k8s.replicationcontrollers import \
    K8sReplicationControllerManager
from mcp_tests.models.k8s.resourcequotas import K8sResourceQuotaManager
from mcp_tests.models.k8s.secrets import K8sSecretManager
from mcp_tests.models.k8s.serviceaccounts import K8sServiceAccountManager
from mcp_tests.models.k8s.services import K8sServiceManager


class K8sCluster(object):
    """docstring for K8sCluster"""

    def __init__(self, schema="https", user=None, password=None,
                 host='localhost', port='443', namespace='default'):
        if user and password:
            auth = base64.encodestring('%s:%s' % (user, password))[:-1]
            auth = "Basic {}".format(auth)
            self._client = api_client.ApiClient(
                '{schema}://{host}:{port}/'.format(
                    schema=schema, host=host, port=port))
            self._client.set_default_header('Authorization', auth)
            restcli_impl = self._client.RESTClient.IMPL
            restcli_impl.ssl_pool_manager.connection_pool_kw['cert_reqs'] = \
                ssl.CERT_NONE

        else:
            self._client = api_client.ApiClient(
                '{schema}://{host}:{port}/'.format(
                    schema=schema, host=host, port=port))
        self._api = apiv_api.ApivApi(self._client)
        self._bapi = apisbatchv_api.ApisbatchvApi(self._client)
        self._eapi = apisextensionsvbeta_api.ApisextensionsvbetaApi(
            self._client)
        self._namespace = namespace

        self.nodes = K8sNodeManager(self._api, self._namespace)
        self.pods = K8sPodManager(self._api, self._namespace)
        self.endpoints = K8sEndpointManager(self._api, self._namespace)
        self.namespaces = K8sNamespaceManager(self._api, self._namespace)
        self.services = K8sServiceManager(self._api, self._namespace)
        self.serviceaccounts = K8sServiceAccountManager(
            self._api, self._namespace)
        self.secrets = K8sSecretManager(self._api, self._namespace)
        self.events = K8sEventManager(self._api, self._namespace)
        self.limitranges = K8sLimitRangeManager(self._api, self._namespace)
        self.jobs = K8sJobManager(self._bapi, self._namespace)
        self.daemonsets = K8sDaemonSetManager(self._eapi, self._namespace)
        self.ingresses = K8sIngressManager(self._eapi, self._namespace)
        self.deployments = K8sDeploymentManager(self._eapi, self._namespace)
        self.horizontalpodautoscalers = K8sHorizontalPodAutoscalerManager(
            self._eapi, self._namespace)
        self.componentstatuses = K8sComponentStatusManager(
            self._api, self._namespace)
        self.resourcequotas = K8sResourceQuotaManager(
            self._api, self._namespace)
        self.replicationcontrollers = K8sReplicationControllerManager(
            self._api, self._namespace)
        self.pvolumeclaims = K8sPersistentVolumeClaimManager(
            self._api, self._namespace)
        self.pvolumes = K8sPersistentVolumeManager(
            self._api, self._namespace)
