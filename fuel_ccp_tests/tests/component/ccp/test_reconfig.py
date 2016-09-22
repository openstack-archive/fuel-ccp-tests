
import json

from fuel_ccp_tests import settings
from fuel_ccp_tests.helpers import post_os_deploy_checks


def test_deploy_and_reconfig_keystone(config, ccpcluster,
                                      k8s_actions, underlay):

    ccpcluster.deploy()
    post_os_deploy_checks.check_jobs_status(k8s_actions.api)
    post_os_deploy_checks.check_pods_status(k8s_actions.api)

    remote = underlay.remote(host=config.k8s.kube_host)
    res = remote.execute('source ~/openrc-ccp; openstack user list -f json')
    users1 = json.loads(res.stdout)
    remote.execute(
        "echo 'keystone__public_port: 5001' >> {deploy_config}".format(
            settings=settings.DEPLOY_CONFIG))
    ccpcluster.deploy('keystone')
    post_os_deploy_checks.check_jobs_status(k8s_actions.api)
    post_os_deploy_checks.check_pods_status(k8s_actions.api)

    res = remote.execute('source ~/openrc-ccp; openstack user list -f json')
    users2 = json.loads(res.stdout)

    assert users1 == users2
