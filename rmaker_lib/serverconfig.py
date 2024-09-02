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