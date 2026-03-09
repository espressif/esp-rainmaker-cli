# SPDX-FileCopyrightText: 2020-2025 Espressif Systems (Shanghai) CO LTD
#
# SPDX-License-Identifier: Apache-2.0

import json
import os
import time
import datetime
from rmaker_lib.logger import log


def cache_manage(vars=None):
    """
    Manage local node cache: enable, disable, show, clear.
    """
    if vars is None:
        print("No cache command specified. Use: cache {enable|disable|show|clear}")
        return

    command = vars.get('cache_command')
    if not command:
        print("No cache command specified. Use: cache {enable|disable|show|clear}")
        return

    if command == 'enable':
        _cache_enable_disable(True)
    elif command == 'disable':
        _cache_enable_disable(False)
    elif command == 'show':
        _cache_show(vars)
    elif command == 'clear':
        _cache_clear(vars)


def _cache_enable_disable(enable):
    """Enable or disable cache for the current profile."""
    try:
        from rmaker_lib.configmanager import Config
        config = Config()
        profile_name = config.get_current_profile_name()
        config.profile_manager.set_cache_enabled(profile_name, enable)
        state = 'enabled' if enable else 'disabled'
        print(f"Node cache {state} for profile '{profile_name}'.")
    except Exception as e:
        print(f"Failed to update cache setting: {e}")


def _cache_show(vars):
    """Show cached data for current user/profile."""
    try:
        from rmaker_lib.configmanager import Config
        from rmaker_lib.node_cache import NodeCache, is_cache_enabled, _get_cache_base_dir

        config = Config(profile_override=vars.get('profile'))
        profile_name = config.get_current_profile_name()
        profile_config = config.get_profile_config_for_current()

        if not is_cache_enabled(profile_config):
            print(f"Node cache is disabled for profile '{profile_name}'.")
            print("Use 'esp-rainmaker-cli cache enable' to enable it.")
            return

        try:
            user_id = config.get_user_id()
        except Exception:
            user_id = 'unknown'

        nc = NodeCache(profile_name, user_id, enabled=True)
        node_filter = vars.get('node')

        if node_filter:
            nodes = [node_filter]
        else:
            nodes = nc.list_cached_nodes()

        if not nodes:
            print("No cached data found.")
            return

        print(f"Cache location: {nc.cache_dir}")
        print(f"Profile: {profile_name}, User: {user_id}")
        print()

        for nodeid in nodes:
            summary = nc.get_cache_summary(nodeid)
            if summary is None:
                print(f"  {nodeid}: No cached data")
                continue

            print(f"  Node: {nodeid}")
            for filename, info in summary.get('files', {}).items():
                ts = info.get('timestamp')
                stale = info.get('stale', True)
                ts_str = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S') if ts else 'unknown'
                status = 'stale' if stale else 'fresh'
                print(f"    {filename}: {ts_str} ({status})")

            lc_info = nc.get_local_control_info(nodeid)
            if lc_info:
                print(f"    Local Control: POP={'yes' if lc_info.get('pop') else 'no'}, "
                      f"sec_ver={lc_info.get('sec_ver', '?')}")

            cap = nc.get_local_control_capability(nodeid)
            if cap:
                if cap.get('supported'):
                    print(f"    Capability: supported, sec_ver={cap.get('sec_ver', '?')}, "
                          f"pop_required={cap.get('pop_required', '?')}")
                else:
                    print(f"    Capability: not supported")

            from rmaker_lib.session_store import SessionStore
            ss = SessionStore(nc.cache_dir, enabled=True)
            if ss.is_session_valid(nodeid):
                sess = ss.load_session(nodeid)
                if sess:
                    last_used = sess.get('last_used_at', 0)
                    age = time.time() - last_used
                    print(f"    Session: active ({age:.0f}s ago)")
            print()

    except Exception as e:
        print(f"Failed to show cache: {e}")
        log.debug(f"Cache show error: {e}")


def _cache_clear(vars):
    """Clear cached data."""
    try:
        from rmaker_lib.configmanager import Config
        from rmaker_lib.node_cache import NodeCache, is_cache_enabled
        from rmaker_lib.session_store import SessionStore

        config = Config(profile_override=vars.get('profile'))
        profile_name = config.get_current_profile_name()
        profile_config = config.get_profile_config_for_current()

        if not is_cache_enabled(profile_config):
            print(f"Node cache is disabled for profile '{profile_name}'.")
            return

        try:
            user_id = config.get_user_id()
        except Exception:
            user_id = 'unknown'

        nc = NodeCache(profile_name, user_id, enabled=True)
        ss = SessionStore(nc.cache_dir, enabled=True)
        node_filter = vars.get('node')

        nc.invalidate(nodeid=node_filter)
        ss.invalidate_session(nodeid=node_filter)

        if node_filter:
            print(f"Cleared cache for node '{node_filter}'.")
        else:
            print("Cleared all cached data.")

    except Exception as e:
        print(f"Failed to clear cache: {e}")
        log.debug(f"Cache clear error: {e}")
