from sms import config
from sms.src import users

username = "ucheigbeka"
password = "testing"
title = "Developer-1"

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
