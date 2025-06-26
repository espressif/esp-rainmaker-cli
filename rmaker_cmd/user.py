# SPDX-FileCopyrightText: 2020-2025 Espressif Systems (Shanghai) CO LTD
#
# SPDX-License-Identifier: Apache-2.0

import sys
import re
import getpass
import time
import json
import os
from pathlib import Path

try:
    from rmaker_lib import user, configmanager, session, serverconfig
    from rmaker_lib.logger import log
    from rmaker_lib.exceptions import SSLError, \
        NetworkError, \
        RequestTimeoutError, \
        InvalidConfigError, \
        InvalidJSONError, \
        HttpErrorResponse, \
        ExpiredSessionError, \
        AuthenticationError
except ImportError as err:
    print("Failed to import ESP Rainmaker library. " + str(err))
    raise err

from rmaker_lib.profile_utils import get_session_with_profile, get_config_with_profile

MAX_PASSWORD_CHANGE_ATTEMPTS = 3


def signup(vars=None):
    """
    User signup to the ESP Rainmaker.

    :param vars: `user_name` as key - Email address/Phone number of the user
                 `profile` as key - Profile to use for signup (optional)
    :type vars: dict

    :raises Exception: If there is any issue in signup for user

    :return: None on Success
    :rtype: None
    """

    config = get_config_with_profile(vars or {})
    current_profile = config.get_current_profile_name()

    print('Current selected profile is \033[1m\033[32m{}\033[0m\033[0m. If you wish to change this, use `profile switch` command.'.format(current_profile))
    time.sleep(3)

    log.info('Signing up the user ' + vars['user_name'])
    u = user.User(vars['user_name'], config)
    password = get_password()
    try:
        status = u.signup_request(password)
    except Exception as signup_err:
        log.error(signup_err)
    else:
        if status is True:
            verification_code = input('Enter verification code sent on your '
                                      'Email/Phone number.\n Verification Code : ')
            try:
                status = u.signup(verification_code)
            except Exception as signup_err:
                log.error(signup_err)
                return
            print('Signup Successful\n'
                  'Please login to continue with ESP Rainmaker CLI')
        else:
            log.error('Signup failed. Please try again.')
    return


