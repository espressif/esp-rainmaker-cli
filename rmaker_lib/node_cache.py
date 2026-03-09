# SPDX-FileCopyrightText: 2020-2025 Espressif Systems (Shanghai) CO LTD
#
# SPDX-License-Identifier: Apache-2.0

import json
import os
import time
import shutil
import hashlib
from rmaker_lib.logger import log

NODE_DETAILS_FILE = 'node_details.json'
NODE_CONFIG_FILE = 'node_config.json'
LOCAL_CONTROL_INFO_FILE = 'local_control_info.json'
LOCAL_CONTROL_CAPABILITY_FILE = 'local_control_capability.json'
CACHE_META_FILE = 'cache_meta.json'

DEFAULT_NODE_DETAILS_TTL = 3600
DEFAULT_NODE_CONFIG_TTL = 3600
DEFAULT_LOCAL_CONTROL_INFO_TTL = 3600
DEFAULT_CAPABILITY_TTL = 86400


def is_cache_enabled(profile_config=None, no_cache_flag=False):
    """
    Determine whether cache is enabled based on resolution order:
    --no-cache flag > RM_NODE_CACHE env var > profile config > default (disabled)
    """
    if no_cache_flag:
        return False

    env_val = os.environ.get('RM_NODE_CACHE')
    if env_val is not None:
        return env_val.strip() == '1'

    if profile_config and profile_config.get('node_cache_enabled'):
        return True

    return False


def _get_cache_base_dir(profile_config=None):
    """
    Resolve base cache directory.
    Priority: RM_NODE_CACHE_DIR env var > profile config > default.
    """
    env_dir = os.environ.get('RM_NODE_CACHE_DIR')
    if env_dir:
        return os.path.expanduser(env_dir)

    if profile_config and profile_config.get('node_cache_dir'):
        return os.path.expanduser(profile_config['node_cache_dir'])

    return os.path.expanduser('~/.espressif/rainmaker/node_cache')


def extract_local_control_info(params_or_details):
    """
    Extract local control info (POP, sec_ver, transport, port) from
    node params or node details response data.

    Scans for a service/device named "Local Control" or similar that
    contains POP and other local control parameters.
    """
    if not isinstance(params_or_details, dict):
        return None

    info = {}

    def _scan_dict(d):
        if not isinstance(d, dict):
            return
        for key, value in d.items():
            lower_key = key.lower().replace(' ', '_').replace('-', '_')
            if lower_key in ('pop', 'proof_of_possession'):
                info['pop'] = str(value)
            elif lower_key == 'sec_ver':
                try:
                    info['sec_ver'] = int(value)
                except (ValueError, TypeError):
                    pass
            elif lower_key == 'type' and isinstance(value, int):
                info.setdefault('sec_ver', value)
            elif lower_key == 'transport':
                info['transport'] = str(value)
            elif lower_key == 'port':
                try:
                    info['port'] = int(value)
                except (ValueError, TypeError):
                    pass
            elif isinstance(value, dict):
                _scan_dict(value)
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        _scan_dict(item)

    _scan_for_local_control_service(params_or_details, info, _scan_dict)

    if info.get('pop') is not None:
        return info
    return None


def _scan_for_local_control_service(data, info, scan_fn):
    """
    Look for a service or device named 'Local Control' and extract its params.
    """
    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(key, str) and 'local' in key.lower() and 'control' in key.lower():
                if isinstance(value, dict):
                    scan_fn(value)
                    return
            if isinstance(value, dict):
                name = value.get('name', '') or value.get('type', '')
                if isinstance(name, str) and 'local' in name.lower() and 'control' in name.lower():
                    scan_fn(value)
                    return
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        name = item.get('name', '') or item.get('type', '')
                        if isinstance(name, str) and 'local' in name.lower() and 'control' in name.lower():
                            scan_fn(item)
                            return


