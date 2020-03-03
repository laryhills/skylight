from flask import abort, request
from json import loads
from sms.models.user import User
from sms.config import app, bcrypt, add_token, get_token
from base64 import b64encode
from hashlib import md5
from flask import abort
from sms.models.master import Master, MasterSchema
from sys import modules
from importlib import reload
from itsdangerous import JSONWebSignatureSerializer as Serializer


def login(token):
    try:
        user = detokenize(token)
        stored_user = User.query.filter_by(username=user['username']).first()
        if bcrypt.check_password_hash(stored_user.password, user['password']):
            token_dict = {'token': token}
            add_token(token, stored_user.username, loads(stored_user.permissions))
            return token_dict, 200
        abort(400)
    except Exception:
        abort(400)


def tokenize(text):
    # Use on client side, this is just for testing
    s = Serializer(hash_key())
    return s.dumps(text).decode('utf-8')


def detokenize(token):
    s = Serializer(hash_key())
    return dict(zip(*[("username","password"),s.loads(token).split(':')]))


def session_key():
    # TODO expose this on swagger to be called by client on login
    return app.config['SECRET_KEY']


def hash_key():
    session_key_sum = str(sum([int(x) for x in session_key() if x in "0123456789"]))
    session_bytes = bytes(session_key_sum, "utf-8")
    return b64encode(md5(session_bytes).digest()).decode("utf-8").strip("=")


def access_decorator(func):
    def inner1(*args, **kwargs):
        try:
            # IN PROD replace with `.get("token") and rm try and exc block`
            token = request.headers["token"]
        except Exception:
            print ("Running from command line or swagger UI, token not supplied!")
            token = tokenize("ucheigbeka:testing")
        req_perms, token_dict = func.__defaults__[-1], get_token(token)
        user_perms, mat_no = token_dict["perms"], kwargs.get("mat_no")
        if not token_dict:
            # Not logged in (using old session token)
            abort(440)
        has_access = True
        if mat_no:
            level = get_level(mat_no)
            has_access &= level in user_perms["levels"]
        for perm in req_perms:
            has_access &= bool(user_perms.get(perm))
        if has_access:
            return func(*args, **kwargs)
        else:
            abort(401)
    return inner1


## UTILS functions

lastLoaded = None

def load_session(session):
    #Import model and force import override if necessary (session changes)
    global lastLoaded
    exec('from sms.models import _{}'.format(session))
    if ('sms.models._{}'.format(session) in modules) and (lastLoaded!=session):
        exec('reload(_{})'.format(session))
    lastLoaded = session
    return eval('_{}'.format(session))


def get_DB(mat_no):
    # Lookup the student's details in the master db
    student = Master.query.filter_by(mat_no=mat_no).first_or_404()
    master_schema = MasterSchema()
    db_name = master_schema.dump(student)['database']
    return db_name.replace('-', '_')


def get_level(mat_no, next = False):
    # 600-800 - is spill, 100-500 spill not inc, grad_status - graduated
    # if next = True, return next level else current level
    db_name = get_DB(mat_no)[:-3]
    session = load_session(db_name)
    PersonalInfo = session.PersonalInfo
    student_data = PersonalInfo.query.filter_by(mat_no=mat_no).first_or_404()
    if next:
        #TODO implement using results table to update with probation category
        return student_data.current_level + 100
    return student_data.current_level


## PERFORM LOGIN, REMOVE IN PROD

my_token = tokenize("ucheigbeka:testing")
login(my_token)
