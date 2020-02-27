import os
import secrets
import connexion
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
from flask_bcrypt import Bcrypt

base_dir = os.path.dirname(__file__)
db_path = os.path.join(base_dir, 'database')

start_session = 2003
end_session = 2019

sqlalchemy_binds = {'master': 'sqlite:///' + os.path.join(db_path, 'master.db'),
                    'courses': 'sqlite:///' + os.path.join(db_path, 'courses.db')}
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

def add_token(token, user):
    tokens[token] = user

def get_token(token):
    return tokens.get(token, None)
