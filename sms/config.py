import os
import secrets
import tempfile
import connexion
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
from flask_bcrypt import Bcrypt

base_dir = os.path.dirname(__file__)

# ===========================================================
#                       CONSTANTS
# ===========================================================
# directories
CACHE_DIR = os.path.join(os.path.expanduser('~'), 'sms', 'cache_mechanical')
BACKUP_DIR = os.path.join(os.path.expanduser('~'), 'sms', 'backups_mechanical')
DB_DIR = os.path.join(base_dir, 'database')
TEMP_DIR = os.path.join(tempfile.gettempdir(), 'sms', 'mechanical')
CACHE_BASE_DIR = TEMP_DIR

# others
UNIBEN_LOGO_PATH = 'file:///' + os.path.join(base_dir, 'templates', 'static', 'Uniben_logo.png')
BACKUPS_TO_RETAIN = 20

# Make dirs
[os.makedirs(path) for path in (CACHE_DIR, BACKUP_DIR, DB_DIR, TEMP_DIR) if not os.path.exists(path)]

# Setup Flask app
connex_app = connexion.App(__name__, specification_dir=base_dir)
app = connex_app.app
app.config['SECRET_KEY'] = secrets.token_hex(16)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(DB_DIR, 'accounts.db')
app.config['SQLALCHEMY_BINDS'] = {key: 'sqlite:///' + os.path.join(DB_DIR, f'{key}.db') for key in ('master', 'courses', 'logs')}
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True

# Initialize extensions
db = SQLAlchemy(app)
ma = Marshmallow(app)
bcrypt = Bcrypt(app)


# Initialize global vars
tokens = {}
jobs = []
scheduler = None


# funcs to work on global vars
def add_token(token, username, permissions):
    tokens[token] = {"user": username, "perms": permissions}


def get_token(token):
    return tokens.get(token)


def remove_token(token):
    tokens.pop(token, None)
    if not tokens:
        app.config['SECRET_KEY'] = secrets.token_hex(16)


def get_current_session():
    from sms.models.master import Props
    current_session = Props.query.filter_by(key="CurrentSession").first().valueint
    return int(current_session)


# Update sqlalchemy binds
def update_binds(start_session=2003, current_session=get_current_session()):
    for num in range(start_session, current_session + 1):
        app.config['SQLALCHEMY_BINDS'].update({
            f'{num}-{num+1}': 'sqlite:///' + os.path.join(DB_DIR, f'{num}-{num+1}.db')
        })


@app.before_first_request
def start_jobs():
    from sms.src.ext.jobs import start_scheduled_jobs
    global scheduler, jobs
    scheduler, jobs = start_scheduled_jobs()


update_binds()
