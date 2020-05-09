#!/usr/bin/env python3

import os, sys
import configparser
import argparse
import time
import json

import googleapiclient.discovery
from six.moves import input

gcpzones = ['us-west1-a','us-west1-b','us-central1-b','us-central1-c','us-central1-f',
            'us-east1-c','us-east1-d','europe-west1-c','europe-west1-d','asia-east1-b',
            'asia-east1-c','asia-northeast1-b','asia-northeast1-c']

configfile = "./hosts/fleet_setup.ini"
hostsfile = "./hosts/fleet_hosts.ini"

# [START list_instances]
def list_instances(compute, project, zone):
    result = compute.instances().list(project=project, zone=zone).execute()
    return result['items']
# [END list_instances]

# [START create_instance]
def create_instance(compute, project, zone, name, size):
    # Get the latest ubuntu image.

    image_response = compute.images().getFromFamily(
        project='ubuntu-os-cloud', family='ubuntu-1804-lts').execute()
    source_disk_image = image_response['selfLink']

    # Configure the machine
    if size == 'medium': 
        machine_type = "zones/%s/machineTypes/n1-standard-1" % zone
    elif size == 'small':
        machine_type = "zones/%s/machineTypes/g1-small" % zone
    elif size == 'large':
        machine_type = "zones/%s/machineTypes/n1-highmem-2" % zone

    image_url = "http://storage.googleapis.com/gce-demo-input/photo.jpg"
    image_caption = "Ready for dessert?"

    config = {
        'name': name,
        'machineType': machine_type,

        # Specify the boot disk and the image to use as a source.
        'disks': [
            {
                'boot': True,
                'autoDelete': True,
                'initializeParams': {
                    'sourceImage': source_disk_image,
                }
            }
        ],

        # Specify a network interface with NAT to access the public
        # internet.
        'networkInterfaces': [{
            'network': 'global/networks/default',
            'accessConfigs': [{'type': 'ONE_TO_ONE_NAT', 'name': 'External NAT'}]
        }],

        # Allow the instance to access cloud storage and logging.
        'serviceAccounts': [{
            'email': 'default',
            'scopes': [
                'https://www.googleapis.com/auth/devstorage.read_write',
                'https://www.googleapis.com/auth/logging.write'
            ]
        }],

        # Metadata is readable from the instance and allows you to
        # pass configuration from deployment scripts to instances.
        'metadata': {
            'items': [
            {
                'key': 'url',
                'value': image_url
            }, {
                'key': 'text',
                'value': image_caption
            }]
        }
    }

    return compute.instances().insert(
        project=project,
        zone=zone,
        body=config).execute()
# [END create_instance]

# [START wait_for_operation]
def wait_for_operation(compute, project, zone, operation):
    print('Waiting for operation to finish...')
    while True:
        result = compute.zoneOperations().get(
            project=project,
            zone=zone,
            operation=operation).execute()

        if result['status'] == 'DONE':
            print('done.')
            if 'error' in result:
                raise Exception(result['error'])
            return result

        time.sleep(1)
# [END wait_for_operation]



def setupapi(project, zone, instance_name, instance_size, wait=False):
    compute = googleapiclient.discovery.build('compute', 'v1')

    print('Creating instance {}'.format(instance_name))

    operation = create_instance(compute, project, zone, instance_name, instance_size)
    wait_for_operation(compute, project, zone, operation['name'])
    instances = list_instances(compute, project, zone)

    print('Instances in project {} and zone {}:'.format(project, zone))
    for instance in instances:
        print(' - ' + instance['name'])

    print('Instance {} is being created'.format(instance_name))


