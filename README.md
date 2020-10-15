# Skylight
This project represents the server side of the **Student Management System**.

## Setup Instructions
- **Wkhtmltopdf** is needed for generating the pdfs. Head over to wkhtmltopdf [download page](https://wkhtmltopdf.org/downloads.html) for binary installers

- **Pipenv** is the project's dependency manager. Install instructions can be found on the [PyPI page](https://pypi.org/project/pipenv/)

- Create a virtual environment with python3
```
pipenv --python 3
```

- Clone this repo
```
git clone https://github.com/lordfme/skylight.git
```

- Navigate to the project's root and start a virtual environment 
```
cd skylight

pipenv shell
```

- Install all dependencies
```
pipenv install
```

### Setting up the server 
- Windows
```
setup/setup.bat

set FLASK_APP=server.py:app
```

- Unix
```
setup/setup.sh

export FLASK_APP=server.py:app
```

### Start the server with
```
flask run
```


###### Note:
Current data in `accounts.db`
 - username = ucheigbeka
 - password = testing
