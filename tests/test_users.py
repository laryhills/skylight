from sms import config
from sms.src import users
from itsdangerous import JSONWebSignatureSerializer as Serializer

username = "ucheigbeka"
password = "testing"
title = "Developer-1"
serializer = Serializer("testing serializer")
token = 'eyJhbGciOiJIUzUxMiJ9.InVzZXJuYW1lOnBhc3N3b3JkIg.eWAbWpuTFWsNxW42iuK9XehuwAHrLlNoKYNRq0YcZp7Zajprzuekowt24yIecGZi-XhF2ZLH8jbIWGo30tZPXQ'

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


def test_session_key():
    assert config.app.config['SECRET_KEY'] == users.session_key()


def test_hash_key():
    assert users.hash_key("3l33t h4x3r5") == "PFncBI6IUCQ76AeaXHTQeQ"


def test_tokenize():
    assert token == users.tokenize("username:password", s=serializer)


def test_detokenize():
    assert users.detokenize("invalid token", s=serializer) == None
    assert users.detokenize(token, parse=False, s=serializer) == "username:password"
    assert users.detokenize(token, s=serializer) == {'username': 'username', 'password': 'password'}

# Continue from testlogs
