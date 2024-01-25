import os
from rmaker_lib.constants import DEFAULT_RM_USER_CONFIG_DIR, RM_USER_CONFIG_DIR


def get_rm_user_config_dir():
    config_dir = os.getenv(RM_USER_CONFIG_DIR, DEFAULT_RM_USER_CONFIG_DIR)
    config_dir = os.path.expanduser(config_dir)
    return config_dir