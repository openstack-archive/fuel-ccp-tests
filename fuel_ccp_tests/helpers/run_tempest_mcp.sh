#!/bin/bash -xe

function prepare {
    sudo rm -rf /home/vagrant/rally
    mkdir /home/vagrant/rally
    echo "sed -i 's|#swift_operator_role = Member|swift_operator_role=SwiftOperator|g' /etc/rally/rally.conf
          source /home/rally/openrc
          rally-manage db recreate
          rally deployment create --fromenv --name=tempest
          rally verify install
          rally verify genconfig
          rally verify showconfig" > /home/vagrant/rally/install_tempest.sh
    chmod +x /home/vagrant/rally/install_tempest.sh
    cp /home/vagrant/openrc-* /home/vagrant/rally/openrc
}

function install_docker_and_run {
    docker pull rallyforge/rally:0.5.0
    image_id=$(docker images | grep 0.5.0| awk '{print $3}')
    docker run --net host -v /home/vagrant/rally:/home/rally -tid -u root $image_id
    docker_id=$(docker ps | grep $image_id | awk '{print $1}'| head -1)
}

function run_tempest {
    source /home/vagrant/rally/openrc
    docker exec -i $docker_id bash -c "./install_tempest.sh"
    docker exec -i $docker_id bash -c "source /home/rally/openrc && rally verify start $1"
    docker exec -i $docker_id bash -c "rally verify results --json --output-file result.json"
    docker exec -i $docker_id bash -c "rally verify results --html --output-file result.html"
}

prepare
install_docker_and_run
run_tempest "$1"
