# SPDX-FileCopyrightText: 2020-2025 Espressif Systems (Shanghai) CO LTD
#
# SPDX-License-Identifier: Apache-2.0


class NetworkError(Exception):
    """ Raised when internet connection is not available """
    def __str__(self):
        return ('Could not connect. '
                'Please check your Internet connection.')


class RequestTimeoutError(Exception):
    """ Raised when HTTP Request times out """
    def __str__(self):
        return ('HTTP Request timed out. '
                'Please check your Internet connection.')


class InvalidJSONError(Exception):
    """ Raised for invalid JSON input """
    def __str__(self):
        return 'Invalid JSON received.'


class ExpiredSessionError(Exception):
    """ Raised when user session expires """
    def __str__(self):
        return 'User session is expired. Please login again.'


class InvalidConfigError(Exception):
    """ Raised for invalid configuration """
    def __str__(self):
        return 'Invalid configuration. Please login again.'


class InvalidUserError(Exception):
    """ Raised when config file does not exists """
    def __str__(self):
        return 'User not logged in. Please use login command.'


class AuthenticationError(Exception):
    """ Raised when user login fails """
    def __str__(self):
        return 'Login failed. Please try again'


class InvalidApiVersionError(Exception):
    """ Raised when current API version is not supported """
    def __str__(self):
        return 'API Version not supported. Please upgrade ESP Rainmaker CLI.'


class InvalidClassInput(Exception):
    """ Raised for invalid Session input """
    def __init__(self, input_arg, err_str):
        self.arg = input_arg
        self.err_str = err_str

    def __str__(self):
        return '{} {}'.format(self.err_str, self.arg)


class SSLError(Exception):
    """ Raised when invalid SSL certificate is passed """
    def __str__(self):
        return 'Unable to verify SSL certificate.'

class HttpErrorResponse(Exception):
    """ Raise error when HTTP request fails"""
    def __init__(self, err_resp):
        self.err_resp = err_resp

    def __str__(self):
        try:
            # Standard ESP RainMaker error response format
            return '{:<7} ({}):  {}'.format(
                self.err_resp['status'].capitalize(),
                self.err_resp['error_code'],
                self.err_resp['description']
            )
        except KeyError:
            try:
                # Alternative format with status and description
                return '{:<7}: {}'.format(
                    self.err_resp['status'].capitalize(),
                    self.err_resp['description']
                )
            except KeyError:
                # Simple message format (e.g., {"message": "Unauthorized"})
                if 'message' in self.err_resp:
                    return 'Error: {}'.format(self.err_resp['message'])
                # Fallback to raw response
                return 'HTTP Error: {}'.format(str(self.err_resp))
