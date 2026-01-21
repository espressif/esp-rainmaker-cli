# SPDX-FileCopyrightText: 2018-2024 Espressif Systems (Shanghai) CO LTD
# SPDX-License-Identifier: Apache-2.0
#
import ipaddress
import socket
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


class Transport_HTTP(Transport):
    def __init__(self, hostname, ssl_context=None):
        host, port = parse_host_port(hostname)
        try:
            socket.getaddrinfo(host, None)
        except socket.gaierror:
            raise RuntimeError(f'Unable to resolve hostname: {host}')

        if ssl_context is None:
            self.conn = HTTPConnection(host, port, timeout=60)
        else:
            self.conn = HTTPSConnection(host, port, context=ssl_context, timeout=60)
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
