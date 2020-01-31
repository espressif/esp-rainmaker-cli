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
HOST = 'https://r8ofygb120.execute-api.us-east-1.amazonaws.com/prod/' + VERSION + '/'
CLIENT_ID = '2fmtjlo5cve01ukiisu1b6poft'
CLIENT_SECRET = '181iq8dumcj3kca5k2757j1kn2mbm02k2vge3oa20pkoeai0hpop'
LOGIN_URL = 'https://rainmaker-login.s3.amazonaws.com/index.html?port='
TOKEN_URL = 'https://rainmaker-staging.auth.us-east-1.amazoncognito.com/oauth2/token'
REDIRECT_URL = 'https://rainmaker-login.s3.amazonaws.com/welcome.html'
GITHUB_URL = 'https://rainmaker-prod.auth.us-east-1.amazoncognito.com/oauth2/authorize?identity_provider=Github&redirect_uri=' + REDIRECT_URL + '&response_type=CODE&client_id=' + CLIENT_ID + '&scope=aws.cognito.signin.user.admin%20email%20openid%20phone%20profile&state=port:'
