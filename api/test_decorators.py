import sqlite3
import requests
from sms import config
from sms.users import access_decorator
from sms.users import accounts_decorator

conn = sqlite3.connect("sms/database/accounts.db")
conn.row_factory=sqlite3.Row
cur=conn.cursor()

username = "decorator_test"
student_400 = "ENG1604295"
dummy_access_fn = lambda *args, **kwargs: (True, 200)
dummy_accounts_fn = lambda *args, **kwargs: (True, 200)

perms_list = [
    {},
    {"read": True, "write": True, "superuser": True, "levels": []},
    {"read": True, "write": True, "superuser": False, "levels": []},
    {"read": True, "write": False, "superuser": True, "levels": []},
    {"read": True, "write": False, "superuser": False, "levels": []},
    {"read": False, "write": True, "superuser": True, "levels": []},
    {"read": False, "write": True, "superuser": False, "levels": []},
    {"read": False, "write": False, "superuser": True, "levels": []},
    {"read": False, "write": False, "superuser": False, "levels": []},

    {"read": True, "write": True, "superuser": True, "levels": [], "usernames": ["lordfme"]},
    {"read": True, "write": True, "superuser": False, "levels": [], "usernames": ["lordfme"]},
    {"read": True, "write": False, "superuser": True, "levels": [], "usernames": ["lordfme"]},
    {"read": True, "write": False, "superuser": False, "levels": [], "usernames": ["lordfme"]},
    {"read": False, "write": True, "superuser": True, "levels": [], "usernames": ["lordfme"]},
    {"read": False, "write": True, "superuser": False, "levels": [], "usernames": ["lordfme"]},
    {"read": False, "write": False, "superuser": True, "levels": [], "usernames": ["lordfme"]},
    {"read": False, "write": False, "superuser": False, "levels": [], "usernames": ["lordfme"]},

    {"read": True, "write": True, "superuser": True, "levels": [400], "usernames": [username]},
    {"read": True, "write": True, "superuser": False, "levels": [400], "usernames": [username]},
    {"read": True, "write": False, "superuser": True, "levels": [400], "usernames": [username]},
    {"read": True, "write": False, "superuser": False, "levels": [400], "usernames": [username]},
    {"read": False, "write": True, "superuser": True, "levels": [400], "usernames": [username]},
    {"read": False, "write": True, "superuser": False, "levels": [400], "usernames": [username]},
    {"read": False, "write": False, "superuser": True, "levels": [400], "usernames": [username]},
    {"read": False, "write": False, "superuser": False, "levels": [400], "usernames": [username]},

]


def test_personal_dets_get():
    # Levels & read perms
    dummy_access_fn.__module__ = "personal_dets"
    dummy_access_fn.__name__ = "get"
    for perms in perms_list:
        config.add_token("TESTING_token", username, perms)
        if perms.get("read") and (400 in perms.get("levels", []) or perms.get("superuser")):
            has_access = 200
        else:
            has_access = 401
        output, ret_code = access_decorator(dummy_access_fn)(mat_no=student_400)
        assert has_access == ret_code

def test_personal_dets_post():
    # Levels & write perms
    dummy_access_fn.__module__ = "personal_dets"
    dummy_access_fn.__name__ = "post"
    student_data = {"mat_no": "ENG1603123", "level": 400}
    for perms in perms_list:
        config.add_token("TESTING_token", username, perms)
        if perms.get("write") and (student_data["level"] in perms.get("levels", []) or perms.get("superuser")):
            has_access = 200
        else:
            has_access = 401
        output, ret_code = access_decorator(dummy_access_fn)(data=student_data)
        assert has_access == ret_code


def test_accounts_get_all():
    # superuser & read perms
    dummy_accounts_fn.__module__ = "accounts"
    dummy_accounts_fn.__name__ = "get"
    for perms in perms_list:
        config.add_token("TESTING_token", username, perms)
        if perms.get("read") and perms.get("superuser"):
            has_access = 200
        else:
            has_access = 401
        output, ret_code = accounts_decorator(dummy_accounts_fn)()
        assert has_access == ret_code


def test_accounts_get_self():
    # usernames and read perms
    dummy_accounts_fn.__module__ = "accounts"
    dummy_accounts_fn.__name__ = "get"
    for perms in perms_list:
        config.add_token("TESTING_token", username, perms)
        if perms.get("read") and ( perms.get("superuser") or username in perms.get("usernames", []) ):
            has_access = 200
        else:
            has_access = 401
        output, ret_code = accounts_decorator(dummy_accounts_fn)(username=username)
        assert has_access == ret_code


