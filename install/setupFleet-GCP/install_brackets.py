#!/usr/bin/env python3

import os, sys
import time
import json
import argparse
import fileinput
import subprocess
import configparser

from copy import deepcopy
import googleapiclient.discovery
from colorama import Fore, Back, Style
#from six.moves import input

gcpzones = ['us-west1-a','us-west1-b','us-central1-b','us-central1-c','us-central1-f',
            'us-east1-c','us-east1-d','europe-west1-c','europe-west1-d','asia-east1-b',
            'asia-east1-c','asia-northeast1-b','asia-northeast1-c']

configfile = './hosts/fleet_setup.ini'
hostsfile = './hosts/fleet_hosts.ini'
ansible_python = '/usr/bin/python3' # Ansible is python too and needs the system python not venv
temp_hostfile = hostsfile + '.temp'
fleet_spinup_pause = 30

def list_instances(compute, project, zone):
    result = compute.instances().list(project=project, zone=zone).execute()
    return result['items']

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
            }, {
                'vendor': 'leeward',
                'product': 'brackets'
            }]
        }
    }

    return compute.instances().insert(
        project=project,
        zone=zone,
        body=config).execute()

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

def setupconfig(gcp=False):
    ids = ''
    zoneis = ''
    cheifcnt = int()
    chiefsize = 'small'

    askcontinue = input('Installing Brackets...' + Fore.GREEN + '\nDo wish to continue? Y|n: ' + Style.RESET_ALL)
    while askcontinue != "Y":
        if askcontinue == "Y":
            pass
        elif askcontinue == "n":
            sys.exit("Exiting")
        else:
            askcontinue = input(Fore.GREEN + 'Do wish to continue? Y/n: ' + Style.RESET_ALL)

    print(Fore.GREEN + '\nGreat! Lets get some info.  A few questions:')
    print('What is your ssh username?  This user should be able to sudo.')
    useris = input("Username: " + Style.RESET_ALL)

    if gcp == True:
        print('\nWhat is your google project ID?')
        print('You can find the id in GCP by clicking the project name like \"My First Project\"')
        idis = input("Google Project Id: ")

        print('\nWhat zone do you want these instances to land?:')
        print('See: https://cloud.google.com/compute/docs/regions-zones/regions-zones')
        print('Options are:') 
        print(gcpzones)
        print('\n')
        zoneis = input("Zone: ")

    print(Fore.GREEN + '\nThis script will configure single admiral and/or several chiefs' + Style.RESET_ALL)

    chieftrk = False
    chiefcnt = 0
    while chieftrk == False:
        try:
            chiefcnt = int(input("How many chiefs/workers are there? [0-20 or more]: "))
            if 0 <= chiefcnt <= 20:
                chieftrk = True
        except ValueError:
            print('Error: Numbers Only\n')

    config = configparser.ConfigParser()
    if gcp == True:
        config['admiral'] = {'ssh_user': useris,
                            'gcp_project_id': idis,
                            'gcp_zone': zoneis,
                            'chief_number': chiefcnt,
                            'chief_size': chiefsize
                             }
    else:
        config['admiral'] = {'ssh_user': useris,
                            'chief_number': chiefcnt}

    with open(configfile, 'w') as cc:
        config.write(cc)

def getconfig():
    # Read the config file
    settings = configparser.ConfigParser()
    settings.read(configfile)

    config = {}
    for key in settings['admiral']:
        config.update({key: settings['admiral'][key]})
        
    return config # returns dict

