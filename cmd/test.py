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

import uuid
import time

try:
    from lib import session, node, configmanager
    from lib.logger import log
except Exception as importError:
    print("Failed to import ESP Rainmaker library. " + importError)
    sys.exit(1)

def add_node(node_object):
    secret_key = str(uuid.uuid4())
    requestId = node_object.add_user_node_mapping(secret_key)
    return requestId, secret_key

def check_status(node_object, requestId):
    status = None
    while True:
        log.debug('Checking user-node association status.')
        try:
            status = node_object.get_mapping_status(requestId)
        except Exception as getMappingStatusError:
            log.error(getMappingStatusError)
            return
        else:
            log.debug('User-node association status ' + status)
            if status == 'requested':
                print('Checking User Node association status - Requested\nRetrying...')
            elif status == 'confirmed':
                print('Checking User Node association status - Confirmed')
                return
            elif status == 'timedout':
                print('Checking User Node association status - Timeout')
                return
            elif status == 'discarded':
                print('Checking User Node association status - Discarded')
                return
        time.sleep(5)
    return

def test(args):
    if args.addnode:
        nodeId = args.addnode
        node_object = node.Node(nodeId, session.Session())
        requestId, secret_key = add_node(node_object)
        config = configmanager.Config()
        userId = config.get_user_id()
        print("Use following command on node simulator or node CLI to confirm user node mapping:")
        print(" add-user " + userId + " " + secret_key )
        print("---------------------------------------------------")
        print("RequestId for user node mapping request : " + requestId)
        check_status(node_object, requestId)
        return
    else:
        args.print_help()