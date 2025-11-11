#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2020-2025 Espressif Systems (Shanghai) CO LTD
#
# SPDX-License-Identifier: Apache-2.0

import asyncio
import json
from rmaker_lib.logger import log
from . import get_rainmaker_config, get_rainmaker_params, set_rainmaker_params
from . import get_security, get_transport, establish_session

async def run_local_control_operation(nodeid, operation, data=None, **kwargs):
    """
    Run ESP Local Control operations directly using the clean module structure
    """
    
    # Extract options with defaults
    pop = kwargs.get('pop', '')
    transport = kwargs.get('transport', 'http')
    sec_ver = kwargs.get('sec_ver', 1)
    port = kwargs.get('port', 8080)
    
    # Build service name
    if ':' not in nodeid:
        if nodeid.endswith('.local'):
            service_name = f"{nodeid}:{port}"
        else:
            service_name = f"{nodeid}.local:{port}"
    else:
        service_name = nodeid
    
    log.debug(f"Built service_name: '{service_name}' from nodeid: '{nodeid}'")
    
    try:
        # Establish transport
        transport_obj = await get_transport(transport, service_name)
        if transport_obj is None:
            log.error("Failed to establish transport")
            return None
        
        # Setup security
        security_obj = get_security(sec_ver, 0, '', '', pop, False)
        if security_obj is None:
            log.error("Failed to setup security")
            return None
        
        # Establish session
        if not await establish_session(transport_obj, security_obj):
            log.error("Failed to establish session")
            return None
        
        # Execute operation
        if operation == 'get_config':
            config = await get_rainmaker_config(transport_obj, security_obj)
            return config
        elif operation == 'get_params':
            params = await get_rainmaker_params(transport_obj, security_obj)
            return params  
        elif operation == 'set_params':
            success = await set_rainmaker_params(transport_obj, security_obj, data)
            return success
        else:
            log.error(f"Unknown operation: {operation}")
            return None
            
    except Exception as e:
        log.error(f"Local control operation failed: {e}")
        return None

def run_local_control_sync(nodeid, operation, data=None, **kwargs):
    """
    Synchronous wrapper for local control operations
    """
    try:
        return asyncio.run(run_local_control_operation(nodeid, operation, data, **kwargs))
    except Exception as e:
        log.error(f"Local control sync wrapper failed: {e}")
        return None