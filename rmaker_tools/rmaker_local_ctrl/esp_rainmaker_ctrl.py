#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2020-2025 Espressif Systems (Shanghai) CO LTD
#
# SPDX-License-Identifier: Apache-2.0

import argparse
import asyncio
import json
import sys
import os
from pathlib import Path
from rmaker_lib.logger import log

# Import from common shared modules
try:
    from . import esp_prov
    from ..common.security.security0 import Security0
    from ..common.security.security1 import Security1
    from ..common.security.security2 import Security2
    from .proto import proto_lc
except ImportError:
    # For standalone execution
    sys.path.insert(0, os.path.dirname(__file__))
    import esp_prov
    # Try common first, fallback to local
    try:
        from rmaker_tools.common.security.security0 import Security0
        from rmaker_tools.common.security.security1 import Security1
        from rmaker_tools.common.security.security2 import Security2
    except ImportError:
        from security.security0 import Security0
        from security.security1 import Security1
        from security.security2 import Security2
    from proto import proto_lc

# Property flags enum
PROP_FLAG_READONLY = (1 << 0)

def on_except(err):
    print(f"Error: {err}")

def get_security(secver, sec_patch_ver, username, password, pop='', verbose=False):
    if secver == 2:
        return Security2(sec_patch_ver, username, password, verbose)
    if secver == 1:
        return Security1(pop, verbose)
    if secver == 0:
        return Security0(verbose)
    return None

async def get_transport(sel_transport, service_name, timeout=60, resolve_timeout=15):
    try:
        if sel_transport == 'http':
            try:
                from ..common.transport.transport_http import Transport_HTTP
            except ImportError:
                from rmaker_tools.common.transport.transport_http import Transport_HTTP
            return Transport_HTTP(service_name, None, timeout=timeout, resolve_timeout=resolve_timeout)
        elif sel_transport == 'https':
            import ssl
            try:
                from ..common.transport.transport_http import Transport_HTTP
            except ImportError:
                from rmaker_tools.common.transport.transport_http import Transport_HTTP
            ssl_ctx = ssl.create_default_context()
            ssl_ctx.check_hostname = False
            ssl_ctx.verify_mode = ssl.CERT_NONE
            return Transport_HTTP(service_name, ssl_ctx, timeout=timeout, resolve_timeout=resolve_timeout)
        elif sel_transport == 'ble':
            try:
                from ..common.transport.transport_ble import Transport_BLE
            except ImportError:
                from rmaker_tools.common.transport.transport_ble import Transport_BLE
            tp = Transport_BLE(
                service_uuid='3d981e4a-31eb-42b4-8a68-75bd8d3bd521',
                nu_lookup={'esp_local_ctrl/version': '0001',
                          'esp_local_ctrl/session': '0002', 
                          'esp_local_ctrl/control': '0003'}
            )
            await tp.connect(devname=service_name)
            return tp
        return None
    except Exception as e:
        on_except(e)
        return None

async def establish_session(tp, sec):
    try:
        response = None
        while True:
            request = sec.security_session(response)
            if request is None:
                break
            response = tp.send_data('esp_local_ctrl/session', request)
            if response is None:
                return False
        return True
    except Exception as e:
        on_except(e)
        return False

PROP_INDEX_CONFIG = 0
PROP_INDEX_PARAMS = 1


async def get_property_by_index(tp, security_ctx, index, expected_name=None):
    """
    Read a single property by its known index. If expected_name is given,
    verify the returned name matches; fall back to sequential scan on mismatch.
    """
    try:
        log.debug(f"Reading property at index {index}" +
                  (f" (expecting '{expected_name}')" if expected_name else ""))
        message = proto_lc.get_prop_vals_request(security_ctx, [index])
        response = tp.send_data('esp_local_ctrl/control', message)
        props = proto_lc.get_prop_vals_response(security_ctx, response)

        if props and len(props) > 0:
            got_name = props[0].get('name', '')
            log.debug(f"Property at index {index}: name='{got_name}'")
            if expected_name is None or got_name == expected_name:
                return props[0]
            log.debug(f"Name mismatch at index {index}: expected '{expected_name}', "
                      f"got '{got_name}'. Falling back to sequential scan.")
        else:
            log.debug(f"No property returned for index {index}, falling back to scan")

        return await get_property_by_name(tp, security_ctx, expected_name or '')
    except Exception as e:
        on_except(e)
        return None


