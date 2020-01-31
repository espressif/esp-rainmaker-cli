# Copyright 2020 Espressif Systems (Shanghai) PTE LTD
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

import webbrowser
import string
import socket
import random
from requests.exceptions import HTTPError
import requests
from oauth2client import _helpers
from six.moves import BaseHTTPServer, http_client, urllib
import os, json, sys, base64

try:
    from lib import projectconfig, configmanager
    from lib.logger import log
except Exception as importError:
    print("Failed to import ESP Rainmaker library. " + importError)
    sys.exit(1)
    
class HttpdServer(BaseHTTPServer.HTTPServer):
    """
    A server to handle requests on localhost.

    Waits for a single request and parses the query parameters
    into query_params and then stops serving.
    """
    query_params = {}


class HttpdRequestHandler(BaseHTTPServer.BaseHTTPRequestHandler):
    """
    A server to handle requests on localhost.

    Waits for a single request and parses the query parameters
    into the servers query_params and then stops serving.
    """

    def do_GET(self):
        """
        Handle a GET request.
        """
        log.debug('Loading the welcome page after successful login.')
        self.send_response(http_client.OK)
        self.send_header('Content-type', 'text/html')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        parts = urllib.parse.urlparse(self.path)
        query = _helpers.parse_unique_urlencoded(parts.query)
        self.server.query_params = query
        index_file = os.path.join(os.path.expanduser('.'), 'html/welcome.html')

        try :
            with open(index_file, 'rb') as home_page:
                self.wfile.write(home_page.read())
        except Exception as errOpenFile :
            log.error(errOpenFile)
            sys.exit(1)

    def log_message(self, format, *args):
        """
        Do not log messages to the command prompt.
        """

def get_free_port():
    tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    tcp.bind(('', 0))
    addr, port = tcp.getsockname()
    tcp.close()
    return port

def browser_login():
    """
    Opens browser with login url.
    Opens Httpd server to handle the GET request.
    """
    log.info('Logging in through browser')
    server_instance = None
    for attempt in range(10):
        try:
            port = get_free_port()
            server_instance = HttpdServer(('localhost', port), HttpdRequestHandler)
            # Added timeout to handle keyboard interrupts for browser login.
            server_instance.timeout = 0.5 
            break
        except socket.error as err:
            log.warn('Error %s. Port %s is not available. Trying with next port.', err, port)

    if server_instance is None:
        log.error('Error: Could not launch local webserver. Use --email option instead.')
        return

    url = projectconfig.LOGIN_URL + str(port) + '&host_url=' + projectconfig.HOST + 'login' + '&github_url=' + projectconfig.GITHUB_URL + str(port)
    print('Opening browser window for login...')
    openStatus = webbrowser.open(url)
    if openStatus is False:
        log.error('Failed to open login page. Please try again.')
        return
    else:
        print('Use the browser for login. Press ctrl+C to abort.')
    log.debug('Web browser opened. Waiting for user login.')
    try:
        while True:
            server_instance.handle_request()
            if 'error' in server_instance.query_params:
                log.error('Authentication Error: "%s". Description: "%s" ' + server_instance.query_params['error'] + server_instance.query_params.ge('error_description'))
                return
            if 'code' in server_instance.query_params:
                log.debug('Login successful. Received authorization code.')
                code = server_instance.query_params['code']
                get_tokens(code)
                print('Login successful')
                return
            if 'id_token' in server_instance.query_params and 'refresh_token' in server_instance.query_params:
                log.debug('Login successful. Received idtoken and refresh token.')
                configData = {}
                configData['idtoken'] = server_instance.query_params['id_token']
                configData['refreshtoken'] = server_instance.query_params['refresh_token']
                configmanager.Config().set_config(configData)
                print('Login successful')
                return
    except Exception as browserLoginError:
        log.error(browserLoginError)

def get_tokens(code):
    """
    Set the config file after successful browser login.
    """
    log.info('Getting access tokens using authorization code.')
    client_id = projectconfig.CLIENT_ID
    client_secret = projectconfig.CLIENT_SECRET
    request_data = 'grant_type=authorization_code&client_id=' + client_id + '&code=' + code + '&client_secret=' + client_secret + '&redirect_uri=' + projectconfig.REDIRECT_URL
    authorization_value = 'Basic ' + base64.b64encode(bytes((client_id + ':' + client_secret).encode('utf-8'))).decode("utf-8")
    request_header = {'content-type': 'application/x-www-form-urlencoded', 'Authorization' : authorization_value}
    try:
        response = requests.post(url = projectconfig.TOKEN_URL, data = request_data, headers = request_header)
        response.raise_for_status()
    except Exception as getTokenError:
        log.error(getTokenError)
        sys.exit(1)
    else:
        configData = {}
        result = response.json()
        configData['idtoken'] = result['id_token']
        configData['refreshtoken'] = result['refresh_token']
        log.debug('Received access tokens using authorization code.')
        configmanager.Config().set_config(configData)
    return