class NodeCache:
    """
    Persistent node details cache scoped by profile and user ID.

    When disabled, all read methods return None and write methods are no-ops,
    making the cache fully transparent to callers.
    """

    def __init__(self, profile_name, user_id, config_dir=None, enabled=True):
        self.enabled = enabled
        self.profile_name = profile_name
        self.user_id = user_id

        if config_dir:
            self.base_dir = config_dir
        else:
            self.base_dir = _get_cache_base_dir()

        self.cache_dir = os.path.join(self.base_dir, profile_name, user_id or 'unknown')

        if self.enabled:
            os.makedirs(self.cache_dir, exist_ok=True)

    def _node_dir(self, nodeid):
        return os.path.join(self.cache_dir, nodeid)

    def _ensure_node_dir(self, nodeid):
        node_dir = self._node_dir(nodeid)
        os.makedirs(node_dir, exist_ok=True)
        return node_dir

    def _read_json(self, nodeid, filename):
        filepath = os.path.join(self._node_dir(nodeid), filename)
        if not os.path.exists(filepath):
            return None
        try:
            with open(filepath, 'r') as f:
                return json.load(f)
        except Exception as e:
            log.debug(f"Failed to read cache file {filepath}: {e}")
            return None

    def _write_json(self, nodeid, filename, data):
        node_dir = self._ensure_node_dir(nodeid)
        filepath = os.path.join(node_dir, filename)
        try:
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2)
            self._update_meta(nodeid, filename)
        except Exception as e:
            log.debug(f"Failed to write cache file {filepath}: {e}")

    def _update_meta(self, nodeid, filename):
        node_dir = self._node_dir(nodeid)
        meta_path = os.path.join(node_dir, CACHE_META_FILE)
        meta = {}
        if os.path.exists(meta_path):
            try:
                with open(meta_path, 'r') as f:
                    meta = json.load(f)
            except Exception:
                meta = {}
        meta[filename] = time.time()
        try:
            with open(meta_path, 'w') as f:
                json.dump(meta, f, indent=2)
        except Exception as e:
            log.debug(f"Failed to update cache meta: {e}")

    def _get_timestamp(self, nodeid, filename):
        node_dir = self._node_dir(nodeid)
        meta_path = os.path.join(node_dir, CACHE_META_FILE)
        if not os.path.exists(meta_path):
            return None
        try:
            with open(meta_path, 'r') as f:
                meta = json.load(f)
            return meta.get(filename)
        except Exception:
            return None

    def is_stale(self, nodeid, data_type, max_age_seconds=None):
        """Check if cached data is older than TTL."""
        if not self.enabled:
            return True

        ttl_map = {
            NODE_DETAILS_FILE: DEFAULT_NODE_DETAILS_TTL,
            NODE_CONFIG_FILE: DEFAULT_NODE_CONFIG_TTL,
            LOCAL_CONTROL_INFO_FILE: DEFAULT_LOCAL_CONTROL_INFO_TTL,
            LOCAL_CONTROL_CAPABILITY_FILE: DEFAULT_CAPABILITY_TTL,
        }

        if max_age_seconds is None:
            max_age_seconds = ttl_map.get(data_type, DEFAULT_NODE_DETAILS_TTL)

        ts = self._get_timestamp(nodeid, data_type)
        if ts is None:
            return True
        return (time.time() - ts) > max_age_seconds

    def get_node_details(self, nodeid):
        if not self.enabled:
            return None
        if self.is_stale(nodeid, NODE_DETAILS_FILE):
            return None
        return self._read_json(nodeid, NODE_DETAILS_FILE)

    def set_node_details(self, nodeid, data):
        if not self.enabled:
            return
        self._write_json(nodeid, NODE_DETAILS_FILE, data)

    def get_node_config(self, nodeid):
        if not self.enabled:
            return None
        if self.is_stale(nodeid, NODE_CONFIG_FILE):
            return None
        return self._read_json(nodeid, NODE_CONFIG_FILE)

    def set_node_config(self, nodeid, data):
        if not self.enabled:
            return
        self._write_json(nodeid, NODE_CONFIG_FILE, data)

    def get_local_control_info(self, nodeid):
        if not self.enabled:
            return None
        if self.is_stale(nodeid, LOCAL_CONTROL_INFO_FILE):
            return None
        return self._read_json(nodeid, LOCAL_CONTROL_INFO_FILE)

    def set_local_control_info(self, nodeid, info):
        if not self.enabled:
            return
        self._write_json(nodeid, LOCAL_CONTROL_INFO_FILE, info)

    def get_local_control_capability(self, nodeid):
        if not self.enabled:
            return None
        if self.is_stale(nodeid, LOCAL_CONTROL_CAPABILITY_FILE):
            return None
        return self._read_json(nodeid, LOCAL_CONTROL_CAPABILITY_FILE)

    def set_local_control_capability(self, nodeid, capability):
        if not self.enabled:
            return
        self._write_json(nodeid, LOCAL_CONTROL_CAPABILITY_FILE, capability)

    def invalidate(self, nodeid=None):
        """Clear cache for a specific node or all nodes."""
        if not self.enabled:
            return

        if nodeid:
            node_dir = self._node_dir(nodeid)
            if os.path.exists(node_dir):
                shutil.rmtree(node_dir, ignore_errors=True)
                log.info(f"Cleared cache for node {nodeid}")
        else:
            if os.path.exists(self.cache_dir):
                shutil.rmtree(self.cache_dir, ignore_errors=True)
                os.makedirs(self.cache_dir, exist_ok=True)
                log.info("Cleared all node cache data")

    def list_cached_nodes(self):
        """Return list of node IDs that have cached data."""
        if not self.enabled or not os.path.exists(self.cache_dir):
            return []
        try:
            return [
                d for d in os.listdir(self.cache_dir)
                if os.path.isdir(os.path.join(self.cache_dir, d))
            ]
        except Exception:
            return []

    def get_cache_summary(self, nodeid):
        """Return a summary of what's cached for a node."""
        if not self.enabled:
            return None

        node_dir = self._node_dir(nodeid)
        if not os.path.exists(node_dir):
            return None

        summary = {'nodeid': nodeid, 'files': {}}
        for filename in [NODE_DETAILS_FILE, NODE_CONFIG_FILE,
                         LOCAL_CONTROL_INFO_FILE, LOCAL_CONTROL_CAPABILITY_FILE]:
            filepath = os.path.join(node_dir, filename)
            if os.path.exists(filepath):
                ts = self._get_timestamp(nodeid, filename)
                stale = self.is_stale(nodeid, filename)
                summary['files'][filename] = {
                    'exists': True,
                    'timestamp': ts,
                    'stale': stale,
                }
        return summary
