.. _devops_underlay.conf.example:

.. code-block:: ini

    #this config can be used to provide access to underlay layer of the lab that is managed with fuel-devops
    [hardware]
    manager='devops'
    conf_path='fuel_ccp_tests/tests/fixtures/templates/default.yaml'

    [underlay]
    ssh='[{'node_name': node1,
           'host': hostname,
           'login': login,
           'password': password,
           'address_pool': (optional),
           'port': (optional),
           'keys': [(optional)],
         }]'