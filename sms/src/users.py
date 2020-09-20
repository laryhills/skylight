from time import time
from hashlib import md5
from pprint import pformat
from base64 import b64encode
from json import loads, dumps
from flask import abort, request
from itsdangerous.exc import BadSignature
from itsdangerous import JSONWebSignatureSerializer as Serializer

from sms.models.user import User
from sms.models.logs import LogsSchema
from sms.models.master import Master, MasterSchema, Props
from sms.config import app, bcrypt, add_token, get_token, remove_token, db


fn_props = {
    "users.login": {
        "perms": {},
        "logs": lambda user, params: "{} logged in".format(user)
    },
    "users.logout": {
        "perms": {},
        "logs": lambda user, params: "{} logged out".format(user)
    },
    "backups.backup_databases": {
        "perms": {},
        "logs": lambda user, params: "{} database backup{} complete".format(
                                      user, ["", " before restore"][int(bool(params.get("before_restore")))])
    },
    "jobs.remove_old_backups": {
        "perms": {},
        "logs": lambda user, params: "{} old backups removed".format(user)
    },
    "jobs.clear_cache_base_dir": {
        "perms": {},
        "logs": lambda user, params: "{} program cache cleared".format(user)
    }
}


def session_key():
    return app.config['SECRET_KEY']


def hash_key():
    s_key = session_key()
    session_key_sum = str(sum([int(x) for x in s_key if x in "0123456789"]))
    session_bytes = bytes(session_key_sum, "utf-8")
    return b64encode(md5(session_bytes).digest()).decode("utf-8").strip("=")


def tokenize(text):
    # Use on client side, this is just for testing
    s = Serializer(hash_key())
    return s.dumps(text).decode('utf-8')


def detokenize(token, parse=True):
    s = Serializer(hash_key())
    try:
        if parse:
            return dict(zip(*[("username","password"),s.loads(token).split(':')]))
        return s.loads(token)
    except BadSignature:
        return None


def backup_counter():
    query = Props.query.filter_by(key="DBWriteCounter").first()
    query.valueint = query.valueint + 1
    db.session.commit()
    if int(query.valueint) % 50 == 0:
        from sms.src.backups import backup_databases
        print("Begin backups")
        backup_databases()


def access_decorator(func):
    qual_name = func.__module__.split('.')[-1] + "." + func.__name__

    def inner1(*args, **kwargs):
        try:
            # IN PROD replace with `.get("token") and rm try and exc block`
            token = request.headers["token"]
        except Exception:
            print("Running from command line or swagger UI, token not supplied!")
            token = tokenize("ucheigbeka:testing")
            # abort(401)
        req_perms, token_dict = fn_props[qual_name]["perms"].copy(), get_token("TESTING_token") or get_token(token)
        if not token_dict:
            # Not logged in (using old session token)
            return None, 440
        user_perms = token_dict["perms"]
        print("your perms", user_perms)
        params = get_kwargs(func, args, kwargs)
        if params.get("superuser"):
            if not user_perms.get("superuser"):
                return 'Access Denied', 401
        has_access = True
        if "levels" in req_perms:
            level = params.get("level") or params.get("data", {}).get("level")
            mat_no = params.get("mat_no") or params.get("data", {}).get("mat_no")
            if mat_no and not level:
                level = get_level(mat_no, parse=False)
                if not level:
                    return None, 404
            has_access = False
            levels = user_perms.get("levels", [])
            mat_nos = user_perms.get("mat_nos", [])
            superuser = user_perms.get("superuser", False)
            has_access |= level in levels
            has_access |= mat_no in mat_nos
            has_access |= superuser
            req_perms.remove("levels")
        if "result_edit" in req_perms:
            superuser = user_perms.get("superuser", False)
            result_edit = bool(Props.query.filter_by(key="ResultEdit").first().valueint)
            if not (result_edit or superuser):
                return "result edit mode not open", 401
            req_perms.remove("result_edit")
        for perm in req_perms:
            has_access &= bool(user_perms.get(perm))
        if has_access:
            if "write" in req_perms and not get_token("TESTING_token"):
                backup_counter()
            (output, ret_code) = func(*args, **kwargs)
            if (ret_code == 200) and not get_token("TESTING_token"):
                log(token_dict["user"], qual_name, func, args, kwargs)
            return (output, ret_code)
        else:
            return 'Access Denied', 401
    return inner1