def test_accounts_get_managed():
    # usernames and read perms
    dummy_accounts_fn.__module__ = "accounts"
    dummy_accounts_fn.__name__ = "get"
    for perms in perms_list:
        config.add_token("TESTING_token", username, perms)
        if perms.get("read") and ( perms.get("superuser") or "lordfme" in perms.get("usernames", []) ):
            has_access = 200
        else:
            has_access = 401
        output, ret_code = accounts_decorator(dummy_accounts_fn)(username="lordfme")
        assert has_access == ret_code


def test_accounts_post():
    # superuser and write perms
    dummy_accounts_fn.__module__ = "accounts"
    dummy_accounts_fn.__name__ = "post"
    for perms in perms_list:
        config.add_token("TESTING_token", username, perms)
        if perms.get("write") and perms.get("superuser"):
            has_access = 200
        else:
            has_access = 401
        output, ret_code = accounts_decorator(dummy_accounts_fn)(data={"username":username})
        assert has_access == ret_code


def test_accounts_put():
    # superuser and write perms
    dummy_accounts_fn.__module__ = "accounts"
    dummy_accounts_fn.__name__ = "put"
    for perms in perms_list:
        config.add_token("TESTING_token", username, perms)
        if perms.get("write") and perms.get("superuser"):
            has_access = 200
        else:
            has_access = 401
        output, ret_code = accounts_decorator(dummy_accounts_fn)(data={"username":username})
        assert has_access == ret_code


def test_accounts_manage_self():
    # usernames and write perms
    dummy_accounts_fn.__module__ = "accounts"
    dummy_accounts_fn.__name__ = "manage"
    for perms in perms_list:
        config.add_token("TESTING_token", username, perms)
        if perms.get("write") and ( perms.get("superuser") or username in perms.get("usernames", []) ):
            has_access = 200
        else:
            has_access = 401
        output, ret_code = accounts_decorator(dummy_accounts_fn)(data={"username": username})
        assert has_access == ret_code


def test_accounts_manage_other():
    # usernames and write perms
    dummy_accounts_fn.__module__ = "accounts"
    dummy_accounts_fn.__name__ = "manage"
    for perms in perms_list:
        config.add_token("TESTING_token", username, perms)
        if perms.get("write") and ( perms.get("superuser") or "lordfme" in perms.get("usernames", []) ):
            has_access = 200
        else:
            has_access = 401
        output, ret_code = accounts_decorator(dummy_accounts_fn)(data={"username": "lordfme"})
        assert has_access == ret_code


def test_accounts_delete():
    # superuser and write perms
    dummy_accounts_fn.__module__ = "accounts"
    dummy_accounts_fn.__name__ = "delete"
    for perms in perms_list:
        config.add_token("TESTING_token", username, perms)
        if perms.get("write") and perms.get("superuser"):
            has_access = 200
        else:
            has_access = 401
        output, ret_code = accounts_decorator(dummy_accounts_fn)(username=username)
        assert has_access == ret_code


def test_senate_version_get():
    # superuser and read perms
    dummy_accounts_fn.__module__ = "senate_version"
    dummy_accounts_fn.__name__ = "get"
    for perms in perms_list:
        config.add_token("TESTING_token", username, perms)
        if perms.get("read") and perms.get("superuser"):
            has_access = 200
        else:
            has_access = 401
        output, ret_code = accounts_decorator(dummy_accounts_fn)(acad_session="2019")
        assert has_access == ret_code


def test_get_logs():
    # read perms
    dummy_accounts_fn.__module__ = "logs"
    dummy_accounts_fn.__name__ = "get"
    for perms in perms_list:
        config.add_token("TESTING_token", username, perms)
        if perms.get("read"):
            has_access = 200
        else:
            has_access = 401
        output, ret_code = accounts_decorator(dummy_accounts_fn)()
        assert has_access == ret_code


def test_result_get():
    # Levels and read perms
    dummy_access_fn.__module__ = "results"
    dummy_access_fn.__name__ = "get"
    for perms in perms_list:
        config.add_token("TESTING_token", username, perms)
        if perms.get("read") and (400 in perms.get("levels", []) or perms.get("superuser")):
            has_access = 200
        else:
            has_access = 401
        output, ret_code = access_decorator(dummy_access_fn)(mat_no=student_400)
        assert has_access == ret_code


'''
def test_result_post():
    # Levels and write perms
    # TODO how is this restricted to a level? what are list_of_results? and is it one level at a time?
    dummy_access_fn.__module__ = "results"
    dummy_access_fn.__name__ = "post"
    for perms in perms_list:
        config.add_token("TESTING_token", username, perms)
        if perms.get("write") and (400 in perms.get("levels", []) or perms.get("superuser")):
            has_access = 200
        else:
            has_access = 401
        output, ret_code = access_decorator(dummy_access_fn)(list_of_results="lalala")
        assert has_access == ret_code
'''