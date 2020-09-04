import os
import secrets
import tempfile
import connexion
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
from flask_bcrypt import Bcrypt

base_dir = os.path.dirname(__file__)
CACHE_DIR = os.path.join(os.path.expanduser('~'), 'sms', 'cache_mechanical')
BACKUP_DIR = os.path.join(os.path.expanduser('~'), 'sms', 'backups_mechanical')
DB_DIR = os.path.join(base_dir, 'database')
TEMP_DIR = os.path.join(tempfile.gettempdir(), 'sms', 'mechanical')

CACHE_BASE_DIR = TEMP_DIR

[os.makedirs(path) for path in (CACHE_DIR, BACKUP_DIR, DB_DIR, TEMP_DIR) if not os.path.exists(path)]


start_session = 2003
end_session = 2019  # TODO query current_session from master DB, (don't use utils)

sqlalchemy_binds = {'master': 'sqlite:///' + os.path.join(DB_DIR, 'master.db'),
                    'courses': 'sqlite:///' + os.path.join(DB_DIR, 'courses.db'),
                    'logs': 'sqlite:///' + os.path.join(DB_DIR, 'logs.db')}
sqlalchemy_binds.update({'{}-{}'.format(num, num + 1): 'sqlite:///' + os.path.join(DB_DIR, '{}-{}.db'.format(num, num + 1)) for num in range(start_session, end_session + 1)})

connex_app = connexion.App(__name__, specification_dir=base_dir)
app = connex_app.app

app.config['SECRET_KEY'] = secrets.token_hex(16)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(DB_DIR, 'accounts.db')
app.config['SQLALCHEMY_BINDS'] = sqlalchemy_binds
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True

db = SQLAlchemy(app)
ma = Marshmallow(app)
bcrypt = Bcrypt(app)
tokens = {}

scheduler = None
jobs = []


def add_token(token, username, permissions):
    tokens[token] = {"user": username, "perms": permissions}


def get_token(token):
    return tokens.get(token)


def remove_token(token):
    return tokens.pop(token, None)


def get_current_session():
    from sms.models.master import Props
    current_session = Props.query.filter_by(key="CurrentSession").first().valueint
    return int(current_session)


@app.before_first_request
def start_jobs():
    from sms.src.ext.jobs import start_scheduled_jobs
    global scheduler, jobs
    scheduler, jobs = start_scheduled_jobs()
