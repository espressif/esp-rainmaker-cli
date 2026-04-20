# SPDX-FileCopyrightText: 2026 Espressif Systems (Shanghai) CO LTD
#
# SPDX-License-Identifier: Apache-2.0

import requests
import json
import socket
from rmaker_lib import configmanager
from requests.exceptions import Timeout, ConnectionError, RequestException, HTTPError
from rmaker_lib.exceptions import HttpErrorResponse, NetworkError, SSLError, RequestTimeoutError
from rmaker_lib.logger import log


class AWSCredentials:
    """
    AWS Credentials class for managing temporary AWS credentials for KVS video streaming.
    """

    def __init__(self, access_key_id, secret_access_key, session_token, region, expiration=None):
        """
        Initialize AWS credentials.

        :param access_key_id: AWS access key ID
        :type access_key_id: str
        :param secret_access_key: AWS secret access key
        :type secret_access_key: str
        :param session_token: AWS session token
        :type session_token: str
        :param region: AWS region
        :type region: str
        :param expiration: Credential expiration timestamp (optional)
        :type expiration: int | None
        """
        self.access_key_id = access_key_id
        self.secret_access_key = secret_access_key
        self.session_token = session_token
        self.region = region
        self.expiration = expiration

    def is_expired(self):
        """
        Check if credentials are expired.

        :return: True if expired, False otherwise
        :rtype: bool
        """
        if self.expiration is None:
            return False
        import time
        return time.time() >= self.expiration

    def to_dict(self):
        """
        Convert credentials to dictionary format.

        :return: Dictionary with credential keys
        :rtype: dict
        """
        return {
            'access_key_id': self.access_key_id,
            'secret_access_key': self.secret_access_key,
            'session_token': self.session_token,
            'region': self.region
        }


def get_video_streaming_credentials(session, node_id, channel_name=None):
    """
    Get AWS credentials for video streaming via assume role API.

    :param session: RainMaker session object
    :type session: rmaker_lib.session.Session
    :param node_id: Node ID of the camera device
    :type node_id: str
    :param channel_name: Optional channel name/ARN (if not provided, will be fetched from node)
    :type channel_name: str | None

    :raises NetworkError: If there is a network connection issue
    :raises HttpErrorResponse: If there is an HTTP error response
    :raises SSLError: If there is an SSL issue
    :raises RequestTimeoutError: If the request times out
    :raises Exception: If there is any other error

    :return: AWSCredentials object on success
    :rtype: AWSCredentials
    """
    socket.setdefaulttimeout(10)
    log.info(f"Getting AWS credentials for video streaming for node {node_id}")

    # Based on Android implementation, the endpoint is user/assume_role
    # Payload format: {"user_role": "videostream", "node_ids": ["node_id"]}
    # Note: accessToken is passed in headers (via session.request_header), not in body
    # The session.request_header already contains Authorization header with the token

    # Build request payload according to Android implementation format
    payload = {
        'user_role': 'videostream'
    }

    # Add node_ids only if node_id is provided (optional in Android, matches Android logic)
    if node_id:
        payload['node_ids'] = [node_id]

    # The endpoint is user/assume_role (not user/nodes/video/credentials)
    endpoint = 'user/assume_role'
    request_url = session.config.get_host() + endpoint

    log.info(f"Requesting AWS credentials via assume_role API")
    log.debug(f"Get video streaming credentials request url: {request_url}")
    log.debug(f"Get video streaming credentials request payload: {json.dumps(payload, indent=2)}")

    try:
        # POST request with JSON body (based on rmaker_assume_role.py)
        response = requests.post(
            url=request_url,
            headers=session.request_header,
            json=payload,
            verify=configmanager.CERT_FILE,
            timeout=(10.0, 10.0)
        )

        log.debug(f"Get video streaming credentials response: {response.text}")
        response.raise_for_status()

        # Parse response
        response_data = json.loads(response.text)

        # Log full response for debugging
        log.debug(f"Full assume_role API response: {json.dumps(response_data, indent=2)}")

        # Handle different response formats
        if 'status' in response_data and response_data['status'].lower() != 'success':
            error_msg = response_data.get('description', 'Unknown error')
            log.error(f"Failed to get credentials: {error_msg}")
            raise HttpErrorResponse(response_data)

        # Extract credentials from response
        # The API response has credentials at top level with fields: access_key, secret_key, session_token
        # Check both nested and top-level locations
        if 'credentials' in response_data:
            creds = response_data['credentials']
        elif 'aws_credentials' in response_data:
            creds = response_data['aws_credentials']
        elif 'Credential' in response_data:
            # AWS AssumeRole response format
            creds = response_data['Credential']
        else:
            # Credentials are at top level
            creds = response_data

        # Extract credentials - handle different response formats
        # The API returns: access_key, secret_key, session_token (at top level)
        # Also check nested creds object and common AWS field names
        # Priority: response_data (top level) > creds (nested) > AWS standard names
        access_key_id = (response_data.get('access_key') or
                        creds.get('access_key') or
                        creds.get('access_key_id') or creds.get('AccessKeyId'))
        secret_access_key = (response_data.get('secret_key') or
                            creds.get('secret_key') or
                            creds.get('secret_access_key') or creds.get('SecretAccessKey'))
        session_token = (response_data.get('session_token') or
                        creds.get('session_token') or creds.get('SessionToken'))
        region = (response_data.get('region') or
                 creds.get('region') or creds.get('Region') or 'us-east-1')
        expiration = (response_data.get('expiration') or
                     creds.get('expiration') or creds.get('Expiration'))

        if not all([access_key_id, secret_access_key, session_token]):
            log.error(f"Incomplete credentials in response. Response: {json.dumps(response_data, indent=2)}")
            raise Exception("Incomplete credentials in response")

        # Convert expiration timestamp if provided as string
        if expiration and isinstance(expiration, str):
            from datetime import datetime
            try:
                expiration_dt = datetime.fromisoformat(expiration.replace('Z', '+00:00'))
                expiration = int(expiration_dt.timestamp())
            except Exception:
                log.warning(f"Could not parse expiration timestamp: {expiration}")

        aws_creds = AWSCredentials(
            access_key_id=access_key_id,
            secret_access_key=secret_access_key,
            session_token=session_token,
            region=region,
            expiration=expiration
        )

        log.info("Successfully retrieved AWS credentials for video streaming")
        log.debug(f"Credentials - Access Key ID: {access_key_id[:10]}..., Region: {region}")

        # Verify credentials by checking if they can be used (will be verified when making actual API calls)
        return aws_creds

    except HTTPError as http_err:
        # Log the actual error response for debugging
        error_response = None
        try:
            error_response = http_err.response.json()
            log.error(f"API error response: {json.dumps(error_response, indent=2)}")
            log.error(f"Status code: {http_err.response.status_code}")
            log.error(f"Response text: {http_err.response.text}")
        except Exception:
            log.error(f"Failed to parse error response: {http_err.response.text}")
            error_response = {'status': 'failure', 'description': http_err.response.text}
        log.debug(http_err)
        raise HttpErrorResponse(error_response)
    except requests.exceptions.SSLError:
        raise SSLError
    except requests.exceptions.ConnectionError:
        raise NetworkError
    except Timeout as time_err:
        log.debug(time_err)
        raise RequestTimeoutError
    except RequestException as req_err:
        log.debug(req_err)
        raise req_err
    except Exception as e:
        log.error(f"Unexpected error getting AWS credentials: {e}")
        raise
