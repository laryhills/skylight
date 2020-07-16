import sqlite3
from sms import accounts
from random import sample
from sms import config

conn = sqlite3.connect("sms/database/accounts.db")
conn.row_factory=sqlite3.Row
cur=conn.cursor()
perms = {"read": True, "write": True, "superuser": True, "levels": [100, 200, 300, 600], "usernames": ["accounts_test"]}
config.add_token("TESTING_token", "accounts_test", perms)

def test_get_all_accounts():
    user_list, ret_code = accounts.get()
    assert ret_code == 200
    user_count = len(cur.execute("SELECT username FROM user").fetchall())
    assert user_count == len(user_list)
    for user in user_list:
        username = user["username"]
        user_row = cur.execute("SELECT * FROM user WHERE username=?",(username,)).fetchone()
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


def test_post_new_account():
    dummy_acct = {
            'email': 'test@dummy.com',
            'permissions': '{"read": false, "write": false, "superuser": false, "levels": [], "usernames": []}',
            'fullname': 'Skylight Testing',
            'title': 'Tester',
            'password': 'testing',
            'username': 'post_test',
    }
    output, ret_code = accounts.post(data=dummy_acct)
    assert ret_code == 200
    user_row = cur.execute("SELECT * FROM user WHERE username=?",(dummy_acct["username"],)).fetchone()
    for prop in dummy_acct:
        assert dummy_acct[prop] == user_row[prop]
    cur.execute("DELETE FROM user WHERE username=?",(dummy_acct["username"],))
    conn.commit()


def test_delete_account():
    cur.execute("INSERT INTO user VALUES(?,?,?,?,?,?)",("delete_test", "somepwdhash", "{}", "Deletion Test", "Dell Ette", "del@e.te"))
    conn.commit()
    output, ret_code = accounts.delete(username="delete_test")
    assert ret_code == 200
    assert cur.execute("SELECT * FROM user WHERE username=?",("delete_test",)).fetchone() == None


def test_put_account():
    dummy_acct = {
            'email': 'test@dummy.com',
            'permissions': '{"read": false, "write": false, "superuser": false, "levels": [], "usernames": []}',
            'fullname': 'Skylight Testing',
            'title': 'Tester',
            'password': 'testing',
            'username': 'put_test',
    }
    cur.execute("INSERT INTO user VALUES(?,?,?,?,?,?)",(dummy_acct["username"], "somepwdhash", "{}", "Put Test", "Putin Vlad", "vlad@put.in"))
    conn.commit()
    output, ret_code = accounts.put(data=dummy_acct)
    assert ret_code == 200
    user_row = cur.execute("SELECT * FROM user WHERE username=?",(dummy_acct["username"],)).fetchone()
    dummy_acct.pop("password")
    for prop in dummy_acct:
        assert dummy_acct[prop] == user_row[prop]
    cur.execute("DELETE FROM user WHERE username=?",(dummy_acct["username"],))
    conn.commit()


def test_manage_account():
    dummy_acct = {
            'email': 'test@dummy.com',
            'permissions': '{"read": false, "write": false, "superuser": false, "levels": [], "usernames": []}',
            'fullname': 'Skylight Testing',
            'title': 'Tester',
            'password': 'testing',
            'username': 'manage_test',
    }
    cur.execute("INSERT INTO user VALUES(?,?,?,?,?,?)",(dummy_acct["username"], "somepwdhash", "{}", "Manage Test", "Mana Ger", "Mana@g.er"))
    conn.commit()
    output, ret_code = accounts.manage(data=dummy_acct)
    assert ret_code == 200
    user_row = cur.execute("SELECT * FROM user WHERE username=?",(dummy_acct["username"],)).fetchone()
    dummy_acct.pop("password")
    for prop in dummy_acct:
        if prop != "permissions":
            assert dummy_acct[prop] == user_row[prop]
        else:
            assert user_row[prop] == "{}"
    cur.execute("DELETE FROM user WHERE username=?",(dummy_acct["username"],))
    conn.commit()
