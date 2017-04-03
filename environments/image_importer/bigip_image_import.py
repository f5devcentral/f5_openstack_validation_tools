import os, sys, re, glob, zipfile, tarfile, time, requests, paramiko, pprint, socket, uuid
import glanceclient.v1.client as gclient
import keystoneclient.v2_0.client as ksclient
import neutronclient.v2_0.client as netclient
import novaclient.client as compclient
import heatclient.client as heatclient

UBUNTU_IMAGE = 'http://cloud-images.ubuntu.com/trusty/current/trusty-server-cloudimg-amd64-disk1.img'
BIGIP_TAR_IMAGE = 'bigipzips.tar'
WEB_SERVER_TEMPLATE = './bigip_image_importer_webserver.yaml'
F5_IMAGE_TEMPLATE = 'https://raw.githubusercontent.com/F5Networks/f5-openstack-heat/master/f5_supported/ve/images/patch_upload_ve_image.yaml'
CONTAINERFORMAT = 'bare'
DISKFORMAT = 'qcow2'

VE_PROPS = {'ALL': {'os_product':'F5 TMOS Virtual Edition for All Modules. 160G disk, 8 or 16G RAM, 4 or 8 vCPUs.'},
            'LTM': {'os_product':'F5 TMOS Virtual Edition for Local Traffic Manager 40G disk, 4 or 8G RAM, 2 or 4 vCPUs.'},
            '1SLOT': {'os_product':'F5 TMOS Virtual Edition for Local Traffic Manager - Small Footprint Single Version. 8G disk, 4G RAM, 1 vCPUs.'},
            'iWorkflow': {'os_product':'F5 TMOS Virtual Edition for iWorkflow Orchestration Services. 160G disk, 4G RAM, 2 vCPUs.'},
            'BIG-IQ': {'os_product':'F5 TMOS Virtual Edition for BIG-IQ Configuration Management Server. 160G disk, 4G RAM, 2 vCPUs.'}}

VE_REQ = {'ALL': {'min_disk':'160', 'min_ram':'8192'},
          'LTM': {'min_disk':'40', 'min_ram':'4096'},
          '1SLOT': {'min_disk':'8', 'min_ram':'2048'},
          'iWorkflow': {'min_disk':'160', 'min_ram':'4096'},
          'BIG-IQ': {'min_disk':'160', 'min_ram':'4096'}}


def _make_bigip_inventory():
    if not 'IMAGE_DIR' in os.environ: 
        return None

    bigip_images = {}
    
    # BIGIP and BIG-IQ Image Packages
    for file in glob.glob("%s/BIG*.zip" % os.environ['IMAGE_DIR']):
        vepackage = zipfile.ZipFile(file)
        filename = os.path.basename(file)
        for packed in vepackage.filelist:
            if packed.filename.startswith(filename[:8]) and \
               packed.filename.endswith('qcow2'): 
                if not filename in bigip_images:
                    bigip_images[filename] = {'image': None,
                                              'datastor': None,
                                              'file': file,
                                              'archname': filename}
                if packed.filename.find('DATASTOR') < 0:
                    bigip_images[filename]['image'] = packed.filename
                else:
                    bigip_images[filename]['datastor'] = packed.filename
    
    # iWorkflow Image Packages
    for file in glob.glob("%s/iWorkflow*.zip" % os.environ['IMAGE_DIR']):
        vepackage = zipfile.ZipFile(file)
        filename = os.path.basename(file)
        for packed in vepackage.filelist:
            if packed.filename.startswith(filename[:8]) and \
               packed.filename.endswith('qcow2'): 
                if not filename in bigip_images:
                    bigip_images[filename] = {'image': None,
                                              'datastor': None,
                                              'file': file,
                                              'archname': filename}
                if packed.filename.find('DATASTOR') < 0:
                    bigip_images[filename]['image'] = packed.filename
                else:
                    bigip_images[filename]['datastor'] = packed.filename

    return bigip_images


def _images_needing_import(bigip_images):
    image_names = bigip_images.keys()
    for image in image_names:
        final_image_name = image.replace('.qcow2.zip', '')
        gc = _get_glance_client()
        for uploaded_image in gc.images.list():
            if uploaded_image.name == final_image_name:
                del bigip_images[image]
    return bigip_images
        

def _strip_version(endpoint):
    """Strip version from the last component of endpoint if present."""
    if endpoint.endswith('/'):
        endpoint = endpoint[:-1]
    url_bits = endpoint.split('/')
    if re.match(r'v\d+\.?\d*', url_bits[-1]):
        endpoint = '/'.join(url_bits[:-1])
    return endpoint


