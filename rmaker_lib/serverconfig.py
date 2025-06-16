# SPDX-FileCopyrightText: 2020-2025 Espressif Systems (Shanghai) CO LTD
#
# SPDX-License-Identifier: Apache-2.0

VERSION = 'v1'

# For Rest of the World

LOGIN_URL = 'https://rainmaker-signin-ui.s3.amazonaws.com/index.html?port='

HOST = 'https://api.rainmaker.espressif.com/' + VERSION + '/'

CLIENT_ID = '1h7ujqjs8140n17v0ahb4n51m2'

TOKEN_URL = ('https://3pauth.rainmaker.espressif.com/'
             'oauth2/token')

REDIRECT_URL = 'https://rainmaker-login-ui.s3.amazonaws.com/welcome.html'

EXTERNAL_LOGIN_URL = (
                     'https://3pauth.rainmaker.espressif.com/' 
                     'oauth2/authorize?&redirect_uri=' +
                     REDIRECT_URL + '&response_type=CODE&client_id=' +
                     CLIENT_ID + '&scope=aws.cognito.signin.user.'
                     'admin%20email%20openid%20phone%20profile&state=port:'
                     )

# For China

LOGIN_URL_CN = 'http://login.rainmaker.espressif.com.cn?rm_cli=true&port='

HOST_CN = 'https://api2.rainmaker.espressif.com.cn/' + VERSION + '/'

CLIENT_ID_CN = '6m3FgmvJSt4g6pDrHgfpYj'

TOKEN_URL_CN = ('https://api2.rainmaker.espressif.com.cn/token')

REDIRECT_URL_CN = 'http://login.rainmaker.espressif.com.cn/welcome.html'

EXTERNAL_LOGIN_URL_CN = (
                     'https://api2.rainmaker.espressif.com.cn/authorize?&client_id=' 
                     + CLIENT_ID_CN + '&response_type=code&redirect_uri='  
                     + REDIRECT_URL_CN + '&state=port:'
                     )

CLAIMING_BASE_URL_CN = 'https://claiming.rainmaker.espressif.com.cn/'