def accounts_decorator(func):
    qual_name = func.__module__.split('.')[-1] + "." + func.__name__

    def inner1(*args, **kwargs):
        try:
            # IN PROD replace with `.get("token") and rm try and exc block`
            token = request.headers["token"]
        except Exception:
            print("Running from command line or swagger UI, token not supplied!")
            token = tokenize("ucheigbeka:testing")
            # abort(401)
        req_perms, token_dict = fn_props[qual_name]["perms"].copy(), get_token("TESTING_token") or get_token(token)
        if not token_dict:
            # Not logged in (using old session token)
            return None, 440
        user_perms = token_dict["perms"]
        print ("your perms", user_perms)
        params = get_kwargs(func, args, kwargs)
        if params.get("superuser"):
            if not user_perms.get("superuser"):
                return 'Access Denied', 401
        has_access = True
        if "usernames" in req_perms:
            username = params.get("username") or params.get("data",{}).get("username")
            has_access = False
            usernames = user_perms.get("usernames", [])
            superuser = user_perms.get("superuser", False)
            has_access |= username in usernames
            has_access |= superuser
            req_perms.remove("usernames")
        for perm in req_perms:
            has_access &= bool(user_perms.get(perm))
        if has_access:
            if "write" in req_perms and not get_token("TESTING_token"):
                backup_counter()
            (output, ret_code) = func(*args, **kwargs)
            if (ret_code == 200) and not get_token("TESTING_token"):
                log(token_dict["user"], qual_name, func, args, kwargs)
            return (output, ret_code)
        else:
            return 'Access Denied', 401
    return inner1


def log(user, qual_name, func, args, kwargs):
    params = get_kwargs(func, args, kwargs)
    print("log msg => " + fn_props[qual_name]["logs"](user, params))
    log_data = {"timestamp": int(time()), "operation": qual_name, "user": user, "params": dumps(params)}
    log_record = LogsSchema().load(log_data)
    db.session.add(log_record)
    db.session.commit()


# UTILS functions

def load_session(session):
    # Valid inputs, 2015, "2015", "2015-2016", "2015_2016", "2015-2016.db", "2015_2016.db"
    session = str(session)[:4]
    session = "{}_{}".format(session, int(session) + 1)
    exec('from sms.models import _{}'.format(session))
    return eval('_{}'.format(session))


def get_DB(mat_no):
    # Lookup the student's details in the master db
    student = Master.query.filter_by(mat_no=mat_no).first()
    if not student:
        return None
    master_schema = MasterSchema()
    db_name = master_schema.dump(student)['database']
    return db_name.replace('-', '_')[:-3]


def get_level(mat_no, parse=True):
    # 600-800 - is spill, 100-500 spill not inc, -ve val if not parse = graduated
    db_name = get_DB(mat_no)
    if not db_name:
        return None
    session = load_session(db_name)
    PersonalInfo = session.PersonalInfo
    student_data = PersonalInfo.query.filter_by(mat_no=mat_no).first()
    current_level = student_data.level
    if parse:
        return abs(current_level)
    return current_level


# USER-specific functions
def dict_render(dct, indent = 0):
    rendered_dict = ""
    for key, val in dct.items():
        key = str(key).capitalize()
        if isinstance(val, dict):
            rendered_dict += "{}{} => \n".format(" " * indent, key)
            rendered_dict += dict_render(val, indent + 4)
        else:
            r_val = pformat(val).replace("\n ", "\n" + " " * (indent+6))
            rendered_dict += "{}{} => {}\n".format(" " * indent, key, r_val)
    if indent:
        return rendered_dict
    return rendered_dict[:-1].replace("_"," ")


def get_kwargs(func, args, kwargs):
    my_kwargs = kwargs.copy()
    if args:
        for idx in range(len(args)):
            kw = func.__code__.co_varnames[idx]
            my_kwargs[kw] = args[idx]
    return my_kwargs


def login(token):
    try:
        user = detokenize(token['token'])
        stored_user = User.query.filter_by(username=user['username']).first()
        if bcrypt.check_password_hash(stored_user.password, user['password']):
            token_dict = {'token': token['token']}
            add_token(token['token'], stored_user.username, loads(stored_user.permissions))
            token_dict['title'] = stored_user.title
            log(user['username'], 'users.login', login, [], [])
            return token_dict, 200
        return None, 401
    except Exception:
        return None, 401


@access_decorator
def logout(token):
    remove_token(token['token'])
    return None, 200


# PERFORM LOGIN, REMOVE IN PROD
my_token = {'token': tokenize("ucheigbeka:testing")}
print("Using token ", my_token['token'])
login(my_token)


