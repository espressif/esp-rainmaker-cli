### Development Guide

Development mode allows you to run the latest version of esp-rainmaker-cli from the repository.
If you are making any changes to the tool then in order to test the changes please follow the below steps.

```
python3 -m pip install -e .
```

This will install esp-rainmaker-cli's dependencies and create an executable script wrappers in the user’s bin
directory. The wrappers will run the scripts found in the git working directory directly, so any time the working
directory contents change it will pick up the new versions.
