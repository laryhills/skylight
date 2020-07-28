import sqlite3
from sms import accounts
from random import sample
from sms import config
from time import time
from sms.users import tokenize

conn = sqlite3.connect("sms/database/accounts.db")
conn.row_factory=sqlite3.Row
cur=conn.cursor()
perms = {"read": True, "write": True, "superuser": True, "levels": [100, 200, 300, 600], "usernames": ["accounts_test"]}
config.add_token("TESTING_token", "accounts_test", perms)
acct_keys = ("username", "password", "permissions", "title", "fullname", "email")
acct_values = ("accounts_test", tokenize("somepwdhash"), "{}", "Testing", "Accounts Test", "accounts@te.st")
acct_base = dict(zip(acct_keys, acct_values))
#TODO add invalid password tests for post, put, manage


def get_account(username):
    return cur.execute("SELECT * FROM user WHERE username=?",(username,)).fetchone()


def insert_account(dummy_acct):
    cur.execute("INSERT INTO user VALUES(?,?,?,?,?,?)", dummy_acct)
    conn.commit()


def delete_account(username):
    cur.execute("DELETE FROM user WHERE username=?",(username,))
    conn.commit()


def test_get_all_accounts():
    user_list, ret_code = accounts.get()
    assert ret_code == 200
    user_count = len(cur.execute("SELECT username FROM user").fetchall())
    assert user_count == len(user_list)
    for user in user_list:
        username = user["username"]
        user_row = get_account(username)
        for prop in user:
            assert user[prop] == user_row[prop]


def test_get_one_account():
    user_rows = cur.execute("SELECT * FROM user").fetchall()
    user_row = sample(user_rows, 1)[0]
    user, ret_code = accounts.get(user_row["username"])
    user = user[0]
    assert ret_code == 200
    for prop in user:
        assert user[prop] == user_row[prop]


def test_get_invalid_username():
    user, ret_code = accounts.get("invalid_username_" + str(time()))
    assert ret_code == 404


def test_post_new_account():
    dummy_acct = acct_base.copy()
    output, ret_code = accounts.post(data=dummy_acct)
    assert ret_code == 200
    user_row = get_account(dummy_acct["username"])
    for prop in dummy_acct:
        assert dummy_acct[prop] == user_row[prop]
    delete_account(dummy_acct["username"])


def test_post_errors():
    dummy_acct = acct_base.copy()
    dummy_acct["extra_field"] = "extra"
    output, ret_code = accounts.post(data=dummy_acct)
    # Ensure no extra unnecessary field
    assert (output, ret_code) == ("Invalid field supplied or missing a compulsory field", 400)
    dummy_acct.pop("extra_field")
    for prop in accounts.required:
        tmp = dummy_acct.pop(prop)
        output, ret_code = accounts.post(data=dummy_acct)
        # Required field missing
        assert (output, ret_code) == ("Invalid field supplied or missing a compulsory field", 400)
        dummy_acct[prop] = ""
        output, ret_code = accounts.post(data=dummy_acct)
        # Required field present but empty
        assert (output, ret_code) == ("Invalid field supplied or missing a compulsory field", 400)
        dummy_acct[prop] = tmp
    dummy_acct["password"] = "invalid password"
    output, ret_code = accounts.post(data=dummy_acct)
    assert (output, ret_code) == ("Invalid password hash", 400)
    dummy_acct["password"] = acct_base["password"]
    non_duplicates = ["username", "title"]
    for prop in non_duplicates:
        value = cur.execute("SELECT * FROM user").fetchone()[prop]
        tmp = dummy_acct[prop]
        dummy_acct[prop] = value
        output, ret_code = accounts.post(data=dummy_acct)
        # username or title taken
        assert (output, ret_code) == ("Username or title already taken", 400)
        dummy_acct[prop] = tmp


def test_delete_account():
    insert_account(acct_values)
    output, ret_code = accounts.delete(username=acct_base["username"])
    assert ret_code == 200
    assert get_account(acct_base["username"]) == None


def test_delete_invalid_username():
    user, ret_code = accounts.delete("invalid_username_" + str(time()))
    assert ret_code == 404


