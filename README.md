---
id: cli-usage
title: RainMaker CLI Usage
sidebar_label: CLI Usage
---

## Setup

If you haven't setup the CLI, follow the steps [here](cli-setup.md) before moving ahead with the usage.

## Commands and Usage:

> **Note : On Windows, use `python rainmaker.py <sub-command>`**
1. First User has to sign up using the following command : 

        ./rainmaker.py signup <email>
 
2. After Signup, User has to do the login for the CLI using the following command :

        ./rainmaker.py login --email <email>
    
For browser login User can use the command :
   
        ./rainmaker.py login

3. After successful login user can use the Rainmaker CLI.

### Running the utility
 
 **Usage**

        ./rainmaker.py [OPTIONS] COMMAND [ARGS]...

Options :

| **No.** | **Parameter** | **Description** |
| --- | --- | --- |
| 1   | -h, --help |  show this help message and exit  |  

 **Commands :**
  	
      Run `./rainmaker.py {command} -h` for additional help 

| **No.** | **Parameter** | **Description** |
| --- | --- | --- |
| 1   | signup         | Sign up for ESP Rainmaker  |
| 2   | login          | Login to ESP Rainmaker  |
| 3   | forgotpassword | Reset the password |
| 4   | getnodes       | List all nodes associated with the user  |
| 5   | getnodeconfig  | Get node configuration  |
| 6   | setparams      | Set node parameters. Note: Enter JSON data in singe quotes  |
| 7   | getparams      | Get node parameters  |
| 8   | removenode     | Remove user node mapping |
| 9   | provision      | Provision the node to join Wi-Fi network  |
| 10  | claim          | Claim the ESP32-S2 (Get Cloud credentials)  |
| 11  | getmqtthost    | Get the MQTT Host URL to be used in the firmware |

> **Note : For `./rainmaker.py setparams <nodeid> --data <JSON_data>` command, the input JSON_data format is different on Windows and MacOS/Linux. For Windows JSON_data should be like `'{\"Light": {\"brightness\": 50, \"output\": false}}'` and on MacOS/Linux data should be like `'{"Light": {"brightness": 50, "output": false}}'`**
