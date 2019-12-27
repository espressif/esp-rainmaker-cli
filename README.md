---
id: cli-usage
title: RainMaker CLI Usage
sidebar_label: CLI Usage
---

## Setup

If you haven't setup the CLI, follow the steps [here](cli-setup.md) before moving ahead with the usage.

## Commands and Usage:

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
| 2   | --filepath |  Path of the json file containing parameters to be set  |
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
| 1   | pop |  Proof of possession for the node  |



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
