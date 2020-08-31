import os
import sqlite3
from time import time
from json import dumps
from sms import config
from tests import db_path
from sms.src import users
from sms.src import personal_info
from itsdangerous import JSONWebSignatureSerializer as Serializer

username = "ucheigbeka"
password = "testing"
title = "Developer-1"
serializer = Serializer("testing serializer")
token = 'eyJhbGciOiJIUzUxMiJ9.InVzZXJuYW1lOnBhc3N3b3JkIg.eWAbWpuTFWsNxW42iuK9XehuwAHrLlNoKYNRq0YcZp7Zajprzuekowt24yIecGZi-XhF2ZLH8jbIWGo30tZPXQ'

conn = sqlite3.connect(os.path.join(db_path, "logs.db"))
conn.row_factory=sqlite3.Row
cur=conn.cursor()

# TODO add test get_level

def test_setup_env():
    config.add_token("TESTING_token", "users_test", {})

def get_log(user):
    return cur.execute("SELECT * FROM Logs WHERE user=?",(user,)).fetchall()[-1]


def delete_log(user):
    cur.execute("DELETE FROM Logs WHERE user=?",(user,))
    conn.commit()


def test_login():
    creds = "{}:{}".format(username, password)
    my_token = {'token': users.tokenize(creds)}
    output, ret_code = users.login(my_token)
    my_token["title"] = title
    assert (output, ret_code) == (my_token, 200)


def test_login_errors():
    # Attempt wrong username
    creds = "inv{}:{}".format(username, password)
    my_token = {'token': users.tokenize(creds)}
    output, ret_code = users.login(my_token)
    assert (output, ret_code) == (None, 401)
    # Attempt wrong password
    creds = "{}:inv{}".format(username, password)
    my_token = {'token': users.tokenize(creds)}
    output, ret_code = users.login(my_token)
    assert (output, ret_code) == (None, 401)
    # Attempt invalid token
    my_token = {'token': "invalid token"}
    output, ret_code = users.login(my_token)
    assert (output, ret_code) == (None, 401)


def test_logout():
    output, ret_code = users.logout({"token":token})
    assert (output, ret_code) == (None, 200)


def test_session_key():
    assert config.app.config['SECRET_KEY'] == users.session_key()


def test_hash_key():
    assert users.hash_key("3l33t h4x3r5") == "PFncBI6IUCQ76AeaXHTQeQ"


def test_tokenize():
    assert token == users.tokenize("username:password", s=serializer)


def test_detokenize():
    # Invalid token
    assert users.detokenize("invalid token", s=serializer) == None
    # Valid token, no parse
    assert users.detokenize(token, parse=False, s=serializer) == "username:password"
    # Valid token, parse to dict
    assert users.detokenize(token, s=serializer) == {'username': 'username', 'password': 'password'}


def test_log():
    curr_time = int(time())
    users.log("user_testing", "personal_info.get_exp", personal_info.get_exp, (), {"mat_no": "ENG1503000"})
    log_entry = get_log("user_testing")
    assert log_entry["USER"] == "user_testing"
    assert log_entry["OPERATION"] == "personal_info.get_exp"
    assert log_entry["PARAMS"] == dumps({"mat_no": "ENG1503000"})
    assert (log_entry["TIMESTAMP"] - curr_time) <= 2
    delete_log("user_testing")


def test_load_session():
    session = users.load_session("2015_2016")
    assert session.__file__ == db_path.replace("database", "models/_2015_2016.py")


def test_get_DB():
    assert users.get_DB("ENGTESTING") == None
    assert users.get_DB("ENG1604235") == '2016_2017'


def test_dict_render():
    output = users.dict_render({1:{2:{3:4},5:6},7:8})
    expected = "1 => \n    2 => \n        3 => 4\n    5 => 6\n7 => 8"
    assert output == expected


def test_get_kwargs():
    my_fn = lambda x, y : x*y
    params = users.get_kwargs(my_fn, (1,2), {})
    assert params == {'x': 1, 'y': 2}
    params = users.get_kwargs(my_fn, (), {"x": 1, "y": 2})
    assert params == {'x': 1, 'y': 2}