def _get_keystone_client():
    return ksclient.Client(username=os.environ['OS_USERNAME'],
                           password=os.environ['OS_PASSWORD'],
                           tenant_name=os.environ['OS_TENANT_NAME'],
                           auth_url=os.environ['OS_AUTH_URL'])


def _get_neutron_client():
    keystone_client = _get_keystone_client()
    neutron_endpoint = _strip_version(
        keystone_client.service_catalog.url_for(
            service_type='network',
            endpoint_type='publicURL'
        )
    )
    return netclient.Client(endpoint_url=neutron_endpoint,
                            token=keystone_client.auth_token)


def _get_nova_client():
    return compclient.Client('2.1',
                             os.environ['OS_USERNAME'],
                             os.environ['OS_PASSWORD'],
                             os.environ['OS_TENANT_NAME'],
                             os.environ['OS_AUTH_URL'])


def _get_glance_client():
    keystone_client = _get_keystone_client()
    glance_endpoint = _strip_version(
        keystone_client.service_catalog.url_for(
            service_type='image',
            endpoint_type='publicURL'
        )
    )
    return gclient.Client(glance_endpoint, token=keystone_client.auth_token)


def _get_heat_client():
    keystone_client = _get_keystone_client()
    heat_endpoint = _strip_version(
        keystone_client.service_catalog.url_for(
            service_type='orchestration',
            endpoint_type='publicURL'
        )
    )
    return heatclient.Client('1', heat_endpoint, token=keystone_client.auth_token)


def _download_file(url):
    local_filename = url.split('/')[-1]
    cached_file = "%s/%s" % (os.environ['IMAGE_DIR'], local_filename)
    if os.path.isfile(cached_file):
        return cached_file
    r = requests.get(url)
    f = open(cached_file, 'wb')
    for chunk in r.iter_content(chunk_size=512 * 1024): 
        if chunk: 
            f.write(chunk)
    f.close()
    return cached_file


def _upload_image_to_glance(local_file_name, image_name, is_public):
    gc = _get_glance_client()
    img_model = gc.images.create(
        name=image_name,
        disk_format=DISKFORMAT,
        container_format=CONTAINERFORMAT,
        is_public=is_public,
        data=open(local_file_name, 'rb')
    )
    return img_model.id


def _get_import_image_id():
    gc = _get_glance_client()
    importer_id = None
    image_name = 'f5-Image-Importer'
    for image in gc.images.list():
        if image.name == image_name:
            importer_id = image.id
    if not importer_id:
        local_filename = _download_file(UBUNTU_IMAGE)
        importer_id = _upload_image_to_glance(local_filename,
                                              image_name,
                                              False)
    return importer_id


def _get_external_net_id():
    nc = _get_neutron_client()
    ext_id = None
    for net in nc.list_networks()['networks']:
        if net['router:external']:
            ext_id = net['id']
    return ext_id


def _allocate_floating_ip(port_id):
    ext_id = _get_external_net_id()
    if ext_id and port_id:
        floating_obj = { 'floatingip': { 'floating_network_id': ext_id, 'port_id': port_id } }
        nc = _get_neutron_client()
        floating_ip = nc.create_floatingip(floating_obj)
        return floating_ip['floatingip']['floating_ip_address']


def _create_web_server(download_server_image, ext_net):    
    image_importer_web_server_template = open(WEB_SERVER_TEMPLATE, 'r').read()
    hc = _get_heat_client()
    web_server_stack_id = hc.stacks.create(
          disable_rollback = True,
          parameters = { "external_network": ext_net, 
                         "web_app_image": download_server_image},
           stack_name = "image_importer_web_server",
           environment = {},
           template = image_importer_web_server_template
    )['stack']['id']
    stack_completed = ['CREATE_COMPLETE','CREATE_FAILED', 'DELETE_COMPLETE']
    print " "
    while True:
        stack = hc.stacks.get(web_server_stack_id)
        print '\tImage importer status is %s          \r'%stack.stack_status,
        if stack.stack_status in stack_completed:
            not_complete = False
            if stack.stack_status == 'CREATE_FAILED':
                print "Image importer web server create failed"
                sys.exit(1)
            if stack.stack_status == 'DELETE_COMPLETE':
                print "Image importer web server was deleted"
                sys.exit(1)
            break
            print('Heat complete')
        else:
            sys.stdout.flush()
            time.sleep(5)
    print " "
    return web_server_stack_id
    


def _is_port_open(ip, port):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.connect((ip, int(port)))
        s.shutdown(2)
        return True
    except:
        return False


def _make_bigip_zip_tar_file(bigip_images):
    tar_file_name = "%s/%s" % (os.environ['IMAGE_DIR'], BIGIP_TAR_IMAGE)
    tar = tarfile.open(tar_file_name, 'w')
    for image in bigip_images:
        tar.add(bigip_images[image]['file'],
                arcname=bigip_images[image]['archname'])
    tar.close()