def login(vars=None):
    """
    First time login of the user.

    :param vars: `email` as key - Email address of the user
                 `user_name` as key - Email address or phone number of the user
                 `password` as key - Password (for CI integration)
                 `profile` as key - Profile to login to (optional)
    :type vars: dict

    :raises Exception: If there is any issue in login for user

    :return: None on Success and Failure
    :rtype: None
    """
    # Determine which profile to use
    profile_to_use = vars.get('profile') if vars else None

    if profile_to_use:
        # If a specific profile is requested, validate it exists
        try:
            config = configmanager.Config()
            if not config.profile_manager.profile_exists(profile_to_use):
                print(f"❌ Profile '{profile_to_use}' does not exist.")
                print("Use 'esp-rainmaker-cli profile list' to see available profiles.")
                return

            # Show which profile we're logging into
            print(f'Logging into profile: \033[1m\033[32m{profile_to_use}\033[0m\033[0m')

            # Create a config with profile override for login
            config = configmanager.Config(profile_override=profile_to_use)
        except Exception as e:
            log.error(f"Error accessing profile '{profile_to_use}': {e}")
            return
    else:
        # Use current profile
        config = configmanager.Config()
        current_profile = config.get_current_profile_name()
        print('Current selected profile is \033[1m\033[32m{}\033[0m\033[0m. If you wish to change this, use `profile switch` command.'.format(current_profile))

    time.sleep(3)

    # Get the profile we're working with
    target_profile = profile_to_use if profile_to_use else config.get_current_profile_name()

    # Check if this is a custom profile
    try:
        profile_config = config.profile_manager.get_profile_config(target_profile)
        is_custom_profile = not profile_config.get('builtin', False)

        if is_custom_profile and not profile_config.get('ui_login_supported', False):
            # Custom profiles require --user_name and don't support UI login
            if not vars.get('user_name') and not vars.get('email'):
                log.error('Custom profiles require --user_name for login. UI-based login is not supported for custom profiles.')
                print('Please use: rainmaker login --user_name <your_email>')
                return
    except Exception as e:
        log.debug(f"Failed to get profile config: {e}")

    # Set email-id
    user_name = vars.get('user_name') if vars else None
    if not user_name:
        user_name = vars.get('email') if vars else None
    log.info('Logging in user: {}'.format(user_name))

    # Check user current creds exist
    resp_filename = config.check_user_creds_exists()
    if resp_filename:
        try:
            user_name_config = config.get_user_name()
            log.info(f'User already logged in for profile {target_profile}: {user_name_config}')
        except Exception:
            log.info(f'Session found for profile {target_profile}')

        log.debug("User login status is active.")

                # Print user details
        try:
            user_name_config = config.get_user_name()
            print(f'\nUser login session found for profile {target_profile}.')
            print(f'Currently logged in as: {user_name_config}')
        except Exception:
            print(f'\nUser login session found for profile {target_profile}.')

        user_input = input(
            f"Do you want to end the session and login again with a different user (Y/N)? :")

        if user_input not in ["Y", "y"]:
            try:
                user_name_config = config.get_user_name()
                print(f"User '{user_name_config}' in profile '{target_profile}' is already logged in.")
            except Exception:
                print(f"Session exists for profile '{target_profile}'.")
            return

        config.remove_curr_login_creds()
        print("Previous login session ended successfully.")

    # Check if we have a password provided
    password = vars.get('password') if vars else None

    if user_name and password:
        # Programmatic login with credentials
        try:
            user_obj = user.User(user_name, config)
            session_obj = user_obj.login(password)
            print("Login successful!")
            return
        except AuthenticationError:
            print("Authentication Failed. Incorrect username or password.")
            return
        except Exception as e:
            log.error(f"Login failed: {e}")
            return

    if user_name:
        # Interactive login with username
        print(f"Performing interactive login for user: {user_name}")
        print("Password can also be set in environment variable: $ESP_RAINMAKER_PASSWORD")

        password = os.getenv('ESP_RAINMAKER_PASSWORD')
        if not password:
            password = getpass.getpass("Please enter the password: ")

        if not password:
            print("Password is required for login.")
            return

        try:
            user_obj = user.User(user_name, config)
            session_obj = user_obj.login(password)
            print("Login successful!")
            return
        except AuthenticationError:
            print("Authentication Failed. Incorrect username or password.")
            return
        except Exception as e:
            log.error(f"Login failed: {e}")
            return
    else:
        # Browser-based login
        log.info("Starting browser login flow")
        print('Secure browser login')
        from rmaker_cmd.browserlogin import browser_login
        browser_login(config)


def logout(vars=None):
    """
    Logout current (logged-in) user

    :param vars: Optional parameters including 'profile'
    :type vars: dict | None

    :return: None on Success and Failure
    :rtype: None
    """
    try:
        log.debug('Logging out current logged-in user')
        curr_session = get_session_with_profile(vars or {})
        response = curr_session.logout()
        log.debug('Logout response: %s' % response)

        # Remove current login creds for the profile being used
        config = get_config_with_profile(vars or {})
        config.remove_curr_login_creds()
        print('Logout successful.')
        return
    except Exception as logout_err:
        if str(logout_err) == 'Unauthorized':
            print('User already logged out')
        else:
            log.error(logout_err)
    return


