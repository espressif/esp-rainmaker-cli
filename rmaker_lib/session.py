# SPDX-FileCopyrightText: 2020-2025 Espressif Systems (Shanghai) CO LTD
#
# SPDX-License-Identifier: Apache-2.0

import requests
import json
import socket
from rmaker_lib import serverconfig, configmanager
from rmaker_lib import node
from rmaker_lib.exceptions import HttpErrorResponse, NetworkError, InvalidConfigError, SSLError,\
    RequestTimeoutError
from rmaker_lib.logger import log


class Session:
    """
    Session class for logged in user.
    """
    def __init__(self, profile_override=None):
        """
        Instantiate session for logged in user.
        
        :param profile_override: Optional profile name to use instead of current profile.
        """
        self.config = configmanager.Config(profile_override=profile_override)
        log.info("Initialising session for user")
        
        # Check if user is logged in to current profile
        current_profile = self.config.get_current_profile_name()
        if not self.config.profile_manager.has_profile_tokens(current_profile):
            profile_config = self.config.profile_manager.get_profile_config(current_profile)
            profile_type = "builtin" if profile_config.get('builtin', False) else "custom"
            is_builtin = profile_config.get('builtin', False)
            
            print(f"\n❌ Not logged in to profile '{current_profile}'")
            print(f"Please login to this {profile_type} profile first:")
            
            if profile_type == "custom":
                print(f"   esp-rainmaker-cli login --user_name <your_email>")
            else:
                print(f"   esp-rainmaker-cli login")
                print(f"   # or with credentials:")
                print(f"   esp-rainmaker-cli login --user_name <your_email>")
            print()
            raise InvalidConfigError("Not logged in to current profile")
        
        self.id_token = self.config.get_access_token()
        if self.id_token is None:
            print(f"\n❌ No valid tokens found for profile '{current_profile}'")
            print(f"Please login to this profile:")
            print(f"   esp-rainmaker-cli login")
            print()
            raise InvalidConfigError("No valid access token found")
        
        # Check if tokens might be for wrong region by looking at token issuer
        try:
            import base64
            import json as json_lib
            # Decode JWT token to check issuer (without verification for quick check)
            token_parts = self.id_token.split('.')
            if len(token_parts) >= 2:
                # Add padding if needed for base64 decoding
                payload = token_parts[1]
                padding = 4 - (len(payload) % 4)
                if padding != 4:
                    payload += '=' * padding
                
                decoded_payload = base64.b64decode(payload)
                token_data = json_lib.loads(decoded_payload)
                token_issuer = token_data.get('iss', '')
                
                # Check if token issuer matches current profile region
                current_region = self.config.get_region()
                if current_region == 'china' and 'cognito-idp.us-east-1' in token_issuer:
                    print(f"\n❌ You have global region tokens in china profile")
                    print(f"Please login to china profile to get correct tokens:")
                    print(f"   esp-rainmaker-cli login")
                    print()
                    raise InvalidConfigError("Wrong region tokens")
                elif current_region == 'global' and 'cognito-idp.us-east-1' not in token_issuer and current_region != 'custom':
                    print(f"\n❌ You have china region tokens in global profile")
                    print(f"Please login to global profile to get correct tokens:")
                    print(f"   esp-rainmaker-cli login")
                    print()
                    raise InvalidConfigError("Wrong region tokens")
        except Exception:
            # If token inspection fails, continue - let the API call fail with proper error
            pass
        
        self.request_header = {'Content-Type': 'application/json',
                               'Authorization': self.id_token}

    def get_nodes(self):
        """
        Get list of all nodes associated with the user.

        :raises NetworkError: If there is a network connection issue
                              while getting nodes associated with user
        :raises Exception: If there is an HTTP issue while getting nodes

        :return: Nodes associated with user on Success
        :rtype: dict
        """
        log.info("Getting nodes associated with the user.")
        path = 'user/nodes'
        
        node_map = {}
        start_id = None
        has_more = True
        
        while has_more:
            query_parameters = ''
            if start_id:
                query_parameters = f'start_id={start_id}'
                getnodes_url = f"{self.config.get_host()}{path}?{query_parameters}"
            else:
                getnodes_url = self.config.get_host() + path
                
            try:
                log.debug("Get nodes request url : " + getnodes_url)
                response = requests.get(url=getnodes_url,
                                        headers=self.request_header,
                                        verify=configmanager.CERT_FILE)
                log.debug("Get nodes request response : " + response.text)
                response.raise_for_status()

            except requests.exceptions.HTTPError as http_err:
                log.debug(http_err)
                raise HttpErrorResponse(response.json())
            except requests.exceptions.SSLError:
                raise SSLError
            except requests.exceptions.ConnectionError:
                raise NetworkError
            except Exception:
                raise Exception(response.text)

            response_data = json.loads(response.text)
            for nodeid in response_data['nodes']:
                node_map[nodeid] = node.Node(nodeid, self)
                
            # Check if there are more nodes to fetch
            if 'next_id' in response_data and response_data['next_id']:
                start_id = response_data['next_id']
            else:
                has_more = False
                
        log.info(f"Received all {len(node_map)} nodes for user successfully.")
        return node_map

    def get_node_details(self):
        """
        Get detailed information for all nodes including config, status, and params.

        :raises NetworkError: If there is a network connection issue
                              while getting node details
        :raises Exception: If there is an HTTP issue while getting node details

        :return: Detailed information for all nodes on Success
        :rtype: dict
        """
        log.info("Getting detailed information for all nodes.")
        path = 'user/nodes'
        
        all_nodes = []
        start_id = None
        has_more = True
        
        while has_more:
            query_parameters = 'node_details=true'
            if start_id:
                query_parameters += f'&start_id={start_id}'
            
            getnodedetails_url = self.config.get_host() + path + '?' + query_parameters

            try:
                log.debug("Get node details request url : " + getnodedetails_url)
                response = requests.get(url=getnodedetails_url,
                                        headers=self.request_header,
                                        verify=configmanager.CERT_FILE)
                log.debug("Get node details response : " + response.text)
                response.raise_for_status()

            except requests.exceptions.HTTPError as http_err:
                log.debug(http_err)
                raise HttpErrorResponse(response.json())
            except requests.exceptions.SSLError:
                raise SSLError
            except requests.exceptions.ConnectionError:
                raise NetworkError
            except Exception:
                raise Exception(response.text)

            response_data = json.loads(response.text)
            
            # Add nodes from current page to result
            if 'node_details' in response_data:
                all_nodes.extend(response_data['node_details'])
            
            # Check if there are more nodes to fetch
            if 'next_id' in response_data and response_data['next_id']:
                start_id = response_data['next_id']
            else:
                has_more = False
        
        # Construct the final response with all nodes
        node_details = {
            'node_details': all_nodes,
            'total': len(all_nodes)
        }
        
        log.info(f"Received detailed information for all {len(all_nodes)} nodes successfully.")
        return node_details

    def get_node_details_by_id(self, node_id):
        """
        Get detailed information for a specific node including config, status, and params.

        :param node_id: ID of the node to fetch details for
        :type node_id: str
        
        :raises NetworkError: If there is a network connection issue
                              while getting node details
        :raises Exception: If there is an HTTP issue while getting node details

        :return: Detailed information for the specified node on Success
        :rtype: dict
        """
        log.info(f"Getting detailed information for node {node_id}.")
        path = 'user/nodes'
        query_parameters = f'node_details=true&node_id={node_id}'
        getnodedetails_url = self.config.get_host() + path + '?' + query_parameters

        try:
            log.debug("Get node details request url : " + getnodedetails_url)
            response = requests.get(url=getnodedetails_url,
                                    headers=self.request_header,
                                    verify=configmanager.CERT_FILE)
            log.debug("Get node details response : " + response.text)
            response.raise_for_status()

        except requests.exceptions.HTTPError as http_err:
            log.debug(http_err)
            raise HttpErrorResponse(response.json())
        except requests.exceptions.SSLError:
            raise SSLError
        except requests.exceptions.ConnectionError:
            raise NetworkError
        except Exception:
            raise Exception(response.text)

        node_details = json.loads(response.text)
        log.info(f"Received detailed information for node {node_id} successfully.")
        return node_details

    def get_mqtt_host(self):
        """
        Get the MQTT Host endpoint.

        :raises NetworkError: If there is a network connection issue
                              while getting MQTT Host endpoint
        :raises Exception: If there is an HTTP issue while getting MQTT host
                           or JSON format issue in HTTP response

        :return: MQTT Host on Success, None on Failure
        :rtype: str | None
        """
        log.info("Getting MQTT Host endpoint.")
        path = 'mqtt_host'
        request_url = self.config.get_host().split(serverconfig.VERSION)[0] + path
        try:
            log.debug("Get MQTT Host request url : " + request_url)
            response = requests.get(url=request_url,
                                    verify=configmanager.CERT_FILE)
            log.debug("Get MQTT Host response : " + response.text)
            response.raise_for_status()

        except requests.exceptions.HTTPError as http_err:
            log.debug(http_err)
            raise HttpErrorResponse(response.json())
        except requests.exceptions.SSLError:
            raise SSLError
        except requests.exceptions.ConnectionError:
            raise NetworkError
        except Exception as mqtt_host_err:
            raise mqtt_host_err

        try:
            response = json.loads(response.text)
        except Exception as json_decode_err:
            raise json_decode_err

        if 'mqtt_host' in response:
            log.info("Received MQTT Host endpoint successfully.")
            return response['mqtt_host']
        return None

    def get_user_details(self):
        """
        Get details of current logged-in user

        :raises SSLError: If there is an SSL issue
        :raises HTTPError: If the HTTP response is an HTTPError
        :raises NetworkError: If there is a network connection issue
        :raises Timeout: If there is a timeout issue
        :raises RequestException: If there is an issue during
                                  the HTTP request
        :raises Exception: If there is an HTTP issue while getting user details
                           or JSON format issue in HTTP response

        :return: HTTP response on Success
        :rtype: dict
        """
        socket.setdefaulttimeout(10)
        log.info('Getting details of current logged-in user')
        version = serverconfig.VERSION
        path = '/user'
        getdetails_url = self.config.get_host().rstrip('/') + path
        try:
            log.debug("Get user details request url : " + getdetails_url)
            response = requests.get(url=getdetails_url,
                                    headers=self.request_header,
                                    verify=configmanager.CERT_FILE,
                                    timeout=(5.0, 5.0))
            log.debug("Get user details request response : " + response.text)
            response.raise_for_status()

        except requests.exceptions.HTTPError as http_err:
            log.debug(http_err)
            return json.loads(http_err.response.text)
        except requests.exceptions.SSLError:
            raise SSLError
        except requests.exceptions.ConnectionError:
            raise NetworkError
        except requests.exceptions.Timeout as time_err:
            log.debug(time_err)
            raise RequestTimeoutError
        except requests.exceptions.RequestException as req_err:
            log.debug(req_err)
            raise req_err
        except Exception:
            raise Exception(response.text)

        log.info("Received user details successfully.")
        try:
            return json.loads(response.text)
        except Exception as resp_err:
            raise resp_err

    def logout(self):
        """
        Logout current logged-in user

        :raises SSLError: If there is an SSL issue
        :raises HTTPError: If the HTTP response is an HTTPError
        :raises NetworkError: If there is a network connection issue
        :raises Timeout: If there is a timeout issue
        :raises RequestException: If there is an issue during
                                  the HTTP request
        :raises Exception: If there is an HTTP issue while logging out
                           or JSON format issue in HTTP response

        :return: HTTP response on Success
        :rtype: dict
        """
        socket.setdefaulttimeout(10)
        log.info('Logging out current logged-in user')
        version = serverconfig.VERSION
        path = '/logout2'
        # Logout only from current session
        query_params = 'logout_all=false'
        logout_url = self.config.get_host().rstrip('/') + path + '?' + query_params
        try:
            log.debug("Logout request url : " + logout_url)
            log.debug("Logout headers: {}".format(self.request_header))
            response = requests.post(url=logout_url,
                                     headers=self.request_header,
                                     verify=configmanager.CERT_FILE,
                                     timeout=(5.0, 5.0))
            log.debug("Logout request response : " + response.text)
            response.raise_for_status()

        except requests.exceptions.HTTPError as http_err:
            log.debug(http_err)
            raise HttpErrorResponse(response.json())
        except requests.exceptions.SSLError:
            raise SSLError
        except requests.exceptions.ConnectionError:
            raise NetworkError
        except requests.exceptions.Timeout as time_err:
            log.debug(time_err)
            raise RequestTimeoutError
        except requests.exceptions.RequestException as req_err:
            log.debug(req_err)
            raise req_err
        except Exception:
            raise Exception(response.text)

        try:
            log.info("Logout API call successful")
            return json.loads(response.text)
        except Exception as resp_err:
            raise resp_err