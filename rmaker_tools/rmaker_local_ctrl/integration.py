#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2020-2025 Espressif Systems (Shanghai) CO LTD
#
# SPDX-License-Identifier: Apache-2.0

import asyncio
import json
import time
from rmaker_lib.logger import log
from . import get_rainmaker_config, get_rainmaker_params, set_rainmaker_params
from . import get_security, get_transport, establish_session

ERR_TRANSPORT = 'transport_failed'
ERR_SECURITY = 'security_failed'
ERR_OPERATION = 'operation_failed'


async def _probe_session(transport_obj, security_obj):
    """
    Send a lightweight get_prop_count request to verify the session is alive.
    Returns True if the device responds correctly.
    """
    try:
        from .proto import proto_lc
        message = proto_lc.get_prop_count_request(security_obj)
        response = transport_obj.send_data('esp_local_ctrl/control', message)
        count = proto_lc.get_prop_count_response(security_obj, response)
        return count is not None and count >= 0
    except Exception as e:
        log.debug(f"Session probe failed: {e}")
        return False


async def _try_resume_session(nodeid, pop, transport_type, session_store):
    """
    Attempt to resume a saved session from disk.
    Returns (transport_obj, security_obj) on success, (None, None) on failure.
    """
    if session_store is None:
        return None, None

    session_data = session_store.load_session(nodeid)
    if session_data is None:
        log.debug(f"No saved session for node {nodeid}")
        return None, None

    if not session_store.is_session_valid(nodeid):
        log.debug(f"Saved session for node {nodeid} has expired")
        session_store.invalidate_session(nodeid)
        return None, None

    saved_host = session_data.get('host')
    saved_port = session_data.get('port', 8080)
    saved_cookie = session_data.get('cookie')
    saved_transport = session_data.get('transport', 'http')

    if not saved_host:
        log.debug("No saved host in session data")
        session_store.invalidate_session(nodeid)
        return None, None

    if session_data.get('sec_ver') == 0:
        try:
            from ..common.transport.transport_http import Transport_HTTP

            service_name = f"{saved_host}:{saved_port}"
            log.debug(f"Sec0 resume: connecting to cached IP {service_name}")

            ssl_ctx = None
            if saved_transport == 'https':
                import ssl
                ssl_ctx = ssl.create_default_context()
                ssl_ctx.check_hostname = False
                ssl_ctx.verify_mode = ssl.CERT_NONE

            try:
                transport_obj = Transport_HTTP(service_name, ssl_ctx, timeout=3)
            except Exception as e:
                log.debug(f"Cannot connect to saved host {service_name}: {e}")
                session_store.invalidate_session(nodeid)
                return None, None

            if saved_cookie:
                transport_obj.set_cookie(saved_cookie)

            security_obj = get_security(0, 0, '', '', '', False)
            if security_obj is None:
                session_store.invalidate_session(nodeid)
                return None, None

            if not await establish_session(transport_obj, security_obj):
                log.debug("Sec0 session establishment to cached IP failed")
                session_store.invalidate_session(nodeid)
                return None, None

            log.info(f"Sec0 session established to cached IP for node {nodeid}")
            return transport_obj, security_obj

        except Exception as e:
            log.debug(f"Sec0 resume failed: {e}")
            session_store.invalidate_session(nodeid)
            return None, None

    try:
        from ..common.security.security1 import Security1
        from ..common.transport.transport_http import Transport_HTTP

        security_obj = Security1.deserialize(session_data, pop=pop, verbose=False)
        if security_obj is None:
            log.debug("Failed to deserialize security object (POP mismatch?)")
            session_store.invalidate_session(nodeid)
            return None, None

        service_name = f"{saved_host}:{saved_port}"
        log.debug(f"Attempting session resume to {service_name}")

        ssl_ctx = None
        if saved_transport == 'https':
            import ssl
            ssl_ctx = ssl.create_default_context()
            ssl_ctx.check_hostname = False
            ssl_ctx.verify_mode = ssl.CERT_NONE

        try:
            transport_obj = Transport_HTTP(service_name, ssl_ctx, timeout=3)
        except Exception as e:
            log.debug(f"Cannot connect to saved host {service_name}: {e}")
            session_store.invalidate_session(nodeid)
            return None, None

        if saved_cookie:
            transport_obj.set_cookie(saved_cookie)

        if await _probe_session(transport_obj, security_obj):
            log.info(f"Session resumed for node {nodeid}")
            return transport_obj, security_obj
        else:
            log.debug("Session probe failed, will establish fresh session")
            session_store.invalidate_session(nodeid)
            return None, None

    except Exception as e:
        log.debug(f"Session resume failed: {e}")
        if session_store:
            session_store.invalidate_session(nodeid)
        return None, None