def forgot_password(vars=None):
    """
    Forgot password request to reset the password.

    :param vars: `user_name` as key - Email address/ phone number of the user
                 `profile` as key - Profile to use for password reset (optional)
    :type vars: dict

    :raises Exception: If there is an HTTP issue while
                       changing password for user

    :return: None on Success and Failure
    :rtype: None
    """
    log.info('Changing user password. Username ' + vars['user_name'])
    config = get_config_with_profile(vars or {})

    # Get email-id if present
    try:
        user_name = config.get_user_name()
    except Exception:
        user_name = None

    # If current logged-in user is same as
    # the email-id given as user input
    # end current session
    # (invalidate current logged-in user token)
    log.debug("Current user email-id: {}, user input email-id: {}".format(user_name, vars['user_name']))
    if user_name and user_name == vars['user_name']:
        log.debug("Ending current session for user: {}".format(user_name))

        # Check user current creds exist
        resp_filename = config.check_user_creds_exists()
        if not resp_filename:
            log.debug("Current login creds not found at path: {}".format(resp_filename))
            log.error("User not logged in")
            return

        # If current creds exist, ask user for ending current session
        # Get user input
        input_resp = config.get_input_to_end_session(user_name)
        if not input_resp:
            return

        # Remove current login creds
        ret_val = config.remove_curr_login_creds(curr_creds_file=resp_filename)
        if ret_val is None:
            print("Failed to end previous login session. Exiting.")
            return

    u = user.User(vars['user_name'], config)
    status = False

    try:
        status = u.forgot_password()
    except Exception as forgot_pwd_err:
        log.error(forgot_pwd_err)
    else:
        verification_code = input('Enter verification code sent on your Email/Phone number.'
                                  '\n Verification Code : ')
        password = get_password()
        if status is True:
            try:
                log.debug('Received verification code on email/phone number ' +
                          vars['user_name'])
                status = u.forgot_password(password, verification_code)
            except Exception as forgot_pwd_err:
                log.error(forgot_pwd_err)
            else:
                print('Password changed successfully.'
                      'Please login with the new password.')
        else:
            log.error('Failed to reset password. Please try again.')
    return


def get_password():
    """
    Get Password as input and perform basic password validation checks.

    :raises SystemExit: If there is an issue in getting password

    :return: Password for User on Success
    :rtype: str
    """
    log.info('Doing basic password confirmation checks.')
    password_policy = '8 characters, 1 digit, 1 uppercase and 1 lowercase.'
    password_change_attempt = 0

    print('Choose a password')
    while password_change_attempt < MAX_PASSWORD_CHANGE_ATTEMPTS:
        log.debug('Password change attempt number ' +
                  str(password_change_attempt+1))
        password = getpass.getpass('Password : ')
        if len(password) < 8 or re.search(r"\d", password) is None or\
           re.search(r"[A-Z]", password) is None or\
           re.search(r"[a-z]", password) is None:
            print('Password should contain at least', password_policy)
            password_change_attempt += 1
            continue
        confirm_password = getpass.getpass('Confirm Password : ')
        if password == confirm_password:
            return password
        else:
            print('Passwords do not match!\n'
                  'Please enter the password again ..')
        password_change_attempt += 1

    log.error('Maximum attempts to change password over. Please try again.')
    sys.exit(1)


def get_user_details(vars=None):
    """
    Get details of current logged-in user

    :param vars: Optional parameters including 'profile'
    :type vars: dict | None
    """
    try:
        # Get user details
        log.debug('Getting details of current logged-in user')
        curr_session = get_session_with_profile(vars or {})
        user_info = curr_session.get_user_details()
        log.debug("User details received")
    except Exception as err:
        log.error(err)
    else:
        # Print API response output
        for key, val in user_info.items():
            if key == "user_name":
                key = key + " (email)"
            title = key.replace("_", " ").title()
            print("{}: {}".format(title, val))
    return

def set_configuration(vars=None):
    """
    Set Configuration - now only handles legacy region setting

    :param vars: Configuration parameters
    :type vars: dict

    :return: None on Success
    """
    if vars.get('region'):
        # Legacy region setting
        if vars['region'] == 'china':
            set_china_region(vars)
        elif vars['region'] == 'global':
            set_global_region(vars)
        else:
            log.error('Invalid Region. Valid regions: china, global. Exiting.')
            sys.exit(1)
    elif vars.get('profile'):
        # Profile switching
        switch_profile(vars)
    elif vars.get('add_profile'):
        # Add custom profile
        add_custom_profile(vars)
    elif vars.get('remove_profile'):
        # Remove custom profile
        remove_custom_profile(vars)
    elif vars.get('list_profiles'):
        # List all profiles
        list_profiles(vars)
    elif vars.get('show_current'):
        # Show current profile
        show_current_profile(vars)
    else:
        log.error('No configuration option specified. Use --help for available options.')
        sys.exit(1)
    return

def set_china_region(vars=None):
    """
    Set China Region - maps to china profile
    """
    config = configmanager.Config()

    try:
        # Switch to china profile
        config.switch_profile('china')
        print("Switched to profile 'china' (region: china)")
    except Exception as e:
        log.error(f"Failed to switch to china region: {e}")
        sys.exit(1)
    return