def set_fleet_hosts(): # Updates hosts file that's not GCP
    all_config = getconfig()
    hwriter = open(temp_hostfile, 'w')

    admiral_ip = input(Fore.GREEN + "What IP or Hostname of Admiral: " + Style.RESET_ALL)
    hwriter.write('[{}]\n'.format('fleetAdmiral'))
    admiralstr = 'admiral ansible_host={} ansible_port=22 ansible_user={}\n'.format(admiral_ip, all_config['ssh_user'])
    hwriter.write(admiralstr)
    hwriter.write('\n')

    print(Fore.BLUE + '\nConfiguring Chiefs....' + Style.RESET_ALL)

    if int(all_config['chief_number']) == 0:
        return(None)
    
    start_count = 1
    hwriter.write('[{}]\n'.format('fleetChiefs'))
    while start_count <= int(all_config['chief_number']):
        brack_name = "brackets-chief" + str(start_count)
        print(Fore.GREEN + "Configuring {}".format(brack_name))
        chief_host = input("What is the ip or hostname of {}? : ".format(brack_name) + Style.RESET_ALL)
        hwriter.write('{} ansible_host={} ansible_port=22 ansible_user={}\n'.format(brack_name, chief_host, all_config['ssh_user']))
        start_count += 1

    hwriter.close()
    os.replace(temp_hostfile, hostsfile)

def set_gcp_hosts(brak_name, brak_ssh_iphost): # updates the ansible hosts file
    all_config = getconfig()
    hwriter = open(temp_hostfile, 'a')

    with open(temp_hostfile) as th:
        temp_host_data = th.readlines()
    
    if brak_name == 'brackets-admiral': # write admiral header
        if '[fleetAdmiral]\n' in temp_host_data:
            pass
        else:
            hwriter.write('[{}]\n'.format('fleetAdmiral'))
        
    # write admiral host
        admiralstr = 'admiral ansible_host={} ansible_port=22 ansible_user={}\n\n'.format(brak_ssh_iphost, all_config['ssh_user'])
        hwriter.write(admiralstr)
        
    else: # write chief header
        if '[fleetChiefs]\n' in temp_host_data:
            pass
        else:
            hwriter.write('[{}]\n'.format('fleetChiefs'))
        
        
        hwriter.write('{} ansible_host={} ansible_port=22 ansible_user={}\n'.format(brak_name, brak_ssh_iphost, all_config['ssh_user']))

    hwriter.close()

def buildinstances(project_id, zone, chief_count):
    ''' Build Instances '''
    # setup one admiral
    setupapi(project_id, zone, 'brackets-admiral','small')
    
    # Build Chiefs
    pstart = 1
    pend = int(chief_count) + 1
    while pstart != pend:
        print('Working on {}'.format(pstart))
        iname = 'brackets-chief' + str(pstart) 
        setupapi(project_id, zone,iname,'small')
        pstart += 1
    ### Finish Building ###

def show_hosts(showfile=hostsfile):
    print('    ########### Brackets Ansible Hosts File ###############')
    for line in fileinput.input(showfile):
        kfline = line.rstrip()
        print('    ' + kfline)
    print('    #######################################################')
        
def update_gcp_hosts(apiconfig):
    ### Query Inventory & Fix Hosts File With IP ###
    compute = googleapiclient.discovery.build('compute', 'v1')
    current_inst = list_instances(compute,apiconfig['gcp_project_id'],apiconfig['gcp_zone'])
    
    # Skip any non brackets instances
    for instance in current_inst:
        if instance['name'].startswith('brackets-'):
            pass
        else:
            continue

        # Get name, external nat, if there is not external nat use the internal ip
        brack_name = instance['name']
        access_ip = instance['networkInterfaces'][0]['networkIP']
        nat_ip = instance['networkInterfaces'][0]['accessConfigs'][0]['natIP']
        set_gcp_hosts(brack_name, nat_ip) # write new hosts file

    # Moving tempfile to  ansible hostsfile
    os.replace(temp_hostfile, hostsfile)
 
def ping_hosts():
    print('\n' + Fore.GREEN + 'Pinging Fleet Now...' + Style.RESET_ALL)
    status = False
    ping_cmd = [ ansible_python, '/usr/local/bin/ansible', '-i', hostsfile, 'all', '-m', 'ping']
    pingit = subprocess.run(ping_cmd, stdout=subprocess.PIPE, text=True)
    if pingit.returncode == 0:
        print(Fore.BLUE + "PASS: SSH connectivity to fleet successfull" + Style.RESET_ALL)
        status = True
    else:
        print(Fore.RED + "ERROR: SSH connectivity fleet failed, check your hosts file and try again\n" + Style.RESET_ALL)
        print(Fore.RED + pingit.stdout + Style.RESET_ALL)
    
    return(status)