def sftp_print_totals(transferred, toBeTransferred):
    percent_uploaded = 100 * float(transferred)/float(toBeTransferred)  
    print '\tTransferred: %d of %d bytes [%d%%]\r'% (transferred, toBeTransferred, int(percent_uploaded)),


def _upload_bigip_zips_to_web_server(web_server_floating_ip, bigip_images):
    print " "
    # wait for web server to answer SSH    
    while True:
        if _is_port_open(web_server_floating_ip, 22):
            print "\tSSH is reachable on web server\n"
            time.sleep(10)
            break
        time.sleep(5)
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(web_server_floating_ip, username='ubuntu', password='openstack')    
    ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command(
        'sudo rm /var/www/html/index.html'
    )
    for image in bigip_images:
        zip_file = bigip_images[image]['file']
        transport = paramiko.Transport((web_server_floating_ip, 22))
        transport.connect(username='ubuntu', password='openstack')
        scp = paramiko.SFTPClient.from_transport(transport)
        print "\tscp %s to server %s" % (zip_file, web_server_floating_ip)
        print " "
        scp.put(zip_file, '/tmp/%s' % image, callback=sftp_print_totals)
        print "\n"
        # deploy the image to the web servers
        ssh_stdin, ssh_stdout, ssh_stderr = ssh.exec_command(
            'sudo mv /tmp/%s /var/www/html/' % image
        )
        print "\tAvailable http://%s/%s" % (web_server_floating_ip, image)
        print "\n"
  

def _get_heat_output_value(stack_id, output_name):
    hc = _get_heat_client()
    stack = hc.stacks.get(stack_id)
    for output in stack.outputs:
        if output['output_key'] == output_name:
            return output['output_value']
    return None


def _create_glance_images(f5_heat_template_file, download_server_image,
                          web_server_stack_id, bigip_images):
    f5_image_template = open(f5_heat_template_file, 'r').read()
    image_prep_key = "importer_%s" % uuid.uuid4()
    cc = _get_nova_client()
    cc.keypairs.create(image_prep_key)
    print " "
    
    for image in bigip_images:
        
        image_name = bigip_images[image]['image']
        glance_image_name = image_name.replace('.qcow2', '')
        final_image_name = image.replace('.qcow2.zip', '')
 
        gc = _get_glance_client()
        create_image = True
        for uploaded_image in gc.images.list():
            if uploaded_image.name == final_image_name:
                create_image = False
        if not create_image:
            print "\tImage with name %s exists. Skipping." % final_image_name
            continue

        print "\tCreating image for %s" % image
        hc = _get_heat_client()
        private_network = _get_heat_output_value(web_server_stack_id,
                                                 'import_network_id')
        web_server_floating_ip = _get_heat_output_value(web_server_stack_id,
                                                        'web_server_public_ip')

        f5_ve_image_url = "http://%s/%s" % (web_server_floating_ip, image)
        image_stack_id = hc.stacks.create(
            disable_rollback = True,
            parameters = { "onboard_image": download_server_image, 
                           "flavor": "3",
                           "use_config_drive": True,
                           "private_network": private_network,
                           "f5_image_import_auth_url": os.environ['OS_AUTH_URL'],
                           "f5_image_import_tenant": os.environ['OS_TENANT_NAME'],
                           "f5_image_import_user": os.environ['OS_USERNAME'],
                           "f5_image_import_password": os.environ['OS_PASSWORD'],
                           "image_prep_url": "https://github.com/F5Networks/f5-openstack-image-prep.git",
                           "f5_ve_image_name": image_name,
                           "f5_ve_image_url": f5_ve_image_url,
                           "image_prep_key": image_prep_key,
                           "apt_cache_proxy_url": None
                         },               
            stack_name = "image_importer",
            environment = {},
            template = f5_image_template
        )['stack']['id']
        
        stack_completed = ['CREATE_COMPLETE','CREATE_FAILED', 'DELETE_COMPLETE']
        while True:
            stack = hc.stacks.get(image_stack_id)
            print '\tImage importer status is %s         \r'%stack.stack_status,
            sys.stdout.flush()
            if stack.stack_status in stack_completed:
                not_complete = False
                if stack.stack_status == 'CREATE_FAILED':
                    print "\tImage importer web server create failed           "
                    cc = _get_nova_client()
                    cc.keypairs.delete(image_prep_key)
                    sys.exit(1)
                if stack.stack_status == 'DELETE_COMPLETE':
                    print "\tImage importer web server was deleted             "
                    cc = _get_nova_client()
                    cc.keypairs.delete(image_prep_key)
                    sys.exit(1)
                break
            else:
                time.sleep(5)
        print " "
        print "\tSUCCESS - Image patched and uploaded."
        hc = _get_heat_client()
        hc.stacks.delete(image_stack_id)
        
        gc = _get_glance_client()      
        # Fix the name to reflect the actual BIG-IP release name
        for uploaded_image in gc.images.list():
            if uploaded_image.name == glance_image_name:
                image_properties = { 'os_vendor':'F5 Networks',
                                     'os_name':'F5 Traffic Management Operating System'} 
                for ve_type in VE_PROPS:
                    if final_image_name.find(ve_type) > -1:
                        image_properties.update(VE_PROPS[ve_type])
                
                min_disk = 0
                min_ram = 0
                
                for ve_type in VE_REQ:
                    if final_image_name.find(ve_type) > -1:
                        if 'min_disk' in VE_REQ[ve_type]:
                            min_disk = VE_REQ[ve_type]['min_disk']
                        if 'min_ram' in VE_REQ[ve_type]:
                            min_ram = VE_REQ[ve_type]['min_ram']
                
                gc.images.update(uploaded_image.id,
                                 name=final_image_name,
                                 is_public=True,
                                 min_disk=min_disk,
                                 min_ram=min_ram,
                                 properties=image_properties)
                
        
        # Add datastor if defined       
        if bigip_images[image]['datastor']:
            datastor_name = bigip_images[image]['datastor'].replace('.qcow2', '')
            create_datastor_image = True
            for uploaded_image in gc.images.list():
                if uploaded_image.name == datastor_name:
                    create_datastor_image = False
                    break
            if create_datastor_image:
                print "\tCreating Datastor image %s" % datastor_name
                vepackage = zipfile.ZipFile(bigip_images[image]['file'])
                vepackage.extract(bigip_images[image]['datastor'])
                gc.images.create(
                    name=datastor_name,
                    disk_format=DISKFORMAT,
                    container_format=CONTAINERFORMAT,
                    is_public=True,
                    data=open(bigip_images[image]['datastor'], 'rb'),
                    properties={
                        'os_vendor':'F5 Networks',
                        'os_name':'F5 TMOS Datastor Volume'}
                )
                os.unlink(bigip_images[image]['datastor'])       
        
        print "\n"

        # Let last image stack delete
        stack_completed = ['DELETE_COMPLETE']
        while True:
            stack = hc.stacks.get(image_stack_id)
            print '\tImage importer status is %s         \r'%stack.stack_status,
            sys.stdout.flush()
            if stack.stack_status in stack_completed:
                not_complete = False
                break
            else:
                time.sleep(5)

        
    cc = _get_nova_client()
    cc.keypairs.delete(image_prep_key)