def set_global_region(vars=None):
    """
    Set Global Region - maps to global profile
    """
    config = configmanager.Config()

    try:
        # Switch to global profile
        config.switch_profile('global')
        print("Switched to profile 'global' (region: global)")
    except Exception as e:
        log.error(f"Failed to switch to global region: {e}")
        sys.exit(1)
    return

def switch_profile(vars=None):
    """
    Switch to a different profile
    """
    profile_name = vars['profile']
    config = configmanager.Config()

    try:
        if not config.profile_manager.profile_exists(profile_name):
            print(f"Profile '{profile_name}' does not exist.")
            print("Use 'profile list' to see available profiles.")
            return

        config.switch_profile(profile_name)
        print(f"Switched to profile '{profile_name}'")

    except Exception as e:
        log.error(f"Failed to switch profile: {e}")

def add_custom_profile(vars=None):
    """
    Add a new custom profile
    """
    profile_name = vars['add_profile']
    base_url = vars.get('base_url')
    description = vars.get('description')

    if not base_url:
        log.error('Base URL is required for custom profiles. Use --base-url option.')
        sys.exit(1)

    config = configmanager.Config()

    try:
        config.profile_manager.create_custom_profile(profile_name, base_url, description)
        print(f"Created custom profile '{profile_name}' with base URL '{base_url}'")
        print(f"Note: Custom profiles require --user_name for login (UI login not supported)")

    except ValueError as e:
        log.error(f"Failed to create profile: {e}")
        sys.exit(1)
    except Exception as e:
        log.error(f"Failed to create profile: {e}")
        sys.exit(1)

def remove_custom_profile(vars=None):
    """
    Remove a custom profile
    """
    profile_name = vars['remove_profile']
    config = configmanager.Config()

    try:
        # Confirm before deletion
        confirmation = input(f"Are you sure you want to delete profile '{profile_name}'? (y/N): ")
        if confirmation.lower() not in ['y', 'yes']:
            print("Profile deletion cancelled.")
            return

        config.profile_manager.delete_custom_profile(profile_name)
        print(f"Deleted custom profile '{profile_name}'")

    except ValueError as e:
        log.error(f"Failed to delete profile: {e}")
    except Exception as e:
        log.error(f"Failed to delete profile: {e}")

def list_profiles(vars=None):
    """
    List all available profiles
    """
    config = configmanager.Config()
    current_profile = config.get_current_profile_name()

    try:
        profiles = config.profile_manager.list_profiles()

        print("Available profiles:")
        print("-" * 50)

        for profile_name, profile_config in profiles.items():
            is_current = " (current)" if profile_name == current_profile else ""
            profile_type = "builtin" if profile_config.get('builtin', False) else "custom"

            print(f"  {profile_name}{is_current}")
            print(f"    Type: {profile_type}")
            print(f"    Description: {profile_config.get('description', 'N/A')}")

            if profile_config.get('host'):
                print(f"    Host: {profile_config['host']}")

            # Check if user is logged in to this profile
            if config.profile_manager.has_profile_tokens(profile_name):
                print(f"    Status: Logged in")
            else:
                print(f"    Status: Not logged in")

            print()

    except Exception as e:
        log.error(f"Failed to list profiles: {e}")

def show_current_profile(vars=None):
    """
    Show current profile information
    """
    config = configmanager.Config()
    current_profile = config.get_current_profile_name()

    try:
        profile_config = config.profile_manager.get_profile_config(current_profile)
        is_builtin = profile_config.get('builtin', False)

        print(f"Current profile: {current_profile}")
        print(f"Type: {'builtin' if is_builtin else 'custom'}")
        print(f"Description: {profile_config.get('description', 'N/A')}")
        print(f"Host: {config.get_host()}")

        # Check login status
        if config.profile_manager.has_profile_tokens(current_profile):
            try:
                user_name = config.get_user_name()
                print(f"Login status: Logged in as {user_name}")
            except:
                print(f"Login status: Logged in")
        else:
            print(f"Login status: Not logged in")

    except Exception as e:
        log.error(f"Failed to get profile information: {e}")

# New clean profile command functions

def profile_list(vars=None):
    """List all available profiles"""
    return list_profiles(vars)

def profile_current(vars=None):
    """Show current profile information"""
    return show_current_profile(vars)

