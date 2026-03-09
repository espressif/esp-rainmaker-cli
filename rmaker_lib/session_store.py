# SPDX-FileCopyrightText: 2020-2025 Espressif Systems (Shanghai) CO LTD
#
# SPDX-License-Identifier: Apache-2.0

import json
import os
import stat
import time
from rmaker_lib.logger import log

SESSION_FILE = 'session.json'
DEFAULT_SESSION_TTL = 604800


class SessionStore:
    """
    Disk-based session store for persisting local control session crypto state
    across CLI invocations.

    Stores: shared_key, device_random (nonce), ctr_offset, cookie, host, port,
    transport, sec_ver, pop_hash.

    When disabled, all methods are no-ops.
    """

    def __init__(self, cache_dir, enabled=True):
        self.cache_dir = cache_dir
        self.enabled = enabled

    def _session_path(self, nodeid):
        return os.path.join(self.cache_dir, nodeid, SESSION_FILE)

    def save_session(self, nodeid, session_data):
        """
        Write session state to disk with restrictive permissions.

        :param nodeid: Node ID
        :param session_data: dict with shared_key, device_random, ctr_offset, cookie, etc.
        """
        if not self.enabled:
            return

        node_dir = os.path.join(self.cache_dir, nodeid)
        os.makedirs(node_dir, exist_ok=True)

        filepath = self._session_path(nodeid)
        session_data['last_used_at'] = time.time()
        if 'created_at' not in session_data:
            session_data['created_at'] = time.time()

        try:
            fd = os.open(filepath, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
            with os.fdopen(fd, 'w') as f:
                json.dump(session_data, f, indent=2)
            log.debug(f"Saved session for node {nodeid}")
        except Exception as e:
            log.debug(f"Failed to save session for node {nodeid}: {e}")

    def load_session(self, nodeid):
        """
        Load session state from disk.

        :return: session dict or None
        """
        if not self.enabled:
            return None

        filepath = self._session_path(nodeid)
        if not os.path.exists(filepath):
            return None

        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
            return data
        except Exception as e:
            log.debug(f"Failed to load session for node {nodeid}: {e}")
            return None

    def is_session_valid(self, nodeid, max_age_seconds=None):
        """
        Check if a saved session exists and is within TTL.
        """
        if not self.enabled:
            return False

        if max_age_seconds is None:
            max_age_seconds = DEFAULT_SESSION_TTL

        data = self.load_session(nodeid)
        if data is None:
            return False

        last_used = data.get('last_used_at', data.get('created_at', 0))
        age = time.time() - last_used
        return age < max_age_seconds

    def update_session_offset(self, nodeid, new_ctr_offset):
        """
        Update the CTR counter offset and last_used_at timestamp
        without rewriting the entire session.
        """
        if not self.enabled:
            return

        data = self.load_session(nodeid)
        if data is None:
            return

        data['ctr_offset'] = new_ctr_offset
        data['last_used_at'] = time.time()
        self.save_session(nodeid, data)

    def invalidate_session(self, nodeid=None):
        """
        Delete session file for a node, or all sessions if nodeid is None.
        """
        if not self.enabled:
            return

        if nodeid:
            filepath = self._session_path(nodeid)
            if os.path.exists(filepath):
                try:
                    os.remove(filepath)
                    log.debug(f"Invalidated session for node {nodeid}")
                except Exception as e:
                    log.debug(f"Failed to invalidate session for node {nodeid}: {e}")
        else:
            if os.path.exists(self.cache_dir):
                for entry in os.listdir(self.cache_dir):
                    sess_path = os.path.join(self.cache_dir, entry, SESSION_FILE)
                    if os.path.exists(sess_path):
                        try:
                            os.remove(sess_path)
                        except Exception:
                            pass
                log.debug("Invalidated all sessions")