def _save_session_state(nodeid, transport_obj, security_obj, transport_type, sec_ver, pop, session_store):
    """Save session crypto state to disk for future resume."""
    if session_store is None:
        return

    try:
        resolved_ip, port = transport_obj.get_resolved_host_port()
        cookie = transport_obj.get_cookie()

        if sec_ver == 0:
            session_data = {
                'sec_ver': 0,
                'host': resolved_ip,
                'port': port,
                'cookie': cookie,
                'transport': transport_type,
            }
        else:
            sec_data = security_obj.serialize()
            if sec_data is None:
                return
            session_data = {
                **sec_data,
                'host': resolved_ip,
                'port': port,
                'cookie': cookie,
                'transport': transport_type,
            }

        session_store.save_session(nodeid, session_data)
        log.debug(f"Saved session with resolved IP {resolved_ip}:{port}")
    except Exception as e:
        log.debug(f"Failed to save session state: {e}")


def _update_session_offset(nodeid, security_obj, session_store):
    """Update the CTR offset in the saved session after an operation."""
    if session_store is None:
        return
    try:
        session_store.update_session_offset(nodeid, security_obj.ctr_offset)
    except Exception as e:
        log.debug(f"Failed to update session offset: {e}")


async def _execute_operation(transport_obj, security_obj, operation, data):
    """Execute the actual local control operation."""
    if operation == 'get_config':
        return await get_rainmaker_config(transport_obj, security_obj)
    elif operation == 'get_params':
        return await get_rainmaker_params(transport_obj, security_obj)
    elif operation == 'set_params':
        return await set_rainmaker_params(transport_obj, security_obj, data)
    else:
        log.error(f"Unknown operation: {operation}")
        return None


async def _fresh_establish(nodeid, pop, transport_type, sec_ver, port):
    """
    Establish a fresh transport + security session.
    Returns (transport_obj, security_obj, error_reason).
    error_reason is None on success, ERR_TRANSPORT or ERR_SECURITY on failure.
    """
    if ':' not in nodeid:
        if nodeid.endswith('.local'):
            service_name = f"{nodeid}:{port}"
        else:
            service_name = f"{nodeid}.local:{port}"
    else:
        service_name = nodeid

    log.debug(f"Fresh session establishment to '{service_name}'")

    transport_obj = await get_transport(transport_type, service_name)
    if transport_obj is None:
        log.error("Failed to establish transport")
        return None, None, ERR_TRANSPORT

    security_obj = get_security(sec_ver, 0, '', '', pop, False)
    if security_obj is None:
        log.error("Failed to setup security")
        return None, None, ERR_SECURITY

    if not await establish_session(transport_obj, security_obj):
        log.error("Failed to establish session")
        return None, None, ERR_SECURITY

    return transport_obj, security_obj, None


async def _discover_and_connect(nodeid, pop, transport_type, port, node_cache):
    """
    Probe the device to discover its local control capability.
    Tries sec0 first (no POP needed), then sec1 with POP.
    Returns (transport_obj, security_obj, discovered_sec_ver) or (None, None, None).

    Only caches 'supported: False' if the device was reachable at the
    transport (TCP) level but local control could not be established.
    Network-level failures (DNS/TCP) are not cached to avoid poisoning
    the capability cache for temporarily unreachable or mistyped nodes.
    """
    log.debug(f"Probing local control capability for node {nodeid}")

    if ':' not in nodeid:
        if nodeid.endswith('.local'):
            service_name = f"{nodeid}:{port}"
        else:
            service_name = f"{nodeid}.local:{port}"
    else:
        service_name = nodeid

    transport_obj = await get_transport(transport_type, service_name)
    if transport_obj is None:
        log.debug(f"Node {nodeid} is not reachable, skipping capability cache")
        return None, None, None

    security_obj = get_security(0, 0, '', '', '', False)
    if security_obj is not None and await establish_session(transport_obj, security_obj):
        if await _probe_session(transport_obj, security_obj):
            log.info(f"Node {nodeid} supports local control with sec0")
            if node_cache:
                node_cache.set_local_control_capability(nodeid, {
                    'supported': True,
                    'sec_ver': 0,
                    'pop_required': False,
                    'transport': transport_type,
                    'port': port,
                })
            return transport_obj, security_obj, 0

    if pop:
        transport_obj = await get_transport(transport_type, service_name)
        if transport_obj is not None:
            security_obj = get_security(1, 0, '', '', pop, False)
            if security_obj is not None and await establish_session(transport_obj, security_obj):
                log.info(f"Node {nodeid} supports local control with sec1")
                if node_cache:
                    node_cache.set_local_control_capability(nodeid, {
                        'supported': True,
                        'sec_ver': 1,
                        'pop_required': True,
                        'transport': transport_type,
                        'port': port,
                    })
                return transport_obj, security_obj, 1

    log.debug(f"Node {nodeid} is reachable but does not support local control")
    if node_cache:
        node_cache.set_local_control_capability(nodeid, {
            'supported': False,
        })
    return None, None, None