def setupconfig():
    print ("""\nThis script is entended to spin up a cloud instance
           of the brackets in the cloud, on a google cloud instance. 
           The setup is fast and automatic.""")
    askcontinue = input('Do wish to continue? Y/n: ')
    while askcontinue != "Y":
        if askcontinue == "Y":
            pass
        elif askcontinue == "n":
            sys.exit("Exiting")
        else:
            askcontinue = input('Do wish to continue? Y/n: ')

    print('\nGreat! Lets get some info.  A few questions:')
    print('What is your GCP username?  This user should be able to sudo.')
    useris = input("Username: ")

    print('\nWhat is your google instance ID?')
    print('You can find the id in GCP by clicking the project name like \"My First Project\"')
    idis = input("Google Project Id: ")

    print('\nWhat zone do you want these instances to land?:')
    print('See: https://cloud.google.com/compute/docs/regions-zones/regions-zones')
    print('Options are:') 
    print(gcpzones)
    print('\n')
    zoneis = input("Zone: ")

    print('\nThis script will spin up a single admiral and several chiefs')

    chieftrk = False
    chiefcnt = 0
    while chieftrk == False:
        try:
            chiefcnt = int(input("How many chiefs/workers do you want to create? [2-20]: "))
            if 2 <= chiefcnt <= 20:
                chieftrk = True
        except ValueError:
            print('Error: Numbers Only\n')
    chiefsize = 'small'
    
    config = configparser.ConfigParser()
    config['admiral'] = {'gcp_user': useris,
                       'gcp_project_id': idis,
                       'gcp_zone': zoneis,
                       'chief_number': chiefcnt,
                       'chief_size': chiefsize
                       }
    '''
    # This is for testing
    config['admiral'] = {'gcp_user': 'firewalleric@gmail.com',
                         'gcp_project_id': 'regal-autonomy-143002',
                         'gcp_zone': 'us-central1-c',
                         'chief_number': 3,
                         'chief_size': 'small'
                        } 
    '''
    with open(configfile, 'w') as cc:
        config.write(cc)


def getconfig():
    # Read the config file
    settings = configparser.ConfigParser()
    settings.read(configfile)

    config = {}
    for key in settings['admiral']:
        config.update({key: settings['admiral'][key]})
        
    return config

def setansiblehosts(apilisthosts): # updates the ansible hosts file
    all_config = getconfig()
    hwriter = open(hostsfile, 'w')

    chief_header_trk = True
    for apiresult in apilisthosts:
        vmname = apiresult['name']
        if vmname == 'brackets-admiral':
            hwriter.write('[{}]\n'.format('fleet-admiral'))
            admiralstr = 'admiral ansible_host={} ansible_port=22 ansible_user={}\n'.format(all_confg['natip'], all_config['gcp_user'])
            hwriter.write(admiralstr)
            hwriter.write('\n')
        elif '-chief' in str(apiresult['name']):
            chiefstr = '{} ansible_host={} ansible_port=22 \ 
                        ansible_user={}\n'.format(vmname, apiresult['natip'], all_config['gcp_user'])
            if chief_header_trk == True:
                hwriter.write('[{}]\n'.format('fleet-chief'))
                hwriter.write(chiefstr)
                chief_header_trk = False
            else:
                hwriter.write(chiefstr)
        else:
            pass

    hwriter.close()    

def main():
    
    if os.path.isfile(configfile): 
        apiconfig = getconfig()
    else:
        setupconfig()
        apiconfig = getconfig()

    # setup one admiral
    setupapi(apiconfig['gcp_project_id'],apiconfig['gcp_zone'],'brackets-admiral','small')

    pstart = 1
    pend = int(apiconfig['chief_number']) + 1
    while pstart != pend:
        print('Working on {}'.format(pstart))
        iname = 'brackets-chief' + str(pstart) 
        setupapi(apiconfig['gcp_project_id'],apiconfig['gcp_zone'],iname,'small')
        pstart += 1
    
    compute = googleapiclient.discovery.build('compute', 'v1')
    current_inst = list_instances(compute,apiconfig['gcp_project_id'],apiconfig['gcp_zone'])
    '''
    for network in current_inst:
        for interface in network['networkInterfaces']:
            for accessconfig in interface['accessConfigs']:
                natip = accessconfig['natIP']
                current_inst['natip'] = natip
        sys.exit()
    '''
    setansiblehosts(current_inst) # write new hosts file
      
    '''
    print('Waiting for instances to start')
    tstart = 1
    tstop = 100 
    while tstart != tstop:
        sys.stdout.write('\r')
        sys.stdout.write("[%-100s] %d%%" % ('='*tstart, 1*tstart))
        sys.stdout.flush()
        time.sleep(1)
        tstart += 1 
    print('\n')
    print('Configuring Fleet Via Ansible')
    '''


if __name__ == '__main__':
    main()