def profile_switch(vars=None):
    """Switch to a different profile"""
    # Convert new argument structure to old format
    if 'profile_name' in vars:
        vars['profile'] = vars['profile_name']
    return switch_profile(vars)

def profile_add(vars=None):
    """Add a new custom profile"""
    # Convert new argument structure to old format
    if 'profile_name' in vars:
        vars['add_profile'] = vars['profile_name']
    return add_custom_profile(vars)

def profile_remove(vars=None):
    """Remove a custom profile"""
    # Convert new argument structure to old format
    if 'profile_name' in vars:
        vars['remove_profile'] = vars['profile_name']
    return remove_custom_profile(vars)

# Region configuration function
def set_region_configuration(vars=None):
    """
    Set Region Configuration

    :param vars: Configuration parameters
    :type vars: dict

    :return: None on Success
    """
    if vars.get('region'):
        # Region setting
        if vars['region'] == 'china':
            set_china_region(vars)
        elif vars['region'] == 'global':
            set_global_region(vars)
        else:
            log.error('Invalid Region. Valid regions: china, global. Exiting.')
            sys.exit(1)
    else:
        log.error('No region specified. Valid regions: china, global.')
        sys.exit(1)
    return

def delete_user(vars=None):
    """
    Delete current user account from ESP RainMaker.
    This is a two-step process with confirmation at each step.

    :param vars: Optional parameters including 'profile'
    :type vars: dict | None

    :return: None on Success and Failure
    :rtype: None
    """
    try:
        log.debug('Initiating user deletion process')

        # Get current session and user info
        curr_session = get_session_with_profile(vars or {})
        config = get_config_with_profile(vars or {})

        # Get current user name if possible
        try:
            current_user = config.get_user_name()
        except Exception:
            current_user = "current user"

        # Step 1: Show warning and get initial confirmation
        print("\n" + "="*60)
        print("⚠️  WARNING: USER ACCOUNT DELETION")
        print("="*60)
        print("This action will PERMANENTLY DELETE your ESP RainMaker account.")
        print("The following data will be PERMANENTLY REMOVED:")
        print("  • All your nodes and devices")
        print("  • All device groups")
        print("  • All schedules and automations")
        print("  • All sharing settings")
        print("  • All user data and preferences")
        print("  • Your account login credentials")
        print("\n⚠️  THIS ACTION CANNOT BE UNDONE!")
        print("="*60)

        confirmation = input(f"\nAre you absolutely sure you want to delete {current_user} (Y/N)? :")
        if confirmation.lower() not in ['y', 'yes']:
            print("User deletion cancelled.")
            return

        # Step 2: Initiate deletion request
        print("\nInitiating account deletion request...")

        try:
            # First API call - request deletion
            curr_session.delete_user(request=True)
            print(f"✅ Deletion request sent successfully!")
            print(f"📧 A verification code has been sent to your email: {current_user}")

        except Exception as delete_err:
            log.error(f"Failed to initiate user deletion: {delete_err}")
            return

        # Step 3: Get verification code
        print("\n" + "-"*50)
        verification_code = input("Please enter the verification code from your email: ")

        if not verification_code.strip():
            print("No verification code provided. User deletion cancelled.")
            return

        # Step 4: Final confirmation
        print("\n" + "="*60)
        print("🔴 FINAL CONFIRMATION")
        print("="*60)
        print("You are about to PERMANENTLY DELETE your account!")
        print("This will remove ALL data associated with your account.")
        print("="*60)

        final_confirmation = input("Type 'DELETE' to confirm permanent account deletion: ")
        if final_confirmation != 'DELETE':
            print("Final confirmation failed. User deletion cancelled.")
            return

        # Step 5: Execute deletion with verification code
        print("\nExecuting account deletion...")
        try:
            curr_session.delete_user(verification_code=verification_code.strip())

            # Remove local credentials
            config.remove_curr_login_creds()

            print("✅ User account deleted successfully.")
            print("Your ESP RainMaker account and all associated data have been permanently removed.")
            print("Thank you for using ESP RainMaker.")

        except Exception as delete_err:
            log.error(f"Failed to delete user account: {delete_err}")
            print("❌ Failed to delete user account. Please try again or contact support.")
            return

    except Exception as err:
        log.error(f"Error during user deletion process: {err}")
        print("❌ An error occurred during the deletion process.")
        return