# Function mapping to perms and logs
fn_props.update({
    "personal_info.get_exp": {"perms": {"levels", "read"},
                              "logs": lambda user, params: "{} requested personal details of {}".format(user, params.get("mat_no"))
                        },
    "personal_info.post_exp": {"perms": {"levels", "write"},
                              "logs": lambda user, params: "{} added personal details for {}:-\n{}".format(user, params.get("data").get("mat_no"), dict_render(params))
                        },
    "personal_info.patch": {"perms": {"levels", "write"},
                            "logs": lambda user, params: "{} modified personal details for {}:-\n{}".format(user, params.get("data").get("mat_no"), dict_render(params))
                        },
    "personal_info.delete": {"perms": {"superuser", "write"},
                            "logs": lambda user, params: "{} deleted student record for {}".format(user, params.get("mat_no"))
                        },
    "course_details.post": {"perms": {"superuser", "write"},
                            "logs": lambda user, params: "{} added course {}:-\n{}".format(user, params.get("course_code"), dict_render(params))
                        },
    "course_details.patch": {"perms": {"superuser", "write"},
                           "logs": lambda user, params: "{} updated courses:-\n{}".format(user, dict_render(params))
                        },
    "course_details.delete": {"perms": {"superuser", "write"},
                              "logs": lambda user, params: "{} deleted course {}:-\n{}".format(user, params.get("course_code"), dict_render(params))
                        },
    "result_update.get": {"perms": {"levels", "read"},
                          "logs": lambda user, params: "{} requested result update for {}".format(user, params.get("mat_no"))
                        },
    "course_form.get": {"perms": {"levels", "read"},
                        "logs": lambda user, params: "{} requested course form for {}".format(user, params.get("mat_no"))
                        },
    "broad_sheet.get": {"perms": {"superuser", "read"},
                        "logs": lambda user, params: "{} requested broad-sheets for the {} session".format(user, params.get('acad_session'))
                        },
    "senate_version.get": {"perms": {"superuser", "read"},
                           "logs": lambda user, params: "{} requested senate version for the {} session".format(user,params.get('acad_session'))
                           },
    "gpa_cards.get": {"perms": {"levels", "read"},
                      "logs": lambda user, params: "{} requested {} level gpa card".format(user, params.get('level'))
                      },
    "course_reg.get": {"perms": {"levels", "read"},
                           "logs": lambda user, params: "{} queried course registration for {}".format(user, params.get("mat_no"))
                        },
    "course_reg.init_new": {"perms": {"levels", "read"},
                           "logs": lambda user, params: "{} queried data for course registration for {}".format(user, params.get("mat_no"))
                        },
    "course_reg.post": {"perms": {"levels", "write"},
                        "logs": lambda user, params: "{} added course registration for {}:-\n{}".format(user, params.get("data").get("mat_no"), dict_render(params))
                        },
    "course_reg.delete": {"perms": {"levels", "write"},
                          "logs": lambda user, params: "{} deleted {}/{} course registration entry for {}".format(user, params.get("acad_session"), params.get("acad_session")+1, params.get("mat_no"))
                          },
    "results.get": {"perms": {"levels", "read"},
                    "logs": lambda user, params: "{} queried results for {}".format(user, params.get("mat_no"))
                    },
    "results.post": {"perms": {"levels", "write", "result_edit"},
                     "logs": lambda user, params: "{} added {} result entries:-\n{}".format(user, len(params.get("data")), dict_render(params))
                     },
    "results.set_resultedit": {"perms": {"superuser", "write"},
                               "logs": lambda user, params: "{} {} result edit mode".format(user, ['closed', 'opened'][bool(params.get('state'))])
                               },
    "results.get_result_details": {"perms": {"levels", "read"},
                                   "logs": lambda user, params: "{} queried result details for {}".format(user, params.get("mat_no"))
                                   },
    "results.get_single_results_stats": {"perms": {"levels", "read"},
                                           "logs": lambda user, params: "{} queried the result stats for the {} for the {} academic session".format(user, params.get("mat_no"), params.get("acad_session"))
                                        },
    "results.get_multiple_results_stats": {"perms": {"levels", "read"},
                                           "logs": lambda user, params: "{} queried all the result stats for the {} level students for the {} academic session".format(user, params.get("level"), params.get("acad_session"))
                                        },
    "logs.get": {"perms": {"read"},
                 "logs": lambda user, params: "{} requested logs".format(user)
                 },
    "logs.delete": {"perms": {"write", "superuser"},
                 "logs": lambda user, params: "{} cleared {} logs".format(user, len(params.get("ids")) if params.get("ids") else "all")
                 },
    "accounts.get": {"perms": {"usernames", "read"},
                     "logs": lambda user, params: "{} requested {} account details".format(user, params.get("username", "all"))
                 },
    "accounts.post": {"perms": {"superuser", "write"},
                      "logs": lambda user, params: "{} added a new account with username {}".format(user, params.get("data").get("username"))
                     },
    "accounts.patch": {"perms": {"usernames", "write"},
                     "logs": lambda user, params: "{} modified {}'s account".format(user, params.get("data").get("username"))
                     },
    "accounts.delete": {"perms": {"superuser", "write"},
                        "logs": lambda user, params: "{} deleted an account with username {}".format(user, params.get("username"))
                     },
    "backups.get": {"perms": {"usernames", "read"},
                    "logs": lambda user, params: "{} requested list of backups".format(user)
                    },
    "backups.download": {"perms": {"superuser", "read"},
                         "logs": lambda user, params: "{} requested backups files, with:\n{}".format(user, dict_render(params))
                         },
    "backups.backup": {"perms": {"superuser", "write"},
                       "logs": lambda user, params: "{} initialized database backup".format(user)
                       },
    "backups.restore": {"perms": {"superuser", "read"},
                        "logs": lambda user, params: '{} restored backup "{}"{}'.format(user, params.get("backup_name"),
                            ["", "; previous account details included"][int(bool(params.get("include_accounts")))])
                        },
    "backups.delete": {"perms": {"superuser", "read"},
                       "logs": lambda user, params: '{} deleted backup "{}"'.format(user, params.get("backup_name"))
                       },
    "grading_rules.get": {"perms": {"levels", "read"},
                          "logs": lambda user, params: "{} requested for the grading rules for the {} academic session".format(user, params.get('acad_session'))
                          },
})
