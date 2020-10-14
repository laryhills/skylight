# Skylight
This project represents the server side of the **Student Management System** for the Department of Mechanical 
Engineering, University of Benin.

## Setup Instructions
- **Wkhtmltopdf** is needed for generating the pdfs. Head over to wkhtmltopdf [download page](https://wkhtmltopdf.org/downloads.html) for binary installers

- [**Pipenv**](https://pypi.org/project/pipenv/) is the project's dependency manager. Install with
```
python -m pip install pipenv
```

- Create a virtual environment with the python installation
```
pipenv --python 3.8
```

- Clone this repo
```
git clone https://github.com/lordfme/skylight.git
```

- Navigate to the project's root and start the virtual environment and 
```
cd skylight

pipenv shell
```

- Install all the dependencies with pipenv
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
Current data in the `accounts.db`
    - username = ucheigbeka
    - password = testing
