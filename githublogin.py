#!/usr/bin/env python3
#
# Copyright 2019 Espressif Systems (Shanghai) PTE LTD
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import webbrowser
import string
import socket
import random
import os, json
from constants import *
from config import *
from six.moves import BaseHTTPServer
from six.moves import http_client
from six.moves import urllib
from logger import log
from requests.exceptions import HTTPError
import requests
from utility import setProfileCredentials
from oauth2client import _helpers
import sys

access_key = None
id_token = None
redirect_url = None

class ClientRedirectServer(BaseHTTPServer.HTTPServer):
    """
    A server to handle OAuth 2.0 redirects back to localhost.

    Waits for a single request and parses the query parameters
    into query_params and then stops serving.
    """
    query_params = {}


class ClientRedirectHandler(BaseHTTPServer.BaseHTTPRequestHandler):
    """
    A handler for OAuth 2.0 redirects back to localhost.

    Waits for a single request and parses the query parameters
    into the servers query_params and then stops serving.
    """

    def do_GET(self):
        """
        Handle a GET request.

        Parses the query parameters and prints a message
        if the flow has completed. Note that we can't detect
        if an error occurred.
        """
        self.send_response(http_client.OK)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        parts = urllib.parse.urlparse(self.path)
        query = _helpers.parse_unique_urlencoded(parts.query)
        self.server.query_params = query
        index_file = os.path.join(os.path.expanduser('.'), INDEX_PAGE)

        try :
            with open(index_file, 'rb') as home_page:
                self.wfile.write(home_page.read())
        except Exception as errOpenFile :
            log.error(f'Opening index page failed : {errOpenFile}')
            print(f'Login failed. Please login again.')
            sys.exit(0)

    def log_message(self, format, *args):
        """
        Do not log messages to stdout while running as cmd. line program.
        """


def login_github():
    """
    Opens browser with login url.
    After successful login, redirects to redirect url.
    Opens redirect server to hanlde the redirect request.
    """
    for port in range(8400, 8410):
        try:
            server_instance = ClientRedirectServer(('localhost', port), ClientRedirectHandler)
            redirect_url = "http://localhost:{}".format(port)
            break
        except socket.error as err:
            print("Port %s is not available with error %s. Trying with next port", port, err)

    if redirect_url is None:
        print("Error: can't reserve a port for authentication redirect url")
        return

    try:
        request_state = ''.join(random.SystemRandom().choice(string.ascii_lowercase + string.digits) for _ in range(20))
    except NotImplementedError:
        request_state = 'state'

    url = GITHUB_LOGIN_URL.format(CLIENT_ID, redirect_url)
    openStatus = webbrowser.open(url)
    if openStatus is False:
        print("Failed to open login page. Please try again")

    while True:
        server_instance.handle_request()
        if 'error' in server_instance.query_params:
            break
        if 'access_token' in server_instance.query_params and 'id_token' in server_instance.query_params:
            id_token = server_instance.query_params['id_token']
            setConfigFile(id_token)
            print("login successful..!!")
            sys.exit(0)

    if 'error' in server_instance.query_params:
        print('Authentication Error: "%s". Description: "%s" ', server_instance.query_params['error'],
                       server_instance.query_params.get('error_description'))
        return


def setConfigFile(id_token) :
    """
    configures the rainmaker config file
    """
    path = PATH_PREFIX + 'getkeys'
    request_header = {'content-type': 'application/json', 'Authorization': id_token}
    url = HTTPS_PREFIX + HOST + path

    try:
        response = requests.get(url = url, headers = request_header)
        response.raise_for_status()
   
    except requests.ConnectionError:
        print("Please check the internet connectivity. No internet connection available")
        sys.exit(1)

    except Exception as err:
        print(f'Setting config file failed. Please login again.')
        log.error(f'Setting config file failed. Please login again. : {err}')
        sys.exit(1)

    try :
        response = json.loads(response.text)
    except Exception as err:
        print(f'Setting config file failed. Please login again.')
        log.error(f'Parsing JSON for setConfigFile failed : {err}')
        sys.exit(1)

    if 'access_key_id' in response and 'secret_acccess_key' in response:
        setProfileCredentials(response['access_key_id'], response['secret_acccess_key'])
    else :
        print(response)