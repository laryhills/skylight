from flask import abort, request
from json import loads, dumps
from sms.models.user import User
from sms.config import app, bcrypt, add_token, get_token, db
from base64 import b64encode
from hashlib import md5
from flask import abort
from sms.models.master import Master, MasterSchema
from sms.models.logs import LogsSchema
from sys import modules
from importlib import reload
from time import time
from itsdangerous import JSONWebSignatureSerializer as Serializer


def login(token):
    try:
        user = detokenize(token['token'])
        stored_user = User.query.filter_by(username=user['username']).first()
        if bcrypt.check_password_hash(stored_user.password, user['password']):
            token_dict = {'token': token['token']}
            add_token(token['token'], stored_user.username, loads(stored_user.permissions))
            return token_dict, 200
        abort(401)
    except Exception:
        abort(401)


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


def hash_key(session_key = session_key()):
    session_key_sum = str(sum([int(x) for x in session_key if x in "0123456789"]))
    session_bytes = bytes(session_key_sum, "utf-8")
    return b64encode(md5(session_bytes).digest()).decode("utf-8").strip("=")


def access_decorator(func):
    qual_name = func.__module__.split('.')[-1] + "." + func.__name__
    def inner1(*args, **kwargs):
        try:
            # IN PROD replace with `.get("token") and rm try and exc block`
            token = request.headers["token"]
        except Exception:
            # print ("Running from command line or swagger UI, token not supplied!")
            # token = tokenize("ucheigbeka:testing")
            abort(401)
        req_perms, token_dict = fn_props[qual_name]["perms"], get_token(token)
        user_perms, mat_no = token_dict["perms"], kwargs.get("mat_no")
        if not token_dict:
            # Not logged in (using old session token)
            abort(440)
        has_access = True
        if mat_no:
            extras, levels = user_perms.get("extras"), user_perms.get("levels")
            if levels:
                level = get_level(mat_no)
                has_access |= level in levels
            if extras:
                has_access |= (mat_no in extras)
        for perm in req_perms:
            has_access &= bool(user_perms.get(perm))
        if has_access:
            log(token_dict["user"], qual_name, func, args, kwargs)
            return func(*args, **kwargs)
        else:
            abort(401)
    return inner1


def log(user, qual_name, func, args, kwargs):
    params = get_kwargs(func, args, kwargs)
    print ("log msg => " + fn_props[qual_name]["logs"](user, params))
    log_data = {"timestamp": time(), "operation": qual_name, "user": user, "params": dumps(params)}
    log_post(log_data)

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


def get_level(mat_no):
    # 600-800 - is spill, 100-500 spill not inc, grad_status - graduated
    # if next = True, return next level else current level
    db_name = get_DB(mat_no)[:-3]
    session = load_session(db_name)
    PersonalInfo = session.PersonalInfo
    student_data = PersonalInfo.query.filter_by(mat_no=mat_no).first_or_404()
    return student_data.current_level

## USER-specific functions

def dict_render(dictionary, indent = 0):
    rendered_dict = ""
    for key in dictionary:
        if isinstance(dictionary[key], dict):
            rendered_dict += "{} => \n".format(key.capitalize())
            rendered_dict += dict_render(dictionary[key], indent = 4)
        else:
            rendered_dict += "{}{} => {}\n".format(' ' * indent, key.capitalize(), dictionary[key])
    if indent:
        return rendered_dict.replace("_"," ")
    return rendered_dict[:-1].replace("_"," ")


def get_kwargs(func, args, kwargs):
    my_kwargs = kwargs.copy()
    if args:
        for idx in range(len(args)):
            kw = func.__code__.co_varnames[idx]
            my_kwargs[kw] = args[idx]
    return my_kwargs


def log_post(log_data):
    log_record = LogsSchema().load(log_data)
    db.session.add(log_record)
    db.session.commit()

## PERFORM LOGIN, REMOVE IN PROD

# my_token = {'token': tokenize("ucheigbeka:testing")}
# print("Using token ", my_token['token'])
# login(my_token)

## Function mapping to perms and logs
fn_props = {
    "personal_info.get": {"perms": ["read"],
                          "logs": lambda user, params: "{} requested personal details of {}".format(user, params.get("mat_no"))
                        },
    "personal_info.post": {"perms": ["write"],
                           "logs": lambda user, params: "{} set personal details for {}:-\n{}".format(user, params.get("student_data").get("mat_no"), dict_render(params))
                        },
    "course_details.post": {"perms": ["superuser"],
                            "logs": lambda user, params: "{} added course {}:-\n{}".format(user, params.get("course_code"), dict_render(params))
                        },
    "result_update.get": {"perms": ["read"],
                          "logs": lambda user, params: "{} requested result update for {}".format(user, params.get("mat_no"))
                        },
    "course_form.get": {"perms": ["read"],
                        "logs": lambda user, params: "{} requested course form for {}".format(user, params.get("mat_no"))
                        },
    "course_reg.get": {"perms": ["read"],
                       "logs": lambda user, params: "{} queried course registration for {}".format(user, params.get("mat_no"))
                        },
    "course_reg.post": {"perms": ["write"],
                        "logs": lambda user, params: "{} added course registration for {}:-\n{}".format(user, params.get("course_reg").get("mat_no"), dict_render(params))
                        },
    "results.get": {"perms": ["read"],
                    "logs": lambda user, params: "{} queried results for {}".format(user, params.get("mat_no"))
                    },
    "results.post": {"perms": ["write"],
                     "logs": lambda user, params: "{} added {} result entries:-\n{}".format(user, len(params.get("list_of_results")), dict_render(params))
                     },
    "logs.get": {"perms": ["read", "levels"],
                 "logs": lambda user, params: "{} requested logs".format(user)
                 },
}
