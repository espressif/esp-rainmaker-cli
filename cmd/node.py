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

import json, re, sys
import requests
from pathlib import Path

try:
    from lib import session, node, projectconfig
    from lib.exceptions import *
    from lib.logger import log
except Exception as importError:
    print("Failed to import ESP Rainmaker library. " + importError)
    sys.exit(1)

from tools.esp_rainmaker_claim.claim import claim

def get_nodes(args):
    """
    List all nodes associated with the user.
    """
    try:
        s = session.Session()
        nodes = s.get_nodes()
    except Exception as getNodesError:
        log.error(getNodesError)
    else:
        if len(nodes.keys()) == 0:
            print('User is not associated with any nodes.')
            return
        for key in nodes.keys():
            print(nodes[key].get_nodeid())
    return

def get_node_config(args):
    """
    Shows the configuration of the node.
    :param args:
    a) nodeId - Node ID for the node
    """
    try:
        n = node.Node(args.nodeId, session.Session())
        nodeConfig = n.get_node_config()
    except Exception as getNodesError:
        log.error(getNodesError)
    else:
        print(json.dumps(nodeConfig, indent=4))
    return

def set_params(args):
    """
    Set parameters of the node.
    :param args:
    a) nodeId   - Node ID for the node
    b) data     - JSON data containing parameters to be set
    c) filepath - Path of the JSON file containing parameters to be set
    """
    log.info('Setting params of the node with nodeId : ' + args.nodeId)
    data = args.data
    filepath = args.filepath
    
    if data is not None:
        log.debug('Setting node parameters using JSON data.')
        #Trimming white spaces
        data = re.sub(r"[\n\t\s]*", "", data)
        try:
            log.debug('JSON data : ' + data)
            data = json.loads(data)
        except Exception as jsonLoadError:
            raise InvalidJSONError
            return
    
    elif filepath is not None:
        log.debug('Setting node parameters using JSON file.')
        file = Path(filepath)
        if not file.exists():
            log.error('File %s does not exist!' % file.name)
            return
        with open(file) as fh:
            try:
                data = json.load(fh)
                log.debug('JSON filename :' + file.name)
            except Exception as jsonLoadError:
                raise InvalidJSONError
                return

    try:
        n = node.Node(args.nodeId, session.Session())
        status = n.set_node_params(data)
    except Exception as setParamsError:
        log.error(setParamsError)
    else:
        print('Node state updated successfully.')
    return
    
def get_params(args):
    """
    Get parameters of the node.
    :param args:
    a) nodeId  - Node ID for the node
    """
    try:
        n = node.Node(args.nodeId, session.Session())
        params = n.get_node_params()
    except Exception as getParamsError:
        log.error(getParamsError)
    else:
        if params is None:
            log.error('Node does not have updated its state.')
            return
        print(json.dumps(params, indent=4))
    return
    
def remove_node(args):
    """
    Removes the user node mapping.
    :param args:
    a) nodeId  - Node ID for the node
    """
    log.info('Removing user node mapping for node ' + args.nodeId)
    try:
        n = node.Node(args.nodeId, session.Session())
        params = n.remove_user_node_mapping()
    except Exception as removeNodeError:
        log.error(removeNodeError)
    else:
        log.debug('Removed the user node mapping successfully.')
        print('Removed node ' + args.nodeId + ' successfully.')
    return

def get_mqtt_host(args) :
    """
    Returns MQTT Host enpoint
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
        return
    except Exception as getMqttHostError:
        log.error(getMqttHostError)
        return
    try:
        response = json.loads(response.text)
    except Exception as jsonDecodeError:
        log.error(jsonDecodeError)
    if 'mqtt_host' in response:
        log.info("Received MQTT Host endpoint successfully.")
        print(response['mqtt_host'])
    else:
        log.error("MQTT Host does not exists.")
    return

def claim_node(args):
    """
    Claims the ESP32-S2 (Get Cloud credentials).
    :param args:
    a) port - Serial Port connected to the device
    """
    try:
        claim(args.port)
    except Exception as claimError:
        log.error(claimError)
        return