def main():
    print "Finding F5 image zip archives"
    bigip_images = _make_bigip_inventory()
     
    if not bigip_images:
        print "No TMOS zip archives. Please place F5 zip files in the directory " \
              "associaed wtih ENV variable IMAGE_DIR"
        sys.exit(1)
    
    bigip_images = _images_needing_import(bigip_images)
    
    if not bigip_images:
        print "All images already imported"
        sys.exit(1)
    
    # external network
    print "Finding external networking"
    ext_net = _get_external_net_id()
    if not ext_net:
        print "No external network found. You need an network " \
              "with router:external attribute set to True"
        sys.exit(1)
    # get supported Image template
    print "Downloading F5 image patch Heat template"
    f5_heat_template_file = _download_file(F5_IMAGE_TEMPLATE)           
               
    # create the download glance image
    print "Getting image to build importer guest instance"
    download_server_image = _get_import_image_id()
    # create web server as an image repo
    print "Creating web server for F5 image repo"
    web_server_stack_id = _create_web_server(download_server_image, ext_net)
    web_server_floating_ip = _get_heat_output_value(web_server_stack_id,
                                                    'web_server_public_ip')
    print "\tweb server available at: %s         \n" % web_server_floating_ip
    # upload F5 images to the repo
    # print "Creating upload F5 image package for web server"
    # _make_bigip_zip_tar_file(bigip_images)
    print "Uploading F5 zip files to web server" 
    _upload_bigip_zips_to_web_server(web_server_floating_ip, bigip_images)
    
    # use the F5 supported Heat template to patch images
    print "Creating F5 images"
    _create_glance_images(f5_heat_template_file,
                          download_server_image,
                          web_server_stack_id,
                          bigip_images)
    hc = _get_heat_client()
    hc.stacks.delete(web_server_stack_id)
    gc = _get_glance_client()
    gc.images.delete(download_server_image)
    print "\n\nImages Imported Successfully\n"
    
if __name__ == "__main__":
    main()
