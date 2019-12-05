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

import json, re, sys
import requests
from constants import *
from config import *
from utility import getHeader
from pathlib import Path
from logger import log
from requests.exceptions import HTTPError
from tools.esp_cloud_user_assoc_prov import provision_device


def getNodes(args):
    """
        List all nodes associated with the user
        :return:
        pass - Prints request response
        fail - None
    """

    log.info("Inside getnodes function ")
    
    path = CLI_PATH_PREFIX + 'user/nodes/mapping'
    request_parameters = ''
    request_header = getHeader(GET_METHOD, path, request_parameters)
    
    getnodes_url = HTTPS_PREFIX + HOST + path 
    try:
        response = requests.get(url = getnodes_url, headers = request_header)
        response.raise_for_status()

    except HTTPError as http_err:
        log.error(f'Getting nodes failed\n{http_err}')
    
    except requests.ConnectionError:
        print("Please check the internet connectivity. No internet connection available")
        sys.exit(1)

    except Exception as err:
        log.error(f'Getting nodes failed\n{err}')

    try:
        response = json.dumps(json.loads(response.text), indent=4)
    except Exception as err:
        print(ERROR_JSON_DECODE)
        log.error(f'Decoding getnodes response failed : {err}')
        return None

    log.info("Nodes for the user " + " : " + "\n" + response)
    print(response)

def getNodeConfig(args):
    """
        Shows the configuration of the node
        :param args:
        a) nodeid - Node Id for the node
        :return:
        pass - Prints request response
        fail - None
    """
    nodeid = args.nodeId
    log.info("Inside getnodeconfig function, nodeid : " + nodeid)

    path = CLI_PATH_PREFIX + 'user/nodes/config'
    request_parameters = 'nodeid=' + nodeid
    request_header = getHeader(GET_METHOD, path, request_parameters)

    getnodeconfig_url = HTTPS_PREFIX + HOST + path + QUESTION_MARK + request_parameters
    try:
        response = requests.get(url = getnodeconfig_url, headers=request_header)
        response.raise_for_status()

    except HTTPError as http_err:
        log.error(f'Getting nodeconfig failed\n{http_err}')
    
    except requests.ConnectionError:
        print("Please check the internet connectivity. No internet connection available")
        sys.exit(1)

    except Exception as err:
        log.error(f'Getting nodeconfig failed\n{err}')

    try:
        response = json.dumps(json.loads(response.text), indent=4)
    except Exception as err:
        print(ERROR_JSON_DECODE)
        log.error(f'Decoding getNodeConfig response failed : {err}')
        return None

    log.info("Node config for " + nodeid + " : " + "\n" + response)
    print(response)

def setParams(args):
    """
        Sets the desired state of the node
        :param args:
        a) nodeid   - Node Id for the node
        b) data     - Json data containing parameters to be set
        c) filePath - Path of the json file conatining parameters to be set
        :return:
        pass - Prints request response
        fail - None
    """
    data = args.data
    filepath = args.filepath
    nodeid = args.nodeid
    log.info("Inside setdynamicparams function, nodeid = " + nodeid)

    if data is None and filepath is None:
        print("Please enter json data or json file path to set the parameters of the node")
        log.error("json data or json file path to set the parameters is not provided")
        return None
    
    if data is not None:
        #Trimming white spaces
        data = re.sub(r"[\n\t\s]*", "", data)
        try:
            data = json.loads(data)
        except Exception as err:
            print(ERROR_JSON_DECODE)
            log.error(f'Decoding JSON file failed : {err}')
            return None
    
    elif filepath is not None:
        file = Path(filepath)
        if not file.exists():
            print("Oops, file %s doesn't exist!" % file.name)
            return None
        with open(file) as fh:
            try:
                data = json.load(fh)
            except Exception as err:
                print(ERROR_JSON_DECODE)
                log.error(f'Decoding JSON file failed : {err}')
                return None

    path = CLI_PATH_PREFIX + 'user/nodes/dynamic_params'
    request_parameters = 'nodeid=' + nodeid

    request_header = getHeader(PUT_METHOD, path, request_parameters, json.dumps(data))
    setdynamicparams_url = HTTPS_PREFIX + HOST + path + QUESTION_MARK + request_parameters

    try:
        response = requests.put(url = setdynamicparams_url, data = json.dumps(data), headers=request_header)
        response.raise_for_status()

    except HTTPError as http_err:
        log.error(f'Setting dynamicparams failed\n{http_err}')

    except requests.ConnectionError:
        print("Please check the internet connectivity. No internet connection available")
        sys.exit(1)
     
    except Exception as err:
        log.error(f'Setting dynamicparams failed\n{err}')
 
    try:
        response = json.dumps(json.loads(response.text), indent=4)
    except Exception as err:
        print(ERROR_JSON_DECODE)
        log.error(f'Decoding setParams response failed : {err}')
        return None
    
    print(response)
    log.info("Dynamic params of the node updated successfully, nodeid = " + nodeid)


def getParams(args):
    """
        Shows the reported state of the node
        :param args:
        a) nodeid  - Node Id for the node
        :return:
        pass - Prints request response
        fail - None
    """
    nodeid = args.nodeId
    log.info("Inside getParams function, nodeid : " + nodeid)

    path = CLI_PATH_PREFIX + 'user/nodes/dynamic_params'
    request_parameters = 'nodeid=' + nodeid
    request_header = getHeader(GET_METHOD, path, request_parameters)

    getdynamicparams_url = HTTPS_PREFIX + HOST + path + QUESTION_MARK + request_parameters
    try:
        response = requests.get(url = getdynamicparams_url, headers=request_header)
        response.raise_for_status()

    except HTTPError as http_err:
        log.error(f'Getting dynamic params for node failed\n{http_err}')

    except requests.ConnectionError:
        print("Please check the internet connectivity. No internet connection available")
        sys.exit(1)
     
    except Exception as err:
        log.error(f'Getting dynamic params for node failed\n{err}')

    try:
        response = json.dumps(json.loads(response.text), indent=4)
    except Exception as err:
        print(ERROR_JSON_DECODE)
        log.error(f'Decoding getParams response failed : {err}')
        return None

    log.info("Current state of the node : " + response)
    print(response)

def getMqttHost(args) :
    # Need to write backend API to get the endpoint. For now it is hard coded
    print("MQTT Host :", AWS_IOT_ENDPOINT)
    sys.exit(0)