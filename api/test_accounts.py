import sqlite3
from sms import accounts
from random import sample

conn = sqlite3.connect("sms/database/accounts.db")
conn.row_factory=sqlite3.Row
cur=conn.cursor()

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
            'username': 'tester',
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
