# F5 OpenStack Validation Tools

#### Tools to interactively validate and test OpenStack clouds with F5 installations

This is a CentOS 7.3 based installation with global utilities and test tools installed from the OpenStack Mitaka release packages. 

For environments which require their own version of tools,  the installation process for the environment will properly install them.

## Building the Validation Image

Clone the git repository to a host with docker installed.

```
  git clone https://github.com/jgruber/f5_openstack_validation_tools.git
```

Edit the Dockerfile to enable the testing environments you wish to build. Remove the comment hash before the line setting the environment enabled variable for the container.

```
  vi ./f5_openstack_validation_tools/Dockerfile
```

By default the ```validate_neutron_for_f5_services```, ```neutron_mitaka```, ```lbaasv2_mitaka```, and ``image_importer`` environments are enabled.

**Disabled environment**

```
 # ENV enable_lbaasv2_mitaka=1
```

**Enabled environment**

```
 ENV enable_lbaasv2_mitaka=1
```

Run docker build from the Dockerfile.

```
  docker build -t f5_openstack_validation_tools ./f5_openstack_validation_tools
```

## Running the Validation Container

```
  docker run -t -i --name f5_openstack_validation_tools -v [F5_VE_zip_package_dir]:/bigip_images  f5_openstack_validation_tools
```

#### Source a test environment ####

Once your docker container is running you can source a test environment from various init files. Each test environment has a initialization script which will query your cloud for required testing configuration. 

You can download yor cloud RC file to your container and source the environment

```
   . overcloudrc
```
or the initialization script will prompt for your cloud credentials.

```
  OpenStack Tenant: admin
  OpenStack Username: admin
  OpenStack Password:
  OpenStack Auth URL: http://controller:5000/v2.0
```

To initialize a test environment source its init script. 

As an example, for the lbaav2_mitaka test environment, you would source the init script as follows.


```
  . init-lbaasv2_mitaka
```

All environment init scripts are in the root of the container file system.


## Instructions for Validating Specific Environments 


#### Validating your Neutron environment for use with F5 Multi-Tenant Services####

Simply intialize the neutron-valdation environment.

```
  . init-validate_neutron_for_f5_services
```

This environment is not interactive and exits when finished running.


#### Validating your Liberty Neutron environment ####

Simply intialize the neutron-valdation environment.

```
  . init-neutron_liberty
```

Once you have initialized the environment you run the validation tests simply run: 

```
  ./run_tests.sh
```

Alternatively you can list and run test using the ```testr``` or ```tempest``` community tools.

```
  testr list-tests
  tempest run --regex '.*smoke'
  testr failing
```

If tests failures leave residual configuration objects on your BIG-IPs you can clean your environment using the cleaning tool. From within the environment you can issue the following command:

```
  ./tools/clean
```

To exit this test environment simply run:

```
  finished
```


#### Validating your Liberty Neutron LBaaSv2 environment ####

Once your LBaaSv2 environment is setup you can test the validity of your environment.

Simply intialize the LBaaSv2 valdation environment.

```
  . init-lbaasv2_liberty
```

Once you have initialized the environment you run the validation tests simply run: 

```
  ./run_tests.sh
```

Alternatively you can list and run test using the ```testr``` or ```tempest``` community tools.

```
  testr list-tests
  tempest run --regex '.*smoke'
  testr failing
```

If tests failures leave residual configuration objects on your BIG-IPs you can clean your environment using the cleaning tool. From within the environment you can issue the following command:

```
  ./tools/clean
```

To exit this test environment simply run:

```
  finished
```


#### Validating your Mitaka Neutron environment ####

Simply intialize the neutron-valdation environment.

```
  . init-neutron_mitaka
```

Once you have initialized the environment you run the validation tests simply run: 

```
  ./run_tests.sh
```

Alternatively you can list and run test using the ```testr``` or ```tempest``` community tools.

```
  testr list-tests
  tempest run --regex '.*smoke'
  testr failing
```

If tests failures leave residual configuration objects on your BIG-IPs you can clean your environment using the cleaning tool. From within the environment you can issue the following command:

```
  ./tools/clean
```

To exit this test environment simply run:

```
  finished
```


#### Validating your Mitaka Neutron LBaaSv2 environment ####

Once your LBaaSv2 environment is setup you can test the validity of your environment.

Simply intialize the LBaaSv2 valdation environment.

```
  . init-lbaasv2_mitaka
```

Once you have initialized the environment you run the validation tests simply run: 

```
  ./run_tests.sh
```

Alternatively you can list and run test using the ```testr``` or ```tempest``` community tools.

```
  testr list-tests
  tempest run --regex '.*smoke'
  testr failing
```

If tests failures leave residual configuration objects on your BIG-IPs you can clean your environment using the cleaning tool. From within the environment you can issue the following command:

```
  ./tools/clean
```

To exit this test environment simply run:

```
  finished
```


#### Importing TMOS Virtual Edition images into your cloud ####

Assure that you can see the desired F5 TMOS zip files in the /bigip_images directory:

```
  ls /bigip_images
```

All F5 TMOS Virtual Edition zip files in that directory will be patched and uploaded to Glance when you source the image importer environment.

```
   . init-image_importer
```


