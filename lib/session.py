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

import requests, json, base64 
from lib import projectconfig, configmanager
from lib import node
from lib.exceptions import *
from lib.logger import log

class Session:
    """
    Session class for logged in user.
    """
    def __init__(self):
        """
        Instantiate session for logged in user.
        """
        config = configmanager.Config()
        log.info("Initialising session for user " + config.get_token_attribute('email'))
        self.id_token = config.get_id_token()
        if self.id_token is None:
            raise InvalidConfigError
        self.__request_header = {'content-type': 'application/json', 'Authorization' : self.id_token}

    def get_nodes(self):
        """
        Get list of all nodes associated with the user.
        """
        log.info("Getting nodes associated with the user.")
        path = 'user/nodes'
        request_parameters = ''
        getnodes_url = projectconfig.HOST + path
        try:
            log.debug("Get nodes request url : " + getnodes_url)
            response = requests.get(url = getnodes_url, headers = self.__request_header)
            log.debug("Get nodes request response : " + response.text)
            response.raise_for_status()
        except requests.ConnectionError:
            raise NetworkError
        except:
            raise Exception(response.text)

        node_map = {}
        for nodeId in json.loads(response.text)['nodes']:
            node_map[nodeId] = node.Node(nodeId, self)
        log.info("Received nodes for user successfully.")
        return node_map

    def get_mqtt_host(self):
        """
        Get the MQTT Host endpoint.
        """
        log.info("Getting MQTT Host endpoint.")
        path = 'mqtt_host'
        request_url = projectconfig.HOST.split(projectconfig.VERSION)[0] + path
        try:
            log.debug("Get MQTT Host request url : " + request_url)
            response = requests.get(url = request_url)
            log.debug("Get MQTT Host resonse : " + response.text)
            response.raise_for_status()
        except requests.ConnectionError:
            raise NetworkError
        except Exception as getMqttHostError:
            raise getMqttHostError

        try:
            response = json.loads(response.text)
        except Exception as jsonDecodeError:
            raise jsonDecodeError

        if 'mqtt_host' in response:
            log.info("Received MQTT Host endpoint successfully.")
            return response['mqtt_host']
        return None
