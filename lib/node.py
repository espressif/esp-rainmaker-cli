# Copyright 2020 Espressif Systems (Shanghai) PTE LTD
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

import requests, json, uuid, getpass
from lib import projectconfig, configmanager, device
from lib.exceptions import *
from lib.logger import log

class Node:
    """
    Node class used to instantiate instances of node to perform various node operations.
    """
    def __init__(self, nodeId, session):
        """
        Instantiate node with nodeId and session object.
        """
        log.info("Initialising node with nodeId : " + nodeId)
        self.__nodeId = nodeId
        self.__session = session
        self.__request_header = {'content-type': 'application/json', 'Authorization' : session.id_token}

    def get_node_config(self):
        """
        Get node configuration.
        """
        log.info("Getting node config for node : " + self.__nodeId)
        path = 'user/nodes/config'
        query_parameters = 'nodeid=' + self.__nodeId
        getnodeconfig_url = projectconfig.HOST + path + '?' + query_parameters
        try:
            log.debug("Get node config request url : " + getnodeconfig_url)
            response = requests.get(url = getnodeconfig_url, headers=self.__request_header)
            log.debug("Get node config response : " + response.text)
            response.raise_for_status()
        except requests.ConnectionError:
            raise NetworkError
        except:
            raise Exception(response.text)
        log.info("Received node config successfully.")
        return response.json()

    def get_nodeid(self):
        return self.__nodeId

    def get_devices(self):
        """
        Get list of devices associated with the node.
        """
        log.info("Getting list of devices associated with the node.")
        nodeInfo = self.get_node_config()
        device_map = {}
        for device in nodeInfo['devices']:
            device_map[device['name']] = device.Device(self, device)
        log.info("Received list of devices successfully.")
        return device_map

    def get_node_params(self):
        """
        Get parameters of the node.
        """
        log.info("Getting parameters of the node with nodeId : " + self.__nodeId)
        path = 'user/nodes/params'
        query_parameters = 'nodeid=' + self.__nodeId
        getparams_url = projectconfig.HOST + path + '?' + query_parameters
        try:
            log.debug("Get node params request url : " + getparams_url)
            response = requests.get(url = getparams_url, headers=self.__request_header)
            log.debug("Get node params response : " + response.text)
            response.raise_for_status()
        except requests.ConnectionError:
            raise NetworkError
        except:
            raise Exception(response.text)

        response = json.loads(response.text)
        if 'status' in response and response['status'] == 'failure':
            return None
        log.info("Received node parameters successfully.")
        return response

    def set_node_params(self, data):
        """
        Set parameters of the node.
        Input data contains the dictionary of node parameters.
        """
        log.info("Updating parameters of the node with nodeId : " + self.__nodeId)
        path = 'user/nodes/params'
        query_parameters = 'nodeid=' + self.__nodeId
        setparams_url = projectconfig.HOST + path + '?' + query_parameters
        try:
            log.debug("Set node params request url : " + setparams_url)
            log.debug("Set node params request payload : " + json.dumps(data))
            response = requests.put(url = setparams_url, data = json.dumps(data), headers=self.__request_header)
            log.debug("Set node params response : " + response.text)
            response.raise_for_status()
        except requests.ConnectionError:
            raise NetworkError
        except:
            raise Exception(response.text)
        log.info("Updated node parameters successfully.")
        return True

    def __user_node_mapping(self, secret_key, operation):
        """
        Add or remove the user node mapping.
        Argument operation can take values 'add' or 'remove'.
        """
        path = 'user/nodes/mapping'
        config = configmanager.Config()
        userid = config.get_user_id()
        request_payload = { 
            'user_id'   : userid,
            'node_id'   : self.__nodeId,
            'secret_key': secret_key,
            'operation' : operation 
            }

        request_url = projectconfig.HOST + path
        try:
            log.debug("User node mapping request url : " + request_url)
            log.debug("User node mapping request payload : " + str(request_payload))
            response = requests.put(url = request_url, data = json.dumps(request_payload), headers=self.__request_header)
            log.debug("User node mapping response : " + response.text)
            response.raise_for_status()
        except requests.ConnectionError:
            raise NetworkError
        except:
            raise Exception(response.text)

        try:
            response = json.loads(response.text)
        except Exception as userNodeMappingError:
            raise userNodeMappingError

        if 'request_id' in response:
            return response['request_id']
        return None
    
    def add_user_node_mapping(self, secret_key):
        """
        Add user node mapping request.
        """
        log.info("Adding user node mapping request with nodeId : " + self.__nodeId)
        return self.__user_node_mapping(secret_key, 'add')

    def remove_user_node_mapping(self):
        """
        Remove user node mapping request.
        """
        log.info("Removing user node mapping with nodeId : " + self.__nodeId)
        secret_key = ""
        return self.__user_node_mapping(secret_key, 'remove')
    
    def get_mapping_status(self, requestId):
        """
        Check status of user node mapping request.
        request_id of the user-node mapping request is needed to check the status.
        """
        log.info("Checking status of user node mapping with requestId : " + requestId)
        path = 'user/nodes/mapping'
        query_parameters = "&request_id=" + requestId 

        request_url = projectconfig.HOST + path + '?' + query_parameters
        try:
            log.debug("Check user node mapping status request url : " + request_url)
            response = requests.get(url = request_url, headers=self.__request_header)
            log.debug("Check user node mapping status response : " + response.text)
            response.raise_for_status()
        except requests.ConnectionError:
            raise NetworkError
        except Exception as getMappingStatusError:
            raise getMappingStatusError

        try:
            response = json.loads(response.text)
        except Exception as getMappingStatusError:
            raise getMappingStatusError

        if 'request_status' in response:
            return response['request_status']
        return None