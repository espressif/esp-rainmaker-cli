# SPDX-FileCopyrightText: 2020-2025 Espressif Systems (Shanghai) CO LTD
#
# SPDX-License-Identifier: Apache-2.0

import requests
import json
import socket
from rmaker_lib import configmanager
from requests.exceptions import Timeout, ConnectionError,\
                                RequestException, HTTPError
from rmaker_lib.exceptions import HttpErrorResponse, NetworkError, InvalidClassInput, SSLError,\
                                  RequestTimeoutError
from rmaker_lib.logger import log


class Node:
    """
    Node class used to instantiate instances of node to perform various
    node operations.

    :param nodeid: Node Id of node
    :type nodeid: str

    :param session: :class:`rmaker_lib.session.Session`
    :type session: object
    """
    def __init__(self, nodeid, session):
        """
        Instantiate node with nodeid and session object.
        """
        log.info("Initialising node with nodeid : " + str(nodeid))
        self.__nodeid = nodeid
        self.__session = session
        try:
            self.request_header = {'content-type': 'application/json',
                                   'Authorization': session.id_token}
            # Use the config from session to maintain profile override
            self.config = session.config
        except AttributeError:
            raise InvalidClassInput(session, 'Invalid Session Input.\
                                              Expected: type <session object>.\
                                              Received: ')

    def get_nodeid(self):
        """
        Get nodeid of device

        :return: Node Id of node on Success
        :rtype: str
        """
        return self.__nodeid

    def get_node_status(self):
        """
        Get online/offline status of the node.

        :raises NetworkError: If there is a network connection issue while
                              getting node status
        :raises Exception: If there is an HTTP issue while getting node status

        :return: Status of node on Success
        :rtype: dict
        """
        log.info("Getting online/offline status of the node : " +
                 self.__nodeid)
        path = 'user/nodes/status'
        query_parameters = 'nodeid=' + self.__nodeid
        getnodestatus_url = self.config.get_host() + path + '?' + query_parameters
        try:
            log.debug("Get node status request url : " + getnodestatus_url)
            response = requests.get(url=getnodestatus_url,
                                    headers=self.request_header,
                                    verify=configmanager.CERT_FILE)
            log.debug("Get node status response : " + response.text)
            response.raise_for_status()

        except HTTPError as http_err:
            log.debug(http_err)
            raise HttpErrorResponse(response.json())
        except requests.exceptions.SSLError:
            raise SSLError
        except requests.exceptions.ConnectionError:
            raise NetworkError
        except Timeout as time_err:
            log.debug(time_err)
            raise RequestTimeoutError
        except Exception:
            raise Exception(response.text)
        log.info("Received node status successfully.")
        return response.json()

    def get_node_config(self):
        """
        Get node configuration.

        :raises NetworkError: If there is a network connection issue while
                              getting node configuration
        :raises Exception: If there is an HTTP issue while getting node config

        :return: Configuration of node on Success
        :rtype: dict
        """
        socket.setdefaulttimeout(10)
        log.info("Getting node config for node : " + self.__nodeid)
        path = 'user/nodes/config'
        query_parameters = 'nodeid=' + self.__nodeid
        getnodeconfig_url = self.config.get_host() + path + '?' + query_parameters
        try:
            log.debug("Get node config request url : " + getnodeconfig_url)
            response = requests.get(url=getnodeconfig_url,
                                    headers=self.request_header,
                                    verify=configmanager.CERT_FILE,
                                    timeout=(5.0, 5.0))
            log.debug("Get node config response : " + response.text)
            response.raise_for_status()

        except HTTPError as http_err:
            log.debug(http_err)
            raise HttpErrorResponse(response.json())
        except requests.exceptions.SSLError:
            raise SSLError
        except requests.exceptions.ConnectionError:
            raise NetworkError
        except Timeout as time_err:
            log.debug(time_err)
            raise RequestTimeoutError
        except RequestException as get_nodes_config_err:
            log.debug(get_nodes_config_err)
            raise get_nodes_config_err

        log.info("Received node config successfully.")
        return response.json()

    def get_node_params(self):
        """
        Get parameters of the node.

        :raises NetworkError: If there is a network connection issue while
                              getting node params
        :raises Exception: If there is an HTTP issue while getting node params
                           or JSON format issue in HTTP response

        :return: Node Parameters on Success, None on Failure
        :rtype: dict | None

        """
        socket.setdefaulttimeout(10)
        log.info("Getting parameters of the node with nodeid : " +
                 self.__nodeid)
        path = 'user/nodes/params'
        query_parameters = 'nodeid=' + self.__nodeid
        getparams_url = self.config.get_host() + path + '?' + query_parameters
        try:
            log.debug("Get node params request url : " + getparams_url)
            response = requests.get(url=getparams_url,
                                    headers=self.request_header,
                                    verify=configmanager.CERT_FILE,
                                    timeout=(5.0, 5.0))
            log.debug("Get node params response : " + response.text)
            response.raise_for_status()

        except HTTPError as http_err:
            log.debug(http_err)
            raise HttpErrorResponse(response.json())
        except requests.exceptions.SSLError:
            raise SSLError
        except requests.exceptions.ConnectionError:
            raise NetworkError
        except Timeout as time_err:
            log.debug(time_err)
            raise RequestTimeoutError
        except RequestException as get_nodes_params_err:
            log.debug(get_nodes_params_err)
            raise get_nodes_params_err

        response = json.loads(response.text)
        if 'status' in response and response['status'] == 'failure':
            return None
        log.info("Received node parameters successfully.")
        return response



    def set_node_params(self, data):
        """
        Set parameters of the node.

        :param data: Parameters to be set for the node
        :type data: dict

        :raises NetworkError: If there is a network connection issue while
                              setting node params
        :raises Exception: If there is an HTTP issue while setting node params
                           or JSON format issue in HTTP response

        :return: True on Success
        :rtype: bool
        """
        socket.setdefaulttimeout(10)
        log.info("Updating parameters of the node with nodeid : " +
                 self.__nodeid)
        
        # Always use the batch API format
        batch_data = [{
            "node_id": self.__nodeid,
            "payload": data
        }]
        
        result = self._set_params_api(batch_data, self.config, self.request_header)
        
        # Return boolean for backward compatibility with existing code
        return result.get("success", True)

    @staticmethod
    def _set_params_api(batch_data, config, request_header):
        """
        Internal method to call the set params API.
        
        :param batch_data: List of node data in format [{"node_id": "string", "payload": {...}}]
        :type batch_data: list
        :param config: Config object for getting host
        :param request_header: Request headers
        :type request_header: dict
        
        :raises NetworkError: If there is a network connection issue while setting node params
        :raises Exception: If there is an HTTP issue while setting node params
        
        :return: Dictionary with success/failure details for each node
        :rtype: dict
        """
        socket.setdefaulttimeout(10)
        path = 'user/nodes/params'
        setparams_url = config.get_host() + path
        
        try:
            log.debug("Set node params request url : " + setparams_url)
            log.debug("Set node params request payload : " + json.dumps(batch_data))
            log.debug("Set node params request header : " + json.dumps(request_header))
            response = requests.put(url=setparams_url,
                                    data=json.dumps(batch_data),
                                    headers=request_header,
                                    verify=configmanager.CERT_FILE,
                                    timeout=(5.0, 5.0))
            log.debug("Set node params response : " + response.text)
            response.raise_for_status()

        except HTTPError as http_err:
            log.debug(http_err)
            raise HttpErrorResponse(response.json())
        except requests.exceptions.SSLError:
            raise SSLError
        except requests.exceptions.ConnectionError:
            raise NetworkError
        except Timeout as time_err:
            log.debug(time_err)
            raise RequestTimeoutError
        except RequestException as set_nodes_params_err:
            log.debug(set_nodes_params_err)
            raise set_nodes_params_err
        
        # Parse response and analyze individual node results
        response_data = json.loads(response.text)
        
        if not isinstance(response_data, list):
            # Handle legacy response format or unexpected response
            log.info("Updated node parameters successfully.")
            return {"success": True, "results": []}
        
        # Analyze each node's result
        successful_nodes = []
        failed_nodes = []
        
        for node_result in response_data:
            node_id = node_result.get("node_id", "unknown")
            status = node_result.get("status", "unknown")
            description = node_result.get("description", "No description")
            
            if status == "success":
                successful_nodes.append({
                    "node_id": node_id,
                    "description": description
                })
            else:
                failed_nodes.append({
                    "node_id": node_id,
                    "status": status,
                    "description": description
                })
        
        result = {
            "success": len(failed_nodes) == 0,
            "total_nodes": len(response_data),
            "successful_nodes": successful_nodes,
            "failed_nodes": failed_nodes,
            "results": response_data
        }
        
        if result["success"]:
            log.info(f"Updated node parameters successfully for all {len(successful_nodes)} nodes.")
        else:
            log.warning(f"Updated parameters for {len(successful_nodes)} of {len(response_data)} nodes. {len(failed_nodes)} failed.")
        
        return result

    @staticmethod
    def set_node_params_multiple(node_params_list, session):
        """
        Set parameters for multiple nodes in a single API call.
        
        :param node_params_list: List of dictionaries with 'node_id' and 'payload' keys
        :type node_params_list: list
        :param session: Session object for authentication
        :type session: Session
        
        :raises NetworkError: If there is a network connection issue while setting node params
        :raises Exception: If there is an HTTP issue while setting node params
        
        :return: Dictionary with success/failure details for each node
        :rtype: dict
        
        Example:
            node_params_list = [
                {
                    "node_id": "node1",
                    "payload": {"Light": {"Power": True, "Brightness": 80}}
                },
                {
                    "node_id": "node2", 
                    "payload": {"Switch": {"Power": False}}
                }
            ]
        """
        if not node_params_list:
            raise ValueError("node_params_list cannot be empty")
            
        for item in node_params_list:
            if not isinstance(item, dict) or 'node_id' not in item or 'payload' not in item:
                raise ValueError("Each item must be a dict with 'node_id' and 'payload' keys")
                
        log.info(f"Updating parameters for {len(node_params_list)} nodes")
        return Node._set_params_api(node_params_list, session.config, session.request_header)

    def __user_node_mapping(self, secret_key, operation):
        """
        Add or remove the user node mapping.

        :param secret_key: The randomly generated secret key that will be
                           used for User-Node mapping
        :type secret_key: str

        :param operation: Operation to be performed, can take values
                          'add' or 'remove'
        :type operation: str

        :raises NetworkError: If there is a network connection issue
                              while adding user node mapping
        :raises Exception: If there is an HTTP issue or JSON format issue
                           in HTTP response

        :return: Request Id if Success, None if Failure
        :rtype: str | None
        """
        socket.setdefaulttimeout(10)
        path = 'user/nodes/mapping'
        config = configmanager.Config()
        userid = config.get_user_id()
        request_payload = {
            'user_id': userid,
            'node_id': self.__nodeid,
            'secret_key': secret_key,
            'operation': operation
        }

        request_url = self.config.get_host() + path
        try:
            log.debug("User node mapping request url : " + request_url)
            log.debug("User node mapping request payload : " +
                      str(request_payload))
            response = requests.put(url=request_url,
                                    data=json.dumps(request_payload),
                                    headers=self.request_header,
                                    verify=configmanager.CERT_FILE,
                                    timeout=(5.0, 5.0))
            log.debug("User node mapping response : " + response.text)
            response.raise_for_status()

        except HTTPError as http_err:
            log.debug(http_err)
            raise HttpErrorResponse(response.json())
        except requests.exceptions.SSLError as ssl_err:
            log.debug(ssl_err)
            raise SSLError
        except (ConnectionError, socket.timeout) as conn_err:
            log.debug(conn_err)
            raise NetworkError
        except Timeout as time_err:
            log.debug(time_err)
            raise RequestTimeoutError
        except RequestException as mapping_status_err:
            log.debug(mapping_status_err)
            raise mapping_status_err

        try:
            response = json.loads(response.text)
        except Exception as user_node_mapping_err:
            raise user_node_mapping_err

        if 'request_id' in response:
            return response['request_id']
        return None

    def add_user_node_mapping(self, secret_key):
        """
        Add user node mapping.

        :param secret_key:  The randomly generated secret key that will be
                            used for User-Node mapping
        :type secret_key: str

        :raises NetworkError: If there is a network connection issue while
                              adding user node mapping
        :raises Exception: If there is an HTTP issue while
                           adding user node mapping or
                           JSON format issue in HTTP response

        :return: Request Id on Success, None on Failure
        :rtype: str | None
        """
        log.info("Adding user node mapping request with nodeid : " +
                 self.__nodeid)
        return self.__user_node_mapping(secret_key, 'add')

    def remove_user_node_mapping(self):
        """
        Remove user node mapping request.

        :raises NetworkError: If there is a network connection issue while
                              removing user node mapping
        :raises Exception: If there is an HTTP issue while
                           removing user node mapping or
                           JSON format issue in HTTP response

        :return: Request Id on Success, None on Failure
        :rtype: str | None
        """
        log.info("Removing user node mapping with nodeid : " + self.__nodeid)
        secret_key = ""
        return self.__user_node_mapping(secret_key, 'remove')

    def get_mapping_status(self, request_id):
        """
        Check status of user node mapping request.

        :param requestId: Request Id
        :type requestId: str

        :raises NetworkError: If there is a network connection issue while
                              getting user node mapping status
        :raises Exception: If there is an HTTP issue while getting
                           user node mapping status or JSON format issue
                           in HTTP response

        :return: Request Status on Success, None on Failure
        :type: str | None
        """
        socket.setdefaulttimeout(10)
        log.debug("Checking status of user node mapping with request_id : " +
                  request_id)
        path = 'user/nodes/mapping'
        query_parameters = "&request_id=" + request_id

        request_url = self.config.get_host() + path + '?' + query_parameters
        try:
            log.debug("Check user node mapping status request url : " +
                      request_url)
            response = requests.get(url=request_url,
                                    headers=self.request_header,
                                    verify=configmanager.CERT_FILE,
                                    timeout=(5.0, 5.0))
            log.debug("Check user node mapping status response : " +
                      response.text)
            response.raise_for_status()

        except HTTPError as http_err:
            log.debug(http_err)
            raise HttpErrorResponse(response.json())
        except requests.exceptions.SSLError as ssl_err:
            log.debug(ssl_err)
            raise SSLError
        except (ConnectionError, socket.timeout) as conn_err:
            log.debug(conn_err)
            raise NetworkError
        except Timeout as time_err:
            log.debug(time_err)
            raise RequestTimeoutError
        except RequestException as mapping_status_err:
            log.debug(mapping_status_err)
            raise mapping_status_err

        try:
            response = json.loads(response.text)
        except Exception as mapping_status_err:
            raise mapping_status_err

        if 'request_status' in response:
            return response['request_status']
        return None

    def get_sharing_details_of_nodes(self):
        """
        Get sharing details of nodes associated with user
        
        :raises SSLError: If there is an SSL issue
        :raises HTTPError: If the HTTP response is an HTTPError
        :raises NetworkError: If there is a network connection issue
        :raises Timeout: If there is a timeout issue
        :raises RequestException: If there is an issue during
                                  the HTTP request
        :raises Exception: If there is an HTTP issue while getting shared nodes
                           or JSON format issue in HTTP response

        :return: HTTP response on Success
        :rtype: dict
        """
        socket.setdefaulttimeout(10)
        log.debug("Getting shared nodes of the node with nodeid : " +
                str(self.__nodeid))
        path = 'user/nodes/sharing'
        if self.__nodeid is not None:
            query_parameters = 'node_id=' + self.__nodeid
            log.debug("Get shared nodes query params : " + query_parameters)
            url = self.config.get_host() + path + '?' + query_parameters
        else:
            url = self.config.get_host() + path
        try:
            log.debug("Get shared nodes request url : " + url)
            log.debug("Request headers set: {}".format(self.request_header))
            response = requests.get(url=url,
                                    headers=self.request_header,
                                    verify=configmanager.CERT_FILE,
                                    timeout=(5.0, 5.0))
            log.debug("Get shared nodes response : " + response.text)

        except HTTPError as http_err:
            log.debug(http_err)
            return json.loads(http_err.response.text)
        except requests.exceptions.SSLError:
            raise SSLError
        except requests.exceptions.ConnectionError:
            raise NetworkError
        except Timeout as time_err:
            log.debug(time_err)
            raise RequestTimeoutError
        except RequestException as get_nodes_params_err:
            log.debug(get_nodes_params_err)
            raise get_nodes_params_err

        response = json.loads(response.text)
        log.debug("Received shared nodes successfully.")

        return response

    def request_op(self, data):
        """
        Perform sharing operations -

        1. Accept or decline sharing request

        :param data: 1. Data containing `request_id` and
                        `accept` as keys
        :type data: dict

        :raises SSLError: If there is an SSL issue
        :raises HTTPError: If the HTTP response is an HTTPError
        :raises NetworkError: If there is a network connection issue
        :raises Timeout: If there is a timeout issue
        :raises RequestException: If there is an issue during
                                  the HTTP request
        :raises Exception: If there is an HTTP issue while performing request operation
                           or JSON format issue in HTTP response

        :return: HTTP response on Success
        :rtype: dict
        """
        socket.setdefaulttimeout(10)
        log.debug("Setting shared nodes")
        path = 'user/nodes/sharing/requests'
        url = self.config.get_host() + path
        try:
            log.debug("Request op - request url: {}".format(url))
            log.debug("Request op - headers set: {}".format(self.request_header))
            log.debug("Request op - data: {}".format(data))
            response = requests.put(url=url,
                                    headers=self.request_header,
                                    data=json.dumps(data),
                                    verify=configmanager.CERT_FILE,
                                    timeout=(5.0, 5.0))
            log.debug("Request op - response : " + response.text)

        except HTTPError as http_err:
            log.debug(http_err)
            return json.loads(http_err.response.text)
        except requests.exceptions.SSLError:
            raise SSLError
        except requests.exceptions.ConnectionError:
            raise NetworkError
        except Timeout as time_err:
            log.debug(time_err)
            raise RequestTimeoutError
        except RequestException as get_nodes_params_err:
            log.debug(get_nodes_params_err)
            raise get_nodes_params_err

        response = json.loads(response.text)
        log.debug("Request operation accept: {} performed successfully.".format(data['accept']))

        return response

    def add_user_for_sharing(self, data):
        """
        Perform sharing operations -

        1. Request to add user for sharing nodes

        :param data: 1. To add nodes - 
                        Data containing `user_name` and `nodes` as keys
        :type data: dict
        
        :raises SSLError: If there is an SSL issue
        :raises HTTPError: If the HTTP response is an HTTPError
        :raises NetworkError: If there is a network connection issue
        :raises Timeout: If there is a timeout issue
        :raises RequestException: If there is an issue during
                                  the HTTP request
        :raises Exception: If there is an HTTP issue while performing sharing operation
                           or JSON format issue in HTTP response

        :return: HTTP response on Success
        :rtype: dict
        """
        socket.setdefaulttimeout(10)
        log.debug("Setting shared nodes")
        path = 'user/nodes/sharing'
        url = self.config.get_host() + path
        try:
            log.debug("Add user to share nodes request url: {}".format(url))
            log.debug("Request headers set: {}".format(self.request_header))
            log.debug("Add user to share nodes data: {}".format(data))
            response = requests.put(url=url,
                                    headers=self.request_header,
                                    data=json.dumps(data),
                                    verify=configmanager.CERT_FILE,
                                    timeout=(5.0, 5.0))
            log.debug("Add user to share nodes response : " + response.text)

        except HTTPError as http_err:
            log.debug(http_err)
            return json.loads(http_err.response.text)
        except requests.exceptions.SSLError:
            raise SSLError
        except requests.exceptions.ConnectionError:
            raise NetworkError
        except Timeout as time_err:
            log.debug(time_err)
            raise RequestTimeoutError
        except RequestException as get_nodes_params_err:
            log.debug(get_nodes_params_err)
            raise get_nodes_params_err

        response = json.loads(response.text)
        log.debug("Add user to share nodes successfully.")

        return response
    
    def remove_user_from_shared_nodes(self, data):
        """
        Remove user from shared nodes

        :param data: Data containing `user_name`
                     and `nodes` as keys
        :type data: dict
        
        :raises SSLError: If there is an SSL issue
        :raises HTTPError: If the HTTP response is an HTTPError
        :raises NetworkError: If there is a network connection issue
        :raises Timeout: If there is a timeout issue
        :raises RequestException: If there is an issue during
                                  the HTTP request
        :raises Exception: If there is an HTTP issue while removing shared nodes
                           or JSON format issue in HTTP response

        :return: HTTP response on Success
        :rtype: dict
        """
        socket.setdefaulttimeout(10)
        log.debug("Removing shared nodes")
        path = 'user/nodes/sharing'
        query_parameters = 'nodes=' + data['nodes'] + '&' + 'user_name=' + data['user_name']
        log.debug("Remove shared nodes query params: {}".format(query_parameters))
        url = self.config.get_host() + path + '?' + query_parameters
        try:
            log.debug("Remove shared nodes request url: {}".format(url))
            log.debug("Request headers set: {}".format(self.request_header))
            response = requests.delete(url=url,
                                        headers=self.request_header,
                                        verify=configmanager.CERT_FILE,
                                        timeout=(5.0, 5.0))
            log.debug("Remove shared nodes response : " + response.text)

        except HTTPError as http_err:
            log.debug(http_err)
            return json.loads(http_err.response.text)
        except requests.exceptions.SSLError:
            raise SSLError
        except requests.exceptions.ConnectionError:
            raise NetworkError
        except Timeout as time_err:
            log.debug(time_err)
            raise RequestTimeoutError
        except RequestException as get_nodes_params_err:
            log.debug(get_nodes_params_err)
            raise get_nodes_params_err

        response = json.loads(response.text)
        log.debug("Removed shared nodes successfully.")

        return response

    def remove_shared_nodes_request(self, req_id):
        """
        Remove/Cancel request sent to share nodes with user

        :param req_id: Id of sharing request
        :type data: str
    
        :raises SSLError: If there is an SSL issue
        :raises HTTPError: If the HTTP response is an HTTPError
        :raises NetworkError: If there is a network connection issue
        :raises Timeout: If there is a timeout issue
        :raises RequestException: If there is an issue during
                                  the HTTP request
        :raises Exception: If there is an HTTP issue while removing sharing request
                           or JSON format issue in HTTP response

        :return: HTTP response on Success
        :rtype: dict
        """
        socket.setdefaulttimeout(10)
        log.debug("Removing shared nodes request")
        path = 'user/nodes/sharing/requests'
        query_parameters = 'request_id=' + req_id
        log.debug("Remove shared nodes request query params: {}".format(query_parameters))
        url = self.config.get_host() + path + '?' + query_parameters
        try:
            log.debug("Remove shared nodes request url: {}".format(url))
            log.debug("Request headers set: {}".format(self.request_header))
            response = requests.delete(url=url,
                                        headers=self.request_header,
                                        verify=configmanager.CERT_FILE,
                                        timeout=(5.0, 5.0))
            log.debug("Remove sharing request response : " + response.text)

        except HTTPError as http_err:
            log.debug(http_err)
            return json.loads(http_err.response.text)
        except requests.exceptions.SSLError:
            raise SSLError
        except requests.exceptions.ConnectionError:
            raise NetworkError
        except Timeout as time_err:
            log.debug(time_err)
            raise RequestTimeoutError
        except RequestException as get_nodes_params_err:
            log.debug(get_nodes_params_err)
            raise get_nodes_params_err

        response = json.loads(response.text)
        log.debug("Received shared nodes successfully.")

        return response

    def get_shared_nodes_request(self, params):
        """
        Get request sent to share nodes with user

        :param params: Query parameters containing `request_id`
                       and `primary_user` as keys
        :type params: dict
        
        :raises SSLError: If there is an SSL issue
        :raises HTTPError: If the HTTP response is an HTTPError
        :raises NetworkError: If there is a network connection issue
        :raises Timeout: If there is a timeout issue
        :raises RequestException: If there is an issue during
                                  the HTTP request
        :raises Exception: If there is an HTTP issue while getting sharing request
                           or JSON format issue in HTTP response

        :return: HTTP response on Success
        :rtype: dict
        """
        socket.setdefaulttimeout(10)
        log.debug("Getting shared nodes request")
        path = 'user/nodes/sharing/requests'
        query_parameters = ""
        if params is not None:
            if 'id' in params:
                query_parameters = 'request_id=' + params['id'] + '&'
            query_parameters += 'primary_user=' + params['primary_user']
            log.debug("Get sharing request query params : " + query_parameters)
            url = self.config.get_host() + path + '?' + query_parameters
        else:
            url = self.config.get_host() + path
        try:
            log.debug("Get sharing request url : " + url)
            log.debug("Request headers set: {}".format(self.request_header))
            response = requests.get(url=url,
                                    headers=self.request_header,
                                    verify=configmanager.CERT_FILE,
                                    timeout=(5.0, 5.0))
            log.debug("Get shared nodes response : " + response.text)

        except HTTPError as http_err:
            log.debug(http_err)
            return json.loads(http_err.response.text)
        except requests.exceptions.SSLError:
            raise SSLError
        except requests.exceptions.ConnectionError:
            raise NetworkError
        except Timeout as time_err:
            log.debug(time_err)
            raise RequestTimeoutError
        except RequestException as get_nodes_params_err:
            log.debug(get_nodes_params_err)
            raise get_nodes_params_err

        response = json.loads(response.text)
        log.debug("Received shared nodes successfully.")

        return response