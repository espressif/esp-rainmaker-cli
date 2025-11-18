# SPDX-FileCopyrightText: 2020-2025 Espressif Systems (Shanghai) CO LTD
#
# SPDX-License-Identifier: Apache-2.0

"""
Simple Local Control wrapper module.
Provides a simplified interface to the ESP Local Control functionality.
"""

from rmaker_lib.logger import log


def run_simple_local_control_operation(nodeid, operation, data=None, **kwargs):
    """
    Run a simple local control operation.
    
    This is a wrapper that tries to use the proper local control integration
    with shared dependencies to avoid proto conflicts.
    
    :param nodeid: Node ID of the target device
    :type nodeid: str
    
    :param operation: Operation to perform ('get_config', 'set_params', 'get_params')
    :type operation: str
    
    :param data: Data to send for set operations (optional)
    :type data: dict or None
    
    :param kwargs: Additional options like 'pop', 'sec_ver', etc.
    :type kwargs: dict
    
    :return: Result of the operation or None on failure
    :rtype: dict or None
    """
    try:
        log.debug(f"Running simple local control operation: {operation} on node {nodeid}")
        
        # Import here to avoid loading conflicts at module level
        from rmaker_tools.rmaker_local_ctrl.integration import run_local_control_sync
        
        # Use the existing local control integration with shared dependencies
        result = run_local_control_sync(nodeid, operation, data, **kwargs)
        
        if result:
            log.debug(f"Local control operation successful")
            return result
        else:
            log.warning(f"Local control operation returned no result")
            return None
            
    except Exception as e:
        log.error(f"Simple local control operation failed: {e}")
        # Fallback: try basic HTTP for very simple operations
        try:
            import requests
            
            port = kwargs.get('port', 8080)
            
            # Build URL
            if ':' not in nodeid:
                if nodeid.endswith('.local'):
                    url = f"http://{nodeid}:{port}"
                else:
                    url = f"http://{nodeid}.local:{port}"
            else:
                url = f"http://{nodeid}"
            
            if operation == 'set_params' and data:
                response = requests.post(f"{url}/params", json=data, timeout=10)
                if response.status_code == 200:
                    return response.json()
            
        except Exception as fallback_err:
            log.debug(f"Fallback also failed: {fallback_err}")
        
        return None