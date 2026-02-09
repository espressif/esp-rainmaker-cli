# SPDX-FileCopyrightText: 2020-2025 Espressif Systems (Shanghai) CO LTD
#
# SPDX-License-Identifier: Apache-2.0

"""
Local Control wrapper module for rmaker_lib.
Provides access to ESP Local Control functionality.
"""

from rmaker_lib.logger import log


def run_local_control_operation(nodeid, operation, data=None, **kwargs):
    """
    Run a local control operation.
    
    This is a synchronous wrapper around the async local control integration.
    
    :param nodeid: Node ID of the target device
    :type nodeid: str
    
    :param operation: Operation to perform ('get_config', 'set_params', 'get_params')
    :type operation: str
    
    :param data: Data to send for set operations (optional)
    :type data: dict or None
    
    :param kwargs: Additional options like 'pop', 'sec_ver', 'transport', 'local_raw', etc.
    :type kwargs: dict
    
    :return: Result of the operation (dict for raw endpoints, bool/None for esp_local_ctrl)
    :rtype: dict, bool, or None
    """
    try:
        log.debug(f"Running local control operation: {operation} on node {nodeid}")
        
        # Import here to avoid loading conflicts at module level
        from rmaker_tools.rmaker_local_ctrl.integration import run_local_control_sync
        
        # Use the existing local control integration
        result = run_local_control_sync(nodeid, operation, data, **kwargs)
        
        return result
            
    except Exception as e:
        log.error(f"Local control operation failed: {e}")
        return None
