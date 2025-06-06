# Profile Management

## Overview

The ESP RainMaker CLI supports multiple profiles, allowing you to manage different login sessions and regions simultaneously. Each profile maintains its own login tokens and configuration, enabling seamless switching between different ESP RainMaker deployments.

## Built-in Profiles

- **global**: Global ESP RainMaker (Rest of World) - default profile
- **china**: China ESP RainMaker region

## Profile Commands

### List All Profiles

```bash
esp-rainmaker-cli profile list
```

**Output:**
```
Available profiles:
--------------------------------------------------
  global (current)
    Type: builtin
    Description: Global ESP RainMaker (Rest of World)
    Host: https://api.rainmaker.espressif.com/v1/
    Status: Logged in

  china
    Type: builtin
    Description: China ESP RainMaker
    Host: https://api2.rainmaker.espressif.com.cn/v1/
    Status: Not logged in

  my-company
    Type: custom
    Description: Company Internal Deployment
    Host: https://rainmaker.company.com/api/v1/
    Status: Logged in
```

### Show Current Profile

```bash
esp-rainmaker-cli profile current
```

**Output:**
```
Current profile: global
Type: builtin
Description: Global ESP RainMaker (Rest of World)
Host: https://api.rainmaker.espressif.com/v1/
Login status: Logged in as user@example.com
```

### Switch Profiles

```bash
# Switch to China region
esp-rainmaker-cli profile switch china

# Switch to custom deployment
esp-rainmaker-cli profile switch my-company

# Switch back to global
esp-rainmaker-cli profile switch global
```

### Add Custom Profile

```bash
# Basic custom profile
esp-rainmaker-cli profile add company-staging \
  --base-url https://staging.rainmaker.company.com/api/

# With description
esp-rainmaker-cli profile add company-prod \
  --base-url https://rainmaker.company.com/api/ \
  --description "Company Production Environment"
```

**Requirements for custom profiles:**
- Must provide `--base-url` parameter
- Base URL should point to your ESP RainMaker API endpoint
- Profile names must be alphanumeric with optional `_`, `-`, `.`, `#` characters

### Remove Custom Profile

```bash
esp-rainmaker-cli profile remove company-staging
```

**Note:** Built-in profiles (`global` and `china`) cannot be removed.

## Profile-Aware Operations

Once you switch to a profile, all subsequent CLI operations use that profile's configuration and authentication:

```bash
# Switch to company deployment
esp-rainmaker-cli profile switch company-prod

# All these commands now operate on company deployment
esp-rainmaker-cli getnodes
esp-rainmaker-cli getparams <node_id>
esp-rainmaker-cli setparams <node_id> --data '{"Switch": {"Power": true}}'
```

## Login Requirements

### Built-in Profiles (Global/China)
Support both UI-based and credential-based login:

```bash
# UI-based login (opens browser)
esp-rainmaker-cli login

# Credential-based login
esp-rainmaker-cli login --user_name your_email@example.com
```

### Custom Profiles
Require credential-based login (UI login not supported):

```bash
# Switch to custom profile
esp-rainmaker-cli profile switch my-company

# Must use --user_name for login
esp-rainmaker-cli login --user_name your_email@company.com
```

## Legacy Compatibility

For backward compatibility, the following commands still work:

```bash
# Legacy region switching
esp-rainmaker-cli configure --region global
esp-rainmaker-cli configure --region china
```

These are equivalent to:
```bash
esp-rainmaker-cli profile switch global
esp-rainmaker-cli profile switch china
```

## Common Workflows

### Multi-Environment Setup

```bash
# Set up development environment
esp-rainmaker-cli profile add dev --base-url https://dev.rainmaker.company.com/api/
esp-rainmaker-cli profile switch dev
esp-rainmaker-cli login --user_name dev@company.com

# Set up production environment
esp-rainmaker-cli profile add prod --base-url https://rainmaker.company.com/api/
esp-rainmaker-cli profile switch prod
esp-rainmaker-cli login --user_name ops@company.com

# Work with development
esp-rainmaker-cli profile switch dev
esp-rainmaker-cli getnodes

# Deploy to production
esp-rainmaker-cli profile switch prod
esp-rainmaker-cli getnodes
```

### Profile Status Check

```bash
# Quick status check
esp-rainmaker-cli profile current

# Detailed status of all profiles
esp-rainmaker-cli profile list
```

## Troubleshooting

### Profile Not Found
```bash
esp-rainmaker-cli profile switch non-existent
# Output: Profile 'non-existent' does not exist.
# Use 'profile list' to see available profiles.
```

### Login Issues
```bash
# Check if logged in to current profile
esp-rainmaker-cli profile current

# If not logged in, login to current profile
esp-rainmaker-cli login --user_name your_email@example.com
```

### Reset Profile System
```bash
# Remove all profiles and start fresh
rm -rf ~/.espressif/rainmaker/profiles/

# Recreate default profiles
esp-rainmaker-cli profile current
```

## Profile Storage

Profiles are stored in `~/.espressif/rainmaker/profiles/`:

```
~/.espressif/rainmaker/
├── profiles/
│   ├── profiles.json          # Profile definitions
│   ├── current_profile        # Active profile name
│   ├── global_config.json     # Global profile tokens
│   ├── china_config.json      # China profile tokens
│   └── custom_config.json     # Custom profile tokens
└── claim_data/               # Claiming data
```

### Configuration Directory

By default, profile data is stored in `~/.espressif/rainmaker/`. You can override this with the `RM_USER_CONFIG_DIR` environment variable for backward compatibility:

```bash
# Use custom config directory
export RM_USER_CONFIG_DIR=/path/to/custom/config
esp-rainmaker-cli profile current
```

Each profile maintains independent:
- Authentication tokens
- Login sessions  
- Server configurations
- Profile metadata 