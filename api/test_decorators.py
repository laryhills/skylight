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

    {"read": True, "write": True, "superuser": True, "levels": [400], "usernames": ["decorator_test"]},
    {"read": True, "write": True, "superuser": False, "levels": [400], "usernames": ["decorator_test"]},
    {"read": True, "write": False, "superuser": True, "levels": [400], "usernames": ["decorator_test"]},
    {"read": True, "write": False, "superuser": False, "levels": [400], "usernames": ["decorator_test"]},
    {"read": False, "write": True, "superuser": True, "levels": [400], "usernames": ["decorator_test"]},
    {"read": False, "write": True, "superuser": False, "levels": [400], "usernames": ["decorator_test"]},
    {"read": False, "write": False, "superuser": True, "levels": [400], "usernames": ["decorator_test"]},
    {"read": False, "write": False, "superuser": False, "levels": [400], "usernames": ["decorator_test"]},

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
        if perms.get("read") and ( perms.get("superuser") or "decorator_test" in perms.get("usernames", []) ):
            has_access = 200
        else:
            has_access = 401
        output, ret_code = accounts_decorator(dummy_accounts_fn)(username="decorator_test")
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
        output, ret_code = accounts_decorator(dummy_accounts_fn)(data={"username":"post_test"})
        assert has_access == ret_code
