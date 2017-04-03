#!/bin/bash

ENV=neutron_newton

enabled_var="enable_$ENV"

if [[ ! ${!enabled_var} == 1 ]]
then
    echo "$ENV disabled"
    exit 0
else
    echo "installing $ENV"
fi

DIR=/$ENV

# initialize the environment
cd /
tempest init $ENV
virtualenv $ENV
cp -R /environments${DIR}/. $DIR/
cp $DIR/init-$ENV /init-$ENV
chmod +x /init-$ENV 

# Get correct version of the software to test and
# copy to the working directory for the environemnt
mkdir $DIR/build

# liberty-eol version of neutron-lbaas
cd $DIR/build

git clone -b stable/newton https://github.com/openstack/neutron.git
cd $DIR/build/neutron
mv $DIR/build/neutron/neutron $DIR/neutron
mv $DIR/build/neutron/requirements.txt $DIR/neutron/requirements.txt
mv $DIR/build/neutron/test-requirements.txt $DIR/neutron/test-requirements.txt

# get rid of the unused source and branches
rm -rf $DIR/build

# install in the virtualenv for the environment
cd $DIR
/bin/bash -c "cd $DIR \
              && source ./bin/activate \
              && pip install -r ./neutron/requirements.txt \
              && pip install -r ./neutron/test-requirements.txt \
              && pip install --upgrade junitxml"

# clean up container files
find $DIR/tools -type f -exec chmod +x {} \;
chmod +x $DIR/run_tests.sh


