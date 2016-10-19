=========================================
Welcome to fuell-ccp-tests documentation!
=========================================

Structure
=========
```
fuel_ccp_tests
├── fixtures
├── helpers
├── logs
├── managers
│   └── k8s
├── templates
│   ├── k8s_templates
│   ├── misc
│   └── registry_templates
└── tests
   ├── component
   │   ├── ccp
   │   ├── ceph
   │   ├── k8s
   │   ├── stacklight
   │   ├── ui
   │   └── underlay
   ├── non-functional
   ├── system
   │   ├── pre_commit
   └── unit
```

Fixtures
--------
The directory contains py.test fixtures

Helpers
-------
Contains set of helper methods: checkers, command executors in the container...

Managers
--------
Contains: envmanager - virtual machine layer, snapshot, revert; underlay_ssh_manager - exists for giving possibility manage the environment, existed or created by tests; k8smanager - k8s cluster management.

Templates
---------
Contains .yaml templates with environment configuration(virtual machines, networks, registry)

Tests Overview
================
The fuel-ccp-test are performed to verify that the completed software (ccp) functions according to the expectations defined by the requirements. 

The tests depended on purpose are divided on several categories.

###component/

Consists from several subgroups. The ccp subgroup includes:

- tests_ccp_cli_messages - checks the output messages depending on the ccp cli command. 
- test_ccp_errexit_codes - checks exit codes when commands are failed 
- test_ccp_logging - checking logging on different actions
- test_dry_run - checking cluster deployment  from yaml objects
- test_reconfig - checking redeployment of one openstack component, and state of the cluster after.

###system/

Consists from 2 categories **precommit** and **system**.  The purpose of the system tests is to maintain the quality of calico, ccp installation, ccp deployment with one/several os, k8s scaling, netchecker. The purpose of precommit is to check cluster components. For the correct precommit execution SERVICE_PATH variable should contains path to fuel-ccp-<some_repo> code with changes. The names of precommit tests were choosing according to the tested components.

Test execution
--------------
To execute tests necessary to add value to several variables via *export* or in the test command. Variables: 

- ENV_NAME - prefix name for the env and VMs
- IMAGE_PATH  - qcow2 image path
- WORKSPACE - directory path
- DEPLOY_SCRIPT - cargo path,  can be cloned from git.openstack.org/openstack/fuel-ccp-installer
- SHUTDOWN_ENV_ON_TEARDOWN - live switched ON the env value is (True), switched OFF value if (False)

After exporting execute the command:

py.test -vvv -s -k <test_name> or py.test -vvv -s -m <test_mark>

