# Espressif Rainmaker CLI Tool
A command line utility for the ESP-Rainmaker Project

### Prerequisites

**Package requirements and installation steps [MacOs]:**

1. Download the Python Package from the URL : https://www.python.org/downloads/release/python-374/

2. Select the Package : https://www.python.org/ftp/python/3.7.4/python-3.7.4-macosx10.9.pkg

3. After the download is complete, run the installer and click through the setup steps leaving all the pre-selected installation defaults.

4. Once complete, make sure that Python3 is installed correctly by running following command on Terminal.

        python3 --version

5. Install all python dependencies using

        pip3 install -r requirements.txt

6. Install get-pip using command

        curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py

        python3 get-pip.py


**Note: Using this utility requires ESP IDF to be set up on your host machine. If it is not already done, please refer the [Getting Started](getting-started.md) document first.**


### Setup Path to rainmaker_cli_without_shell[MacOs]:
1. Open the .bash_profile or .profile file in a editor.

2. Add export PATH="your-dir:$PATH" to the last line of the file, where your-dir is the rainmaker_cli_without_shell.

3. Save the .bash_profile or .profile file.

4. Restart your terminal.

### Commands and Usage:

1. First User has to sign up using the following command : 

        rainmaker signup <Email>
 
2. After Signup, User has to do the login for the CLI using the following command :

        rainmaker login --email <Email>
    
For github login User can use the command :
   
        rainmaker login

3. After successful login user can use the Rainmaker CLI.

### Running the utility
 
 **Usage**

        rainmaker [-h] [--verbose] {signup,login,getnodeconfig,getnodes,setparams,getparams,provision,claim} ...

Optional Arguments:

| **No.** | **Parameter** | **Description** |
| --- | --- | --- |
| 1   | -h, --help |  show this help message and exit  |  

 **Commands:**
  	
      Run `rainmaker {command} -h` for additional help 

| **No.** | **Parameter** | **Description** |
| --- | --- | --- |
| 1   | signup |  User signup to the ESP Rainmaker CLI  |
| 2   | login |   User login to the ESP Rainmaker CLI  |
| 3   | getnodes |  List all nodes associated with the user  |
| 4   | getnodeconfig |  Shows the configuration of the node  |
| 5   | setparams |  Sets the desired state of the node  |
| 6   | getparams |  Shows the reported state of the node  |
| 7   | provision |  Does the provisioning of the node  |
| 8   | claim |  Claim your node with ESP claim  |


**To signup ESP-Rainmaker CLI:**
 
**Usage**

        rainmaker signup [-h] Email
        
Positional Arguments:

| **No.** | **Parameter** | **Description** |
| --- | --- | --- |
| 1   | Email |  Email address of the user  | 

Optional Arguments:

| **No.** | **Parameter** | **Description** |
| --- | --- | --- |
| 1   | -h, --help |  show this help message and exit  |  


**To login ESP-Rainmaker CLI:**
   
 **Usage**

        rainmaker login [-h] [--email EMAIL]

Optional Arguments:

| **No.** | **Parameter** | **Description** |
| --- | --- | --- |
| 1   | -h, --help |  show this help message and exit  |
| 2   | --email |  Email address of the user  |

**To get nodes for user:**
 
  **Usage**

        rainmaker getnodes [-h]

Optional Arguments:

| **No.** | **Parameter** | **Description** |
| --- | --- | --- |
| 1   | -h, --help |  show this help message and exit  |  


**To get the node info:**
   
 **Usage**

        rainmaker getnodeconfig [-h] nodeId
        
Positional Arguments:

| **No.** | **Parameter** | **Description** |
| --- | --- | --- |
| 1   | nodeId |  Node Id for the node  |



Optional Arguments:

| **No.** | **Parameter** | **Description** |
| --- | --- | --- |
| 1   | -h, --help |  show this help message and exit  | 

**To set the desired state of the node:**

 **Usage**

        rainmaker setparams [-h] [--filePath FILEPATH] [--data DATA] nodeid
        
Positional Arguments:

| **No.** | **Parameter** | **Description** |
| --- | --- | --- |
| 1   | nodeId |  Node Id for the node  |


Optional Arguments:

| **No.** | **Parameter** | **Description** |
| --- | --- | --- |
| 1   | -h, --help  |  show this help message and exit  |
| 2   | --filepath |  Path of the json file conatining parameters to be set  |
| 3   | --data |  Json data containing parameters to be set. Note: Enter the data in single inverted quotes |

    Note : Example data can be like '{ "Light.brightness": 15, "Light.color": "white", "Light.output": true }'



**To get the cerrent state of the node:**
  
  **Usage**

        rainmaker getparams [-h] nodeId
        
Positional Arguments:

| **No.** | **Parameter** | **Description** |
| --- | --- | --- |
| 1   | nodeId |  Node Id for the node  |


Optional Arguments:

| **No.** | **Parameter** | **Description** |
| --- | --- | --- |
| 1   | -h, --help  |  show this help message and exit  |

**To do the provision of the node:**
   
 **Usage**

        rainmaker provision [-h] [--ssid SSID] pop
        
Positional Arguments:

| **No.** | **Parameter** | **Description** |
| --- | --- | --- |
| 1   | pop |  Proof of possesion for the node  |



Optional Arguments:

| **No.** | **Parameter** | **Description** |
| --- | --- | --- |
| 1   | -h, --help  |  show this help message and exit  |
| 2   | --ssid   |  SSID of the network   |



For claiming the node:
   
 **Usage**

        rainmaker claim [-h] [--port PORT] [--certAddr CERTADDR]

Optional Arguments:

| **No.** | **Parameter** | **Description** |
| --- | --- | --- |
| 1   | -h, --help  |  show this help message and exit  |
| 2   | --port   |  Serial Port connected to the device   |
| 3   | --certAddr   |  Starting address of the certificates in flash   |