def test_put_account():
    dummy_acct = acct_base.copy()
    insert_account((dummy_acct["username"], "somepwdhash", "{}", "Mutable Test", "TBD", "accts@te.st"))
    output, ret_code = accounts.put(data=dummy_acct)
    assert ret_code == 200
    user_row = get_account(dummy_acct["username"])
    dummy_acct.pop("password")
    for prop in dummy_acct:
        assert dummy_acct[prop] == user_row[prop]
    delete_account(dummy_acct["username"])


def test_put_errors():
    dummy_acct = acct_base.copy()
    insert_account((dummy_acct["username"], "somepwdhash", "{}", "Mutable Test", "TBD", "accts@te.st"))
    dummy_acct["extra_field"] = "extra"
    output, ret_code = accounts.put(data=dummy_acct)
    assert (output, ret_code) == ("Invalid field supplied", 400)
    dummy_acct.pop("extra_field")
    for prop in accounts.required & dummy_acct.keys():
        tmp = dummy_acct.pop(prop)
        dummy_acct[prop] = ""
        output, ret_code = accounts.put(data=dummy_acct)
        # Required field present but empty
        assert (output, ret_code) == ("Invalid field supplied", 400)
        dummy_acct[prop] = tmp
    dummy_acct["username"] = "invalid_username_" + str(time())
    output, ret_code = accounts.put(data=dummy_acct)
    # Test can't edit non-existing user
    assert (output, ret_code) == ("Invalid username", 404)
    dummy_acct["username"] = acct_base["username"]
    dummy_acct["password"] = "invalid password"
    output, ret_code = accounts.put(data=dummy_acct)
    assert (output, ret_code) == ("Invalid password hash", 400)
    dummy_acct["password"] = acct_base["password"]
    title = cur.execute("SELECT * FROM user").fetchone()["title"]
    dummy_acct["title"] = title
    output, ret_code = accounts.put(data=dummy_acct)
    assert (output, ret_code) == ("Duplicate title supplied", 400)
    delete_account(dummy_acct["username"])


def test_manage_account():
    dummy_acct = acct_base.copy()
    old_props = (dummy_acct["username"], "somepwdhash", "{}", "Mutable Test", "TBD", "accts@te.st")
    insert_account(old_props)
    output, ret_code = accounts.manage(data=dummy_acct)
    assert ret_code == 200
    dummy_acct.pop("password")
    user_row = get_account(dummy_acct["username"])
    # Ensure permissions cannot be changed
    assert old_props[2] == user_row["permissions"]
    for prop in dummy_acct:
        assert dummy_acct[prop] == user_row[prop]
    delete_account(dummy_acct["username"])


def test_manage_errors():
    dummy_acct = acct_base.copy()
    insert_account((dummy_acct["username"], "somepwdhash", "{}", "Mutable Test", "TBD", "accts@te.st"))
    dummy_acct["extra_field"] = "extra"
    output, ret_code = accounts.manage(data=dummy_acct)
    assert (output, ret_code) == ("Invalid field supplied", 400)
    dummy_acct.pop("extra_field")
    for prop in (accounts.required - {"permissions"}) & dummy_acct.keys():
        tmp = dummy_acct.pop(prop)
        dummy_acct[prop] = ""
        output, ret_code = accounts.manage(data=dummy_acct)
        # Required field present but empty
        assert (output, ret_code) == ("Invalid field supplied", 400)
        dummy_acct[prop] = tmp
    dummy_acct["username"] = "invalid_username_" + str(time())
    output, ret_code = accounts.manage(data=dummy_acct)
    # Test can't edit non-existing user
    assert (output, ret_code) == ("Invalid username", 404)
    dummy_acct["username"] = acct_base["username"]
    dummy_acct["password"] = "invalid password"
    output, ret_code = accounts.manage(data=dummy_acct)
    assert (output, ret_code) == ("Invalid password hash", 400)
    dummy_acct["password"] = acct_base["password"]
    title = cur.execute("SELECT * FROM user").fetchone()["title"]
    dummy_acct["title"] = title
    output, ret_code = accounts.manage(data=dummy_acct)
    assert (output, ret_code) == ("Duplicate title supplied", 400)
    delete_account(dummy_acct["username"])
