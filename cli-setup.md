---
id: cli-setup
title: RainMaker CLI Setup
sidebar_label: CLI Setup
---

Setting up ESP RainMaker Command Line utility

## Installing Python3

If you have python3 already installed, just move on to the next section. Else, follow these steps:

1. Download python 3 for your OS from the [python website](https://www.python.org/downloads/). Latest version should be fine, but the CLI is tested with python 3.7.4.
2. Run the OS specific installer to install python3.
3. Verify the installation by running following command on terminal.

```
$ python3 --version
```

## Installing dependencies

We will have to first install pip, which is a package installer for python and then install the dependencies. Here are the steps:

**Installing pip**

```
$ curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py
$ python3 get-pip.py
```

**Getting ESP RainMaker CLI**
Download the ESP RainMaker CLI using the following

```
$ git clone -b release/alpha https://gitlab.espressif.cn:6688/esp_rainmaker/esp-rainmaker-cli.git
```

**Installing dependencies**

```
$ cd /path/to/esp-rainmaker-cli/
$ pip3 install -r requirements.txt
```

> **Note: Using this utility requires ESP IDF to be set up on your host machine. If it is not already done, please refer the [ESP IDF Get Started guide](https://docs.espressif.com/projects/esp-idf/en/latest/get-started/index.html) and ensure that the IDF\_PATH is set correctly**


## Adding the CLI to your PATH (Optional)

The RainMaker CLI can be used from the esp-rainmaker-cli folder directly as below:

```
$ ./rainmaker <cmd>
```

However, if you want to allow using it from any path, add it to your PATH variable. For MacOS, the steps are as below

1. Open the ~/.bash_profile or ~/.profile file in an editor.
2. Add `export PATH=$PATH:/path/to/esp-rainmaker-cli/` line at the end
3. Save the .bash_profile or .profile file.
4. Restart your terminal, or just execute `$ source ~/.bash_profile` or `$ source ~/.profile` as applicable.
