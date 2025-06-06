# SPDX-FileCopyrightText: 2020-2025 Espressif Systems (Shanghai) CO LTD
#
# SPDX-License-Identifier: Apache-2.0

import uuid
import time
import sys

try:
    from rmaker_lib import session, node, configmanager
    from rmaker_lib.logger import log
    from rmaker_lib.profile_utils import get_session_with_profile
except ImportError as err:
    print("Failed to import ESP Rainmaker library. " + str(err))
    raise err


def add_node(node_object):
    secret_key = str(uuid.uuid4())
    request_id = node_object.add_user_node_mapping(secret_key)
    return request_id, secret_key


def check_status(node_object, request_id):
    status = None
    while True:
        log.debug('Checking user-node association status.')
        try:
            status = node_object.get_mapping_status(request_id)
        except Exception as mapping_status_err:
            log.error(mapping_status_err)
            return
        else:
            log.debug('User-node association status ' + status)
            if status == 'requested':
                print('Checking User Node association status - Requested\n'
                      'Retrying...')
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


def test(vars=None):
    """
    Check user node mapping

    :param vars:
        `addnode` as key - Node ID of node to be mapped to user,\n
        `profile` as key - Profile to use for the operation,\n
        defaults to `None`
    :type vars: dict

    """
    node_id = vars['addnode']
    if node_id is None or not vars.get('addnode'):
        print('Error: The following arguments are required: --addnode\n'
              'Check usage: rainmaker.py [-h]\n')
        sys.exit(0)
    
    curr_session = get_session_with_profile(vars or {})
    node_object = node.Node(node_id, curr_session)
    request_id, secret_key = add_node(node_object)
    config = configmanager.Config()
    user_id = config.get_user_id()
    print('Use following command on node simulator or '
          'node CLI to confirm user node mapping:')
    print(" add-user " + user_id + " " + secret_key)
    print("---------------------------------------------------")
    print("RequestId for user node mapping request : " + request_id)
    check_status(node_object, request_id)
    return
