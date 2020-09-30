# Skylight
This project represents the server side of the **Student Management System** for the Department of Mechanical 
Engineering, University of Benin.

# Requirements
Skylight requires python >= 3.8 and redis >= 3.2.100. Make sure the server is running locally on port 6379.

**Note**: Due to the non-availability of `os.fork`, one of the dependencies, rq, does not run on the Windows native Python interpreter. An alternative for Windows users would be to run a Unix emulation using [Windows SubSystem for Linux (WSL)]('https://msdn.microsoft.com/en-us/commandline/wsl/about')

## Setup Instructions
- Download and install redis. On Windows, Microsoft maintains installers [here]('http://github.com/MicrosoftArchive/redis/releases'). Linux and Mac OS X users can get it either through their package manager or directly from the [redis official website.]('https://redis.io/')
- Start the redis server manually with the `redis-server` command. You can check if the server is running by pinging it with the `redis-cli PING`  command.
- Install `pipenv` with python's default package manager
```
python -m pip install pipenv
```
- Create a virtual environment with the python installation
```
pipenv --python 3.8
```
- Start the virtual environment and navigate to the project's root
```
pipenv start
cd path/to/project/root
```
- Install all the dependencies with `pipenv`
```
pipenv install
```

## Instructions
- `server.py` is the main entry point into the app
- Before executing `server.py` first run `setup/src/generate_models.py` 
  which generates all the database models
- Also run `setup/setup.bat` (Windows) or `setup/setup.sh` (Unix) to generate the database

###### Note:
1. Current data in the `accounts.db`
    - username = ucheigbeka
    - password = testing

2. [**Wkhtmltopdf**](https://wkhtmltopdf.org/downloads.html) is needed for generating the pdfs