# SPDX-FileCopyrightText: 2020-2025 Espressif Systems (Shanghai) CO LTD
#
# SPDX-License-Identifier: Apache-2.0

from rmaker_lib import configmanager, session
from rmaker_lib.logger import log


def get_session_with_profile(vars_dict):
    """
    Get a session object, optionally using a different profile.
    
    :param vars_dict: Dictionary containing parsed command arguments
    :type vars_dict: dict
    
    :return: Session object configured for the specified or current profile
    :rtype: session.Session
    """
    profile_override = vars_dict.get('profile')
    
    if profile_override:
        log.info(f"Using profile override: {profile_override}")
        # Validate that the profile exists before creating session
        config = configmanager.Config()
        if not config.profile_manager.profile_exists(profile_override):
            print(f"❌ Profile '{profile_override}' does not exist.")
            print("Use 'esp-rainmaker-cli profile list' to see available profiles.")
            raise ValueError(f"Profile '{profile_override}' does not exist")
        
        # Show which profile is being used
        print(f"Using profile: \033[1m\033[32m{profile_override}\033[0m\033[0m")
        
        return session.Session(profile_override=profile_override)
    else:
        return session.Session()


def get_config_with_profile(vars_dict):
    """
    Get a config object, optionally using a different profile.
    
    :param vars_dict: Dictionary containing parsed command arguments
    :type vars_dict: dict
    
    :return: Config object configured for the specified or current profile
    :rtype: configmanager.Config
    """
    profile_override = vars_dict.get('profile')
    
    if profile_override:
        log.info(f"Using profile override: {profile_override}")
        # Validate that the profile exists
        config = configmanager.Config()
        if not config.profile_manager.profile_exists(profile_override):
            print(f"❌ Profile '{profile_override}' does not exist.")
            print("Use 'esp-rainmaker-cli profile list' to see available profiles.")
            raise ValueError(f"Profile '{profile_override}' does not exist")
        
        # Show which profile is being used
        print(f"Using profile: \033[1m\033[32m{profile_override}\033[0m\033[0m")
        
        return configmanager.Config(profile_override=profile_override)
    else:
        return configmanager.Config() 