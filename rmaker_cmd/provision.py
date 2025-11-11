#!/usr/bin/env python3
#
# SPDX-FileCopyrightText: 2020-2025 Espressif Systems (Shanghai) CO LTD
#
# SPDX-License-Identifier: Apache-2.0

import uuid
import time
import sys
import json

TRANSPORT_MODE_SOFTAP = 'softap'
MAX_HTTP_CONNECTION_RETRIES = 5
PROVISION_FAILURE_MSG = ('Provisioning Failed. Reset your board to factory '
                         'defaults and retry.')

try:
    from rmaker_tools.rmaker_prov.esp_rainmaker_prov import provision_device
    from rmaker_lib.logger import log
    from rmaker_lib import session, configmanager, node
    from rmaker_lib.exceptions import NetworkError, SSLError,\
        RequestTimeoutError, InvalidConfigError
    from rmaker_lib.profile_utils import get_session_with_profile
except ImportError as err:
    print("Failed to import ESP Rainmaker library.\n" + str(err))
    raise err


def provision(vars=None):
    """
    Provision the device to join Wi-Fi and add it to user account.

    :param vars: Dictionary containing provisioning parameters:
                 - `pop`: Proof of Possession for the device
                 - `transport`: Transport mode (softap/ble/console)
                 - `sec_ver`: Security version (0/1/2)
                 - `sec2_username`: Username for Security 2
                 - `sec2_password`: Password for Security 2
                 - `device_name`: Device name for BLE transport
                 - `ssid`: WiFi SSID
                 - `passphrase`: WiFi password
                 - `profile`: Profile to use for the operation
    :type vars: dict | None

    :raises Exception: If there is an issue with provisioning or adding device

    :return: None on Success
    :rtype: None
    """
    if vars is None:
        vars = {}
    
    try:
        log.info('Starting device provisioning...')
        
        # Create session with profile support
        curr_session = get_session_with_profile(vars)
        
        # Get user credentials
        config = configmanager.Config()
        userid = config.get_user_id()
        log.debug('User session is initialized for the user ' + userid)
        
        # Extract provisioning parameters
        # Handle both positional pop and --pop flag for backward compatibility
        # Ensure pop is always a string (not None) to avoid len() errors
        pop = vars.get('pop_flag') or vars.get('pop') or ''
        pop = pop if pop is not None else ''
        transport_mode = vars.get('transport', 'softap')
        sec_ver = vars.get('sec_ver')
        
        # Validate pop requirement based on security version
        # For sec_ver 1, pop may be optional if device supports 'no_pop' capability
        # This will be checked after connecting to the device in provision_device()
        # For sec_ver 0 and 2, pop is not needed
        # Only require pop upfront if sec_ver is not explicitly set (auto-detect case)
        if not pop and sec_ver is None:
            raise ValueError("Proof of possession (pop) is required. Use --pop or provide as positional argument.")
        sec2_username = vars.get('sec2_username', '')
        sec2_password = vars.get('sec2_password', '')
        device_name = vars.get('device_name')
        ssid = vars.get('ssid')
        passphrase = vars.get('passphrase')
        
        # Generate secret key for user-node mapping
        secret_key = str(uuid.uuid4())
        
        # Transport-specific connection prompt
        if transport_mode == 'softap':
            try:
                input('Please connect to the device\'s WiFi hotspot (PROV_XXXXXX) and press Enter to continue...')
            except KeyboardInterrupt:
                print("\nExiting...")
                sys.exit(0)
        elif transport_mode == 'ble':
            if device_name:
                print(f'Looking for BLE device: {device_name}')
            else:
                print('Scanning for BLE devices... Make sure your device is in provisioning mode.')
        elif transport_mode == 'console':
            print('Using console transport. Make sure device is connected to serial port.')
        
        log.info(f'Provisioning via {transport_mode.upper()} transport')
        
        # Call the provisioning function with all parameters including session
        try:
            result = provision_device(
                transport_mode=transport_mode,
                pop=pop,
                userid=userid,
                secretkey=secret_key,
                ssid=ssid,
                passphrase=passphrase,
                security_version=sec_ver,
                sec2_username=sec2_username,
                sec2_password=sec2_password,
                device_name=device_name,
                session=curr_session
            )
        except RuntimeError as claim_err:
            # Handle claim requirement error specifically
            error_msg = str(claim_err)
            log.error(error_msg)
            print(f'❌ Error: {error_msg}')
            sys.exit(1)
        
        # Handle tuple return (node_id, challenge_response_performed)
        if isinstance(result, tuple):
            node_id, challenge_response_performed = result
        else:
            node_id = result
            challenge_response_performed = False
        
        if node_id is None:
            log.error(PROVISION_FAILURE_MSG)
            print(PROVISION_FAILURE_MSG)
            return
            
        log.info(f'Node {node_id} provisioned successfully.')
        print(f'✅ Node {node_id} provisioned successfully!')
        
        # Skip node mapping if challenge-response was used (already added synchronously)
        if challenge_response_performed:
            log.info('Node already added to account via challenge-response flow')
            print(f'✅ Node added to your account successfully!')
            return
        
        # Add node to user account (traditional flow requires polling)
        try:
            log.info('Adding node to user account...')
            node_obj = node.Node(node_id, curr_session)
            request_id = node_obj.add_user_node_mapping(secret_key)
            if not request_id:
                print(f'⚠️  Warning: Node provisioned but failed to add to account')
                log.warning('add_user_node_mapping returned None')
                return
            
            # Poll for mapping status
            log.info(f'Polling for mapping status with request_id: {request_id}')
            print('Waiting for node mapping confirmation...')
            max_poll_time = 60  # Maximum polling time in seconds
            poll_interval = 5  # Poll every 5 seconds
            start_time = time.time()
            poll_count = 0
            
            while True:
                try:
                    status = node_obj.get_mapping_status(request_id)
                    poll_count += 1
                    elapsed_time = int(time.time() - start_time)
                    
                    # Show periodic status updates
                    if status:
                        print(f'Mapping status: {status} (elapsed: {elapsed_time}s)')
                    else:
                        print(f'Checking mapping status... (elapsed: {elapsed_time}s)')
                    
                    log.debug(f'Mapping status (poll #{poll_count}): {status}')
                    
                    if status == 'confirmed':
                        log.info('Node mapping confirmed successfully')
                        print(f'✅ Node added to your account successfully!')
                        return
                    elif status == 'requested':
                        # Continue polling
                        elapsed_time = time.time() - start_time
                        if elapsed_time >= max_poll_time:
                            log.debug(f'Mapping status polling timed out after {max_poll_time} seconds')
                            print(f'❌ Error: Node mapping request timed out after {max_poll_time} seconds')
                            sys.exit(1)
                        time.sleep(poll_interval)
                        continue
                    elif status == 'timedout':
                        log.debug('Node mapping request timed out')
                        print(f'❌ Error: Node mapping request timed out')
                        sys.exit(1)
                    elif status == 'discarded':
                        log.debug('Node mapping request was discarded')
                        print(f'❌ Error: Node mapping request was discarded')
                        sys.exit(1)
                    elif status is None:
                        log.debug('Mapping status check returned None, continuing to poll...')
                        elapsed_time = time.time() - start_time
                        if elapsed_time >= max_poll_time:
                            log.debug(f'Mapping status polling timed out after {max_poll_time} seconds')
                            print(f'❌ Error: Node mapping status check timed out after {max_poll_time} seconds')
                            sys.exit(1)
                        time.sleep(poll_interval)
                        continue
                    else:
                        log.debug(f'Unknown mapping status: {status}, continuing to poll...')
                        elapsed_time = time.time() - start_time
                        if elapsed_time >= max_poll_time:
                            log.debug(f'Mapping status polling timed out after {max_poll_time} seconds')
                            print(f'❌ Error: Node mapping status check timed out after {max_poll_time} seconds')
                            sys.exit(1)
                        time.sleep(poll_interval)
                        continue
                        
                except (NetworkError, RequestTimeoutError) as poll_err:
                    elapsed_time = int(time.time() - start_time)
                    log.debug(f'Error while polling mapping status: {poll_err}, retrying...')
                    print(f'Network error while checking status, retrying... (elapsed: {elapsed_time}s)')
                    elapsed_time = time.time() - start_time
                    if elapsed_time >= max_poll_time:
                        log.debug(f'Mapping status polling timed out after {max_poll_time} seconds')
                        print(f'❌ Error: Failed to check node mapping status after {max_poll_time} seconds')
                        sys.exit(1)
                    time.sleep(poll_interval)
                    continue
                except Exception as poll_err:
                    log.debug(f'Unexpected error while polling mapping status: {poll_err}')
                    print(f'❌ Error: Failed to check node mapping status: {poll_err}')
                    sys.exit(1)
            
        except Exception as add_node_err:
            log.error(f'Failed to add node to user account: {add_node_err}')
            print(f'⚠️  Warning: Node provisioned but failed to add to account: {add_node_err}')
        
    except KeyboardInterrupt:
        print("\nProvisioning cancelled by user.")
        sys.exit(0)
    except Exception as provision_err:
        log.error(f"Provisioning failed: {provision_err}")
        print(f"❌ Provisioning failed: {provision_err}")
        sys.exit(1)