async def get_property_by_name(tp, security_ctx, prop_name):
    try:
        message = proto_lc.get_prop_count_request(security_ctx)
        response = tp.send_data('esp_local_ctrl/control', message)
        count = proto_lc.get_prop_count_response(security_ctx, response)
        log.debug(f"Property scan: count={count}, looking for '{prop_name}'")

        for i in range(count):
            message = proto_lc.get_prop_vals_request(security_ctx, [i])
            response = tp.send_data('esp_local_ctrl/control', message)
            props = proto_lc.get_prop_vals_response(security_ctx, response)

            if props and len(props) > 0:
                got_name = props[0].get('name', '')
                log.debug(f"  index {i}: name='{got_name}'")
                if got_name == prop_name:
                    return props[0]

        log.debug(f"Property '{prop_name}' not found in {count} properties")
        return None
    except Exception as e:
        on_except(e)
        return None


async def get_rainmaker_config(tp, security_ctx):
    prop = await get_property_by_index(tp, security_ctx, PROP_INDEX_CONFIG, "config")
    if prop and 'value' in prop:
        try:
            config_str = prop['value'].decode('utf-8') if isinstance(prop['value'], bytes) else prop['value']
            return json.loads(config_str)
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            print(f"Failed to parse config: {e}")
            return None
    return None


async def get_rainmaker_params(tp, security_ctx):
    prop = await get_property_by_index(tp, security_ctx, PROP_INDEX_PARAMS, "params")
    if prop and 'value' in prop:
        try:
            params_str = prop['value'].decode('utf-8') if isinstance(prop['value'], bytes) else prop['value']
            return json.loads(params_str)
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            print(f"Failed to parse params: {e}")
            return None
    return None

async def set_rainmaker_params(tp, security_ctx, new_params):
    try:
        # Find the params property
        message = proto_lc.get_prop_count_request(security_ctx)
        response = tp.send_data('esp_local_ctrl/control', message)
        count = proto_lc.get_prop_count_response(security_ctx, response)
        
        params_index = None
        for i in range(count):
            message = proto_lc.get_prop_vals_request(security_ctx, [i])
            response = tp.send_data('esp_local_ctrl/control', message)
            props = proto_lc.get_prop_vals_response(security_ctx, response)
            
            if props and len(props) > 0 and props[0]['name'] == "params":
                if props[0]['flags'] & PROP_FLAG_READONLY:
                    print("Cannot set read-only params property")
                    return False
                params_index = i
                break
        
        if params_index is None:
            print("Params property not found")
            return False
        
        # Set the new params
        params_json = json.dumps(new_params)
        params_bytes = params_json.encode('utf-8')
        
        message = proto_lc.set_prop_vals_request(security_ctx, [params_index], [params_bytes])
        response = tp.send_data('esp_local_ctrl/control', message)
        return proto_lc.set_prop_vals_response(security_ctx, response)
        
    except Exception as e:
        on_except(e)
        return False

async def main():
    parser = argparse.ArgumentParser(description='ESP RainMaker Local Control Client')
    
    parser.add_argument('--name', dest='service_name', type=str, required=True,
                       help='Device hostname or IP')
    parser.add_argument('--transport', dest='transport', type=str,
                       help='Transport (http/https/ble)', default='http')
    parser.add_argument('--sec_ver', dest='secver', type=int, default=1,
                       help='Security version (0/1/2)')
    parser.add_argument('--pop', dest='pop', type=str, default='',
                       help='Proof of Possession for security v1')
    
    # Operation flags
    parser.add_argument('--get-config', action='store_true',
                       help='Get ESP RainMaker configuration')
    parser.add_argument('--get-params', action='store_true', 
                       help='Get ESP RainMaker parameters')
    parser.add_argument('--set-params', type=str,
                       help='Set ESP RainMaker parameters (JSON string)')
    
    args = parser.parse_args()
    
    # Establish transport
    transport = await get_transport(args.transport, args.service_name)
    if transport is None:
        print("Failed to establish transport")
        return 1
    
    # Setup security
    security_obj = get_security(args.secver, 0, '', '', args.pop, False)
    if security_obj is None:
        print("Failed to setup security")
        return 1
    
    # Establish session
    if not await establish_session(transport, security_obj):
        print("Failed to establish session")
        return 1
    
    # Execute operations
    if args.get_config:
        config = await get_rainmaker_config(transport, security_obj)
        if config:
            print(json.dumps(config, indent=2))
        else:
            print("Failed to get config")
            return 1
            
    elif args.get_params:
        params = await get_rainmaker_params(transport, security_obj)
        if params:
            print(json.dumps(params, indent=2))
        else:
            print("Failed to get params")
            return 1
            
    elif args.set_params:
        try:
            new_params = json.loads(args.set_params)
            if await set_rainmaker_params(transport, security_obj, new_params):
                print("Parameters set successfully")
            else:
                print("Failed to set parameters")
                return 1
        except json.JSONDecodeError as e:
            print(f"Invalid JSON in --set-params: {e}")
            return 1
    else:
        print("No operation specified. Use --get-config, --get-params, or --set-params")
        return 1
    
    return 0

if __name__ == '__main__':
    sys.exit(asyncio.run(main()))