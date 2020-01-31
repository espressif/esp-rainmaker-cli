# Copyright 2020 Espressif Systems (Shanghai) PTE LTD
#
# Licensed under the Apache License, Version 2.0 (the "License');
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

import uuid, urllib
import time
import getpass
import json
from pathlib import Path
from packaging import version
import sys

try:
    from lib.logger import log
    from lib import session, configmanager, node
    from lib.exceptions import NetworkError
except Exception as importError:
    print("Failed to import ESP Rainmaker library. " + importError)
    sys.exit(1)

MINIMUM_PROTOBUF_VERSION = '3.10.0'
TRANSPORT_MODE_SOFTAP = 'softap'
MAX_HTTP_CONNECTION_RETRIES = 5

def provision(args):
    """
    Does the provisioning of the node.
    :param args:
    a) pop  - Proof of possesion for the node
    """
    try:
        from tools.esp_rainmaker_prov.esp_rainmaker_prov import provision_device
    except Exception as importError :
        import google.protobuf
        if version.parse(google.protobuf.__version__) < version.parse(MINIMUM_PROTOBUF_VERSION):
            log.warn('Package protobuf does not satisfy the minimum required version.\n'
                    'Minimum required version is ' + MINIMUM_PROTOBUF_VERSION)
        else :
            log.error('Provisioning failed due to import error.', importError)
            sys.exit(1)
    log.info('Provisioning the node.')
    secret_key = str(uuid.uuid4())
    pop = args.pop
    try:
        config = configmanager.Config()
        userid = config.get_user_id()
        log.debug('User session is initialized for the user ' + userid)
    except Exception as getUserIdError:
        log.error(getUserIdError)
        sys.exit(1)
    try:
        input('Please connect to the wifi PROV_XXXXXX and Press Enter to continue...')
    except:
        print("Exiting...")
        sys.exit(0)

    nodeId = provision_device(TRANSPORT_MODE_SOFTAP, pop, userid, secret_key)
    if nodeId is None:
        print('Provisioning Failed. Reset your board to factory defaults and retry.')
        return
    log.debug('Node ' + nodeId + ' provisioned successfully.')
    
    print('------------------------------------------')
    input('Please ensure host machine is connected to internet and Press Enter to continue...')
    print('Adding User-Node association...')
    retries = MAX_HTTP_CONNECTION_RETRIES
    node_object = None
    while retries > 0:
        try:
            # If session is expired then to initialise the new session internet connection is required.
            node_object = node.Node(nodeId, session.Session())
        except NetworkError:
            time.sleep(5)
            log.warn("Session is expired. Initialising new session.")
            pass
        except exception as nodeInitializeError:
            log.error(nodeInitializeError)
            print('Provisioning Failed. Reset your board to factory defaults and retry.')
            return
        else:
            break
        retries -= 1

    if node_object == None:
        print('Please check the internet connectivity.')
        print('Provisioning Failed. Reset your board to factory defaults and retry.')
        return
    retries = MAX_HTTP_CONNECTION_RETRIES
    requestId = None
    while retries > 0:
        try:
            log.debug('Adding user-node association.')
            requestId = node_object.add_user_node_mapping(secret_key)
        except Exception as addUserNodeMappingError:
            print("Sending User-Node association request to ESP RainMaker Cloud - Failed\nRetrying...")
            log.warn(addUserNodeMappingError)
            pass
        else:
            if requestId is not None:
                log.debug('User-node mapping added successfully with requestId ' + requestId)
                break
        time.sleep(5)
        retries -= 1

    if requestId is None:
        print('Sending User-Node association request to ESP RainMaker Cloud - Failed')
        print('Provisioning Failed. Reset your board to factory defaults and retry.')
        return
    print('Sending User-Node association request to ESP RainMaker Cloud - Successful')

    status = None
    while True:
        log.debug('Checking user-node association status.')
        try:
            status = node_object.get_mapping_status(requestId)
        except Exception as getMappingStatusError:
            log.warn(getMappingStatusError)
            pass
        else:
            log.debug('User-node association status ' + status)
            if status == 'requested':
                print('Checking User Node association status - Requested\nRetrying...')
            elif status == 'confirmed':
                print('Checking User Node association status - Confirmed')
                print('Provisioning was Successful.')
                return
            elif status == 'timedout':
                print('Checking User Node association status - Timeout')
                print('Provisioning Failed. Reset your board to factory defaults and retry.')
                return
            elif status == 'discarded':
                print('Checking User Node association status - Discarded')
                print('Provisioning Failed. Reset your board to factory defaults and retry.')
                return
        time.sleep(5)

    if status is None:
        print('Provisioning Failed. Reset your board to factory defaults and retry.')
        print('Checking User Node association status failed. Please check the internet connectivity.')
        return
    return