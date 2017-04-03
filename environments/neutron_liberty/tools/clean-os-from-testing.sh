#!/bin/bash

for instance in $(nova list --all-tenants 2>/dev/null | tail -n +4 | head -n -1 | awk '{print $2}')
do
    is_tempest=$(nova show $instance 2>/dev/null | grep tempest|wc -l)
    if [[ $is_tempest ]]
    then
       echo "deleting Nova server $instance"
       nova delete $instance
    fi
done

for secgroup in $(neutron security-group-list 2>/dev/null | grep tempest | awk '{print $2}')
do
    echo "delete neutron security-group $secgroup"
    neutron security-group-delete $secgroup 2>/dev/null
done

for router in $(neutron router-list 2>/dev/null | grep tempest | awk '{print $2}')
do
    echo "deleting router $router"
    neutron router-port-list $router 2>/dev/null | grep subnet_id | while read line; do subnet_id=$(echo $line|awk 'BEGIN { FS="\"";}{print $4}'); neutron router-interface-delete $router $subnet_id 2>/dev/null; done
    neutron router-delete $router 2>/dev/null
done

for pool in $(neutron lbaas-pool-list 2>/dev/null | tail -n +4 | head -n -1 | awk '{print $2}')
do
    echo "deleting neutron LBaaS pool $pool"
    neutron lbaas-pool-delete $pool 2>/dev/null
done

for listener in $(neutron lbaas-listener-list 2>/dev/null | tail -n +4 | head -n -1 | awk '{print $2}')
do
    echo "deleting neutron LBaaS listener $listener"
    neutron lbaas-listener-delete $listener 2>/dev/null
done

for loadbalancer in $(neutron lbaas-loadbalancer-list 2>/dev/null | tail -n +4 | head -n -1 | awk '{print $2}')
do
    echo "deleting neutron LBaaS loadbalancer $loadbalancer"
    neutron lbaas-loadbalancer-delete $loadbalancer 2>/dev/null
done

for network in $(neutron net-list 2>/dev/null | tail -n +4 | head -n -1 | awk '{print $2}')
do
    network_name=$(neutron net-show $network 2>/dev/null | grep name | awk '{print $4}')
    subnets_id=$(neutron net-show $network 2>/dev/null | grep subnets | awk '{print $4}')
    if [[ $network_name == tempest* || $network_name == network-* ]]
    then  
        neutron port-list 2>/dev/null | grep $subnets_id | while read line ; do port_id=$(echo $line|awk '{print $2}'); echo "deleting neutron port $port_id"; neutron port-delete $port_id 2>/dev/null; done
        echo "deleting neutron subnet $subnets_id"
        neutron subnet-delete $subnets_id 2>/dev/null
        echo "deleting neutron network $network"
        neutron net-delete $network 2>/dev/null
    fi
done

for project in $(openstack project list | tail -n +4 | head -n -1 | awk '{print $2}')
do
    project_name=$(openstack project show $project | grep name | awk '{print $4}')
    if [[ $project_name == tempest* ]]
    then
        echo "deleting stranded project $project_name from OpenStack"
        openstack project delete $project
    fi
done