def standup_fleet():
    
    fleet_cmd = [ ansible_python, '/usr/local/bin/ansible-playbook', '-i', hostsfile, './brackets.yml']
    fleet_deploy = subprocess.Popen(fleet_cmd, text=True, stdout=subprocess.PIPE)

    while True:
        output = fleet_deploy.stdout.readline()
        if output == '' and fleet_deploy.poll() is not None:
            break
        if output:
            if output.startswith('ok:'):
                print(Fore.GREEN + output.strip())
            elif output.startswith('changed:'):
                print(Fore.YELLOW + output.strip())
            elif output.startswith('skipping:'):
                print(Fore.BLUE + output.strip())
            elif output.startswith('fatal:'):
                print(Fore.RED + output.strip() + Style.RESET_ALL)
            else:
                print(Style.RESET_ALL + output.strip())
    print(Style.RESET_ALL)
    rc = fleet_deploy.poll()
    return(True)
        
def menu_option():
    max_option=8 # should always be +1 of the options below
    options = range(1,max_option)
    selection = int()

    while True:
        print()
        print(Fore.GREEN + 'Brackets Menu: Select Option' + Style.RESET_ALL)
        print('  1 - Install Brackets on 1 or more Ubuntu-18 VMs, instances or servers')
        print('  2 - Install Brackets on GCP from scratch (spin up & install)')
        print('  3 - View active hosts file')
        print('  4 - Update GCP nodes')
        print('  5 - Check connectivity to fleet')
        print('  6 - Run playbooks again on fleet')
        print('  7 - Exit Now')
        print()
        
        selection = int(input(Fore.GREEN + 'Select Option: ' + Style.RESET_ALL))
        if selection in options:
            return(selection)
        else:
            print(Fore.RED + "Error: Please select option {}".format(list(options)) + Style.RESET_ALL)
            
def main():
    # Clean up any old temp files
    if os.path.exists(temp_hostfile):
        os.remove(temp_hostfile)

    set_option = int()
    try:
        while True:
            set_option = menu_option() 

            if set_option == 1:
                print('Running setup')
                if os.path.isfile(configfile): 
                    print(Fore.YELLOW + 'WARNING' + Fore.BLUE)
                    show_hosts()
                    print(Fore.YELLOW + 'Found existing brackets hosts')
                    overwrite = input('Do you want to overwrite this? y|n: ' + Style.RESET_ALL)

                    if overwrite == 'y':
                        setupconfig()
                        set_fleet_hosts()
                    apiconfig = getconfig()
                else:
                    setupconfig()
                    apiconfig = getconfig()
                standup_fleet()

            elif set_option == 2:
                print("Setup and install on gcp")
                setupconfig(gcp=True)
                apiconfig = getconfig()
                buildinstances(apiconfig['gcp_project_id'], apiconfig['gcp_zone'], apiconfig['chief_number'])
                update_gcp_hosts(apiconfig)
                print(Fore.CYAN + "Waiting for fleet to spin up")
                start_pause = deepcopy(fleet_spinup_pause) 
                while True:
                    if start_pause == 0:
                        break
                    else:
                        print(start_pause)
                        time.sleep(1.2)
                        start_pause -= 1

                while True:
                    ping_status = ping_hosts()
                    if ping_status == True: # Waiting for ping to succeed
                        standup_fleet()
                        break
                    else:
                        print('Waiting')
                        time.sleep(10)

            elif set_option == 3:
                show_hosts(hostsfile)

            elif set_option == 4:
                print('Update gcp fleet hosts file')
                update_gcp_hosts(getconfig())
                show_hosts(hostsfile)

            elif set_option == 5:
                ping_hosts()

            elif set_option == 6:
                fleet_status = standup_fleet()

            elif set_option == 7:
                print(Fore.GREEN + 'Option 7: Exit' + Style.RESET_ALL)
                sys.exit()

            else:
                pass
               
    except KeyboardInterrupt:
        sys.exit(Fore.GREEN + '\nExit...' + Style.RESET_ALL)


if __name__ == '__main__':
    main()