async def run_local_control_operation(nodeid, operation, data=None, **kwargs):
    """
    Run ESP Local Control operations with session reuse and capability caching.

    If kwargs contains an 'error_info' dict, it will be populated with
    'reason' on failure (ERR_TRANSPORT, ERR_SECURITY, or ERR_OPERATION).
    """
    error_info = kwargs.get('error_info', None)

    def _set_error(reason):
        if error_info is not None:
            error_info['reason'] = reason

    use_local_raw = kwargs.get('local_raw', False)
    if use_local_raw:
        log.debug("Using local control via raw endpoints")
        from .raw_params import run_raw_params_operation
        return await run_raw_params_operation(nodeid, operation, data, **kwargs)

    pop = kwargs.get('pop', '')
    transport_type = kwargs.get('transport', 'http')
    sec_ver = kwargs.get('sec_ver', 1)
    port = kwargs.get('port', 8080)
    node_cache = kwargs.get('node_cache', None)
    session_store = kwargs.get('session_store', None)
    explicit_sec_ver = kwargs.get('explicit_sec_ver', False)

    if node_cache:
        capability = node_cache.get_local_control_capability(nodeid)
        if capability and not capability.get('supported', True):
            log.info(f"Node {nodeid} is known to not support local control (cached)")
            _set_error(ERR_TRANSPORT)
            return None

        if capability and capability.get('supported') and not explicit_sec_ver:
            sec_ver = capability.get('sec_ver', sec_ver)
            port = capability.get('port', port)
            transport_type = capability.get('transport', transport_type)
            if sec_ver == 0:
                pop = ''

    last_err = None

    try:
        transport_obj, security_obj = await _try_resume_session(
            nodeid, pop, transport_type, session_store
        )

        resumed = transport_obj is not None

        if not resumed:
            if not explicit_sec_ver and not pop and node_cache:
                cap = node_cache.get_local_control_capability(nodeid)
                if cap is None:
                    transport_obj, security_obj, sec_ver = await _discover_and_connect(
                        nodeid, pop, transport_type, port, node_cache
                    )
                    if transport_obj is None:
                        _set_error(ERR_TRANSPORT)
                        return None
                else:
                    transport_obj, security_obj, last_err = await _fresh_establish(
                        nodeid, pop, transport_type, sec_ver, port
                    )
            else:
                transport_obj, security_obj, last_err = await _fresh_establish(
                    nodeid, pop, transport_type, sec_ver, port
                )

            if transport_obj is None or security_obj is None:
                _set_error(last_err or ERR_TRANSPORT)
                return None

            _save_session_state(nodeid, transport_obj, security_obj,
                                transport_type, sec_ver, pop, session_store)

        result = await _execute_operation(transport_obj, security_obj, operation, data)

        if result is not None:
            _update_session_offset(nodeid, security_obj, session_store)
            if node_cache and not node_cache.get_local_control_capability(nodeid):
                node_cache.set_local_control_capability(nodeid, {
                    'supported': True,
                    'sec_ver': sec_ver,
                    'pop_required': bool(pop),
                    'transport': transport_type,
                    'port': port,
                })

        if result is None and resumed:
            log.debug("Operation failed on resumed session, retrying with fresh session")
            if session_store:
                session_store.invalidate_session(nodeid)

            transport_obj, security_obj, last_err = await _fresh_establish(
                nodeid, pop, transport_type, sec_ver, port
            )
            if transport_obj is None or security_obj is None:
                _set_error(last_err or ERR_SECURITY)
                return None

            _save_session_state(nodeid, transport_obj, security_obj,
                                transport_type, sec_ver, pop, session_store)

            result = await _execute_operation(transport_obj, security_obj, operation, data)
            if result is not None:
                _update_session_offset(nodeid, security_obj, session_store)

        if result is None:
            _set_error(ERR_OPERATION)
        return result

    except Exception as e:
        log.error(f"Local control operation failed: {e}")
        _set_error(ERR_TRANSPORT)
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
