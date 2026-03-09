# SPDX-FileCopyrightText: 2018-2024 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
#
import ipaddress
import socket
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from http.client import HTTPConnection
from http.client import HTTPSConnection

from ..utils.convenience import str_to_bytes

from .transport import Transport

from typing import Tuple


def parse_host_port(hostname: str) -> Tuple[str, int]:
    """
    parse IP address/host and port from '<host>:<port>' or '[<ipv6>]:<port>'
    """

    if hostname.startswith('['):
        # IPv6: [<ipv6>]:<port>
        try:
            host_part, port_part = hostname.rsplit(']:', 1)
            host = host_part[1:]  # remove '['
        except ValueError:
            raise ValueError(f"invalid IPv6 address format: {hostname}")
        # check whether the ip address is valid
        try:
            ipaddress.ip_address(host)
        except ValueError:
            raise ValueError(f"invalid IP address: {host}")
    else:
        # <host>:<port>
        try:
            host, port_part = hostname.rsplit(':', 1)
        except ValueError:
            raise ValueError(f"invalid host name format: {hostname}")

    # check port number
    try:
        port = int(port_part)
        if not (0 <= port <= 65535):
            raise ValueError
    except ValueError:
        raise ValueError(f"invalid port: {port_part}")

    return host, port


def _resolve_with_timeout(host, port, resolve_timeout=None):
    """
    Resolve hostname with an optional timeout.
    socket.getaddrinfo has no timeout parameter, so we run it in a thread.
    """
    if resolve_timeout is None:
        return socket.getaddrinfo(host, port)
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(socket.getaddrinfo, host, port)
        try:
            return future.result(timeout=resolve_timeout)
        except FuturesTimeoutError:
            raise socket.gaierror(f'Resolution timed out after {resolve_timeout}s')


class Transport_HTTP(Transport):
    def __init__(self, hostname, ssl_context=None, timeout=60, resolve_timeout=None):
        host, port = parse_host_port(hostname)
        try:
            addrs = _resolve_with_timeout(host, port, resolve_timeout)
            self._resolved_ip = addrs[0][4][0]
        except socket.gaierror:
            raise RuntimeError(f'Unable to resolve hostname: {host}')

        self._host = host
        self._port = port
        self._ssl_context = ssl_context

        if ssl_context is None:
            self.conn = HTTPConnection(self._resolved_ip, port, timeout=timeout)
        else:
            self.conn = HTTPSConnection(self._resolved_ip, port, context=ssl_context, timeout=timeout)
        try:
            print(f'++++ Connecting to {hostname}++++')
            self.conn.connect()
        except Exception as err:
            raise RuntimeError('Connection Failure : ' + str(err))
        self.headers = {'Content-type': 'application/x-www-form-urlencoded','Accept': 'text/plain'}

    def _send_post_request(self, path, data):
        data = str_to_bytes(data) if isinstance(data, str) else data
        try:
            self.conn.request('POST', path, data, self.headers)
            response = self.conn.getresponse()
            # While establishing a session, the device sends the Set-Cookie header
            # with value 'session=cookie_session_id' in its first response of the session to the tool.
            # To maintain the same session, successive requests from the tool should include
            # an additional 'Cookie' header with the above received value.
            for hdr_key, hdr_val in response.getheaders():
                if hdr_key == 'Set-Cookie':
                    self.headers['Cookie'] = hdr_val
            if response.status == 200:
                return response.read().decode('latin-1')
        except Exception as err:
            raise RuntimeError('Connection Failure : ' + str(err))
        raise RuntimeError('Server responded with error code ' + str(response.status))

    def send_data(self, ep_name, data):
        return self._send_post_request('/' + ep_name, data)

    def get_cookie(self):
        return self.headers.get('Cookie')

    def set_cookie(self, cookie):
        if cookie:
            self.headers['Cookie'] = cookie

    def get_host_port(self):
        return self._host, self._port

    def get_resolved_host_port(self):
        return self._resolved_ip, self._port
