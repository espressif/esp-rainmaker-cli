#!/usr/bin/env python3
#
# Copyright 2019 Espressif Systems (Shanghai) PTE LTD
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import uuid, urllib
import time
import requests
import getpass
from requests.exceptions import HTTPError
import json
from constants import *
from config import *
from pathlib import Path
from logger import log
from utility import getHeader
from packaging import version
import sys
try:
    from tools.esp_cloud_user_assoc_prov import provision_device
except Exception as err :
    if version.parse(google.protobuf.__version__) < version.parse(MINIMUM_PROTOBUF_VERSION):
        print("Package protobuf does not satisfy the minimum required version.\n"
                "Minimum required version is " + MINIMUM_PROTOBUF_VERSION)
    else :
        print("Provisining failed due to import error")

def provision(args):
    """
        Does the provisioning of the node
        :param args:
        a) pop  - Proof of possesion for the node
        b) ssid - SSID of the wifi network (optional)
        :return:
        pass - Acknowledges for the successful provision
        fail - Prints error message and exit
    """
    log.info('Doing the provisioning of the node')
    secret_key = str(uuid.uuid4())
    pop = args.pop
    userid = getUserId()
    if userid is None:
        print("\n==== Provisioning was failed. Please try again ====")
        return
    input("Please connect to the wifi PROV_XXXXXX and Press Enter to continue...")

    if args.ssid is not None: 
        password = getpass.getpass("Enter Wi-Fi password : ")
        nodeId = provision_device(TRANSPORT_MODE_SOFTAP, pop, userid, secret_key, args.ssid, password)
    else:
        nodeId = provision_device(TRANSPORT_MODE_SOFTAP, pop, userid, secret_key)
    
    if nodeId is None:
        return

    print("\n==== Adding user-node association ====")
    retries = MAX_CONNECTION_RETRIES
    while retries > 0:
        time.sleep(5)
        requestId = add_user_node_mapping(userid, nodeId, secret_key)
        if requestId is not None:
            break
        retries -= 1
    if requestId is None:
        print("\n==== Adding user-node mapping failed. Please check the internet connectivity ====")
        return
    print("==== Added user-node association successfully ====")

    print("\n==== Checking user-node association status ====")
    retries = MAX_CONNECTION_RETRIES
    while retries > 0:
        time.sleep(5)
        status = get_mapping_status(userid, nodeId, requestId)
        if status == 'confirmed':
            break
        retries -= 1
    if status is None:
        print("\n==== Checking user-node association status failed. Please check the internet connectivity ====")
        return
    elif status == 'requested':
        print("\n==== User-node association is not confirmed ====")
        return
    print("==== User-node association confirmed ====")


def add_user_node_mapping(userid, nodeid, secret_key):
    """
        Adds the user node mapping request from the user side
        :param args:
        a) userid     - Unique identity of the user
        b) nodeid     - Unique identity of the node
        c) secret_key - Secret key on which both node and user agrees
        :return:
        pass - RequestId for the user node mapping request
        fail - Prints error message and exit
    """
    log.info("Adding user node mapping from user, userid = " + userid + " nodeid = " + nodeid)

    path = CLI_PATH_PREFIX + 'user/nodes/mapping'
    request_parameters = ''
    request_payload = { 'user_id' : userid,
                        'node_id' : nodeid,
                        'secret_key': secret_key,
                        'operation' : ADD_OPERATION }

    request_header = getHeader(PUT_METHOD, path, request_parameters, json.dumps(request_payload))
    request_url = HTTPS_PREFIX + HOST + path

    try:
        response = requests.put(url = request_url, data = json.dumps(request_payload), headers=request_header)        
        response.raise_for_status()                 # If the response was successful, no Exception will be raised

    except HTTPError as http_err:
        log.error(f'Adding user node mapping failed\n {http_err}')
        return None

    except Exception as err:
        log.error(f'Adding user node mapping failed : {err}')
        return None
    try:
        response = json.loads(response.text)
    except Exception as err:
        print(ERROR_JSON_DECODE)
        log.error(f'Decoding getnodes response failed : {err}')
        return None

    if 'request_id' in response:
        log.info("User node mapping requestId = " + response['request_id'])
        return response['request_id']


def get_mapping_status(userid, nodeid, request_id):
    """
        Checks the status of user node mapping request
        :param args:
        a) userid     - Unique identity of the user
        b) nodeid     - Unique identity of the node
        c) request_id - RequestId for the user node mapping request
        :return:
        pass - Request status for the user node mapping request
        fail - Prints error message and exit
    """
    log.info("Getting status of user-node mapping request, userid = " + userid + " nodeid = " + nodeid)
    path = CLI_PATH_PREFIX + 'user/nodes/mapping'
    request_parameters = "node_id=" + nodeid + "&request_id=" + request_id + "&user_request=true" + "&userid=" + userid

    request_header = getHeader(GET_METHOD, path, request_parameters)
    request_url = HTTPS_PREFIX + HOST + path + QUESTION_MARK + request_parameters

    try:
        response = requests.get(url = request_url, headers=request_header)
        response.raise_for_status()                 # If the response was successful, no Exception will be raised

    except HTTPError as http_err:
        log.error(f'Getting status of user-node mapping request failed\n {http_err}')
        return None

    except Exception as err:
        log.error(f'Getting status of user-node mapping request failed : {err}')
        return None

    try:
        response = json.loads(response.text)
    except Exception as err:
        print(ERROR_JSON_DECODE)
        log.error(f'Decoding getMapping_status response failed : {err}')
        return None

    if 'request_status' in response:
        log.info("User node mapping request status = " + response['request_status'])
        print("++++ Status : " + response['request_status'] + " ++++")
        return response['request_status']

def getUserId():
    """
        Returns the userId of the user
    """

    log.info("Inside getUserId function ")
    
    path = CLI_PATH_PREFIX + 'user'
    request_parameters = ''
    request_header = getHeader(GET_METHOD, path, request_parameters)
    
    getuser_url = HTTPS_PREFIX + HOST + path
 
    try:
        response = requests.get(url = getuser_url, headers=request_header)
        response.raise_for_status()

    except HTTPError as http_err:
        log.error(f'Getting user info failed\n{http_err}')
   
    except requests.ConnectionError:
        print("Please check the internet connectivity. No internet connection available")
        sys.exit(1)

    except Exception as err:
        log.error(f'Getting user info failed\n{err}')

    try:
        response = json.loads(response.text)
    except Exception as err:
        print(ERROR_JSON_DECODE)
        log.error(f'Decoding getUserId response failed : {err}')
        return None
        
    if 'user_id' in response:
        log.info("Getting userid for user successful, userid = " + response['user_id'])
        return response['user_id']