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

import requests

from devops.helpers import helpers
from k8sclient.client import rest

from fuel_ccp_tests import logger
from fuel_ccp_tests import settings
from fuel_ccp_tests.helpers import utils


LOG = logger.logger


NETCHECKER_CONTAINER_PORT = NETCHECKER_SERVICE_PORT = 8081
NETCHECKER_NODE_PORT = 31081
NETCHECKER_REPORT_INTERVAL = 30

NETCHECKER_POD_CFG = {
    "apiVersion": "v1",
    "kind": "Pod",
    "metadata": {
        "labels": {
            "app": "netchecker-server"
        },
        "name": "netchecker-server"
    },
    "spec": {
        "containers": [
            {
                "env": None,
                "image": "127.0.0.1:31500/netchecker/server:latest",
                "imagePullPolicy": "Always",
                "name": "netchecker-server",
                "ports": [
                    {
                        "containerPort": NETCHECKER_CONTAINER_PORT,
                        "hostPort": NETCHECKER_CONTAINER_PORT
                    }
                ]
            },
            {
                "args": [
                    "proxy"
                ],
                "image": ("gcr.io/google_containers/kubectl:"
                          "v0.18.0-120-gaeb4ac55ad12b1-dirty"),
                "imagePullPolicy": "Always",
                "name": "kubectl-proxy"
            }
        ]
    }
}

NETCHECKER_SVC_CFG = {
    "apiVersion": "v1",
    "kind": "Service",
    "metadata": {
        "name": "netchecker-service"
    },
    "spec": {
        "ports": [
            {
                "nodePort": NETCHECKER_NODE_PORT,
                "port": NETCHECKER_SERVICE_PORT,
                "protocol": "TCP",
                "targetPort": NETCHECKER_CONTAINER_PORT
            }
        ],
        "selector": {
            "app": "netchecker-server"
        },
        "type": "NodePort"
    }
}

NETCHECKER_DS_CFG = [
    {
        "apiVersion": "extensions/v1beta1",
        "kind": "DaemonSet",
        "metadata": {
            "labels": {
                "app": "netchecker-agent-hostnet"
            },
            "name": "netchecker-agent"
        },
        "spec": {
            "template": {
                "metadata": {
                    "labels": {
                        "app": "netchecker-agent"
                    },
                    "name": "netchecker-agent"
                },
                "spec": {
                    "containers": [
                        {
                            "env": [
                                {
                                    "name": "MY_POD_NAME",
                                    "valueFrom": {
                                        "fieldRef": {
                                            "fieldPath": "metadata.name"
                                        }
                                    }
                                },
                                {
                                    "name": "REPORT_INTERVAL",
                                    "value": str(NETCHECKER_REPORT_INTERVAL)
                                }
                            ],
                            "image": "127.0.0.1:31500/netchecker/agent:latest",
                            "imagePullPolicy": "Always",
                            "name": "netchecker-agent"
                        }
                    ],
                    "nodeSelector": {
                        "netchecker": "agent"
                    }
                }
            }
        }
    },
    {
        "apiVersion": "extensions/v1beta1",
        "kind": "DaemonSet",
        "metadata": {
            "labels": {
                "app": "netchecker-agent-hostnet"
            },
            "name": "netchecker-agent-hostnet"
        },
        "spec": {
            "template": {
                "metadata": {
                    "labels": {
                        "app": "netchecker-agent-hostnet"
                    },
                    "name": "netchecker-agent-hostnet"
                },
                "spec": {
                    "containers": [
                        {
                            "env": [
                                {
                                    "name": "MY_POD_NAME",
                                    "valueFrom": {
                                        "fieldRef": {
                                            "fieldPath": "metadata.name"
                                        }
                                    }
                                },
                                {
                                    "name": "REPORT_INTERVAL",
                                    "value": str(NETCHECKER_REPORT_INTERVAL)
                                }
                            ],
                            "image": "127.0.0.1:31500/netchecker/agent:latest",
                            "imagePullPolicy": "Always",
                            "name": "netchecker-agent"
                        }
                    ],
                    "hostNetwork": True,
                    "nodeSelector": {
                        "netchecker": "agent"
                    }
                }
            }
        }
    }
]


