import os
import secrets
import connexion
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
from flask_bcrypt import Bcrypt

base_dir = os.path.dirname(__file__)
db_path = os.path.join(base_dir, 'database')

start_session = 2003
end_session = 2019 # TODO query from master DB, (don't use utils)

sqlalchemy_binds = {'master': 'sqlite:///' + os.path.join(db_path, 'master.db'),
                    'courses': 'sqlite:///' + os.path.join(db_path, 'courses.db'),
                    'logs': 'sqlite:///' + os.path.join(db_path, 'logs.db')}
sqlalchemy_binds.update({'{}-{}'.format(num, num + 1): 'sqlite:///' + os.path.join(db_path, '{}-{}.db'.format(num, num + 1)) for num in range(start_session, end_session + 1)})

connex_app = connexion.App(__name__, specification_dir=base_dir)
app = connex_app.app

app.config['SECRET_KEY'] = secrets.token_hex(16)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(db_path, 'accounts.db')
app.config['SQLALCHEMY_BINDS'] = sqlalchemy_binds
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True

db = SQLAlchemy(app)
ma = Marshmallow(app)
bcrypt = Bcrypt(app)
tokens = {}

cache_base_dir = os.path.join(os.path.expanduser('~'), 'sms', 'cache_mechanical')


def add_token(token, username, permissions):
    tokens[token] = {"user": username, "perms": permissions}


def get_token(token):
    return tokens.get(token)


def get_current_session():
    # Code stub that returns current session, TODO take from master.db
    return 2019