def start_server(k8s, namespace=None,
                 pod_spec=NETCHECKER_POD_CFG,
                 svc_spec=NETCHECKER_SVC_CFG):
    """Start netchecker server in k8s cluster

    :param k8s: K8SManager
    :param namespace: str
    :param pod_spec: dict
    :param svc_spec: dict
    :return: None
    """
    for container in pod_spec['spec']['containers']:
        if container['name'] == 'netchecker-server':
            container['image'] = '{0}:{1}'.format(
                settings.MCP_NETCHECKER_SERVER_IMAGE_REPO,
                settings.MCP_NETCHECKER_SERVER_VERSION)
    try:
        if k8s.api.pods.get(name=pod_spec['metadata']['name']):
            LOG.debug('Network checker server pod {} is '
                      'already running! Skipping resource creation'
                      '.'.format(pod_spec['metadata']['name']))
    except rest.ApiException as e:
        if e.status == 404:
            k8s.check_pod_create(body=pod_spec, namespace=namespace)
        else:
            raise e

    try:
        if k8s.api.services.get(name=svc_spec['metadata']['name']):
            LOG.debug('Network checker server service {} is '
                      'already running! Skipping resource creation'
                      '.'.format(svc_spec['metadata']['name']))
    except rest.ApiException as e:
        if e.status == 404:
            k8s.check_service_create(body=svc_spec, namespace=namespace)
        else:
            raise e


def start_agent(k8s, namespace=None, ds_spec=NETCHECKER_DS_CFG):
    """Start netchecker agent in k8s cluster

    :param k8s:
    :param namespace:
    :param ds_spec:
    :return:
    """
    for k8s_node in k8s.api.nodes.list():
        k8s_node.add_labels({'netchecker': 'agent'})

    for ds in ds_spec:
        for container in (ds['spec']['template']['spec']['containers']):
            if container['name'] == 'netchecker-agent':
                container['image'] = '{0}:{1}'.format(
                    settings.MCP_NETCHECKER_AGENT_IMAGE_REPO,
                    settings.MCP_NETCHECKER_AGENT_VERSION)
        k8s.check_ds_create(body=ds, namespace=namespace)
        k8s.wait_ds_ready(dsname=ds['metadata']['name'], namespace=namespace)


@utils.retry(3, requests.exceptions.RequestException)
def get_status(kube_host_ip, netchecker_pod_port=NETCHECKER_NODE_PORT):
    net_status_url = 'http://{0}:{1}/api/v1/connectivity_check'.format(
        kube_host_ip, netchecker_pod_port)
    return requests.get(net_status_url, timeout=5)


def wait_running(kube_host_ip, timeout=120, interval=5):
    helpers.wait_pass(
        lambda: get_status(kube_host_ip),
        timeout=timeout, interval=interval)


def check_network(kube_host_ip, works=True):
    if works:
        assert get_status(kube_host_ip).status_code in (200, 204)
    else:
        assert get_status(kube_host_ip).status_code == 400


def wait_check_network(kube_host_ip, works=True, timeout=120, interval=5):
    helpers.wait_pass(lambda: check_network(kube_host_ip, works=works),
                      timeout=timeout, interval=interval)


def calico_block_traffic_on_node(underlay, target_node):
    LOG.info('Blocked traffic to the network checker service from '
             'containers on node "{}".'.format(target_node))
    underlay.sudo_check_call(
        'calicoctl profile calico-k8s-network rule add --at=1 outbound '
        'deny tcp to ports {0}'.format(NETCHECKER_SERVICE_PORT),
        node_name=target_node)


def calico_unblock_traffic_on_node(underlay, target_node):
    LOG.info('Unblocked traffic to the network checker service from '
             'containers on node "{}".'.format(target_node))
    underlay.sudo_check_call(
        'calicoctl profile calico-k8s-network rule remove outbound --at=1',
        node_name=target_node)
