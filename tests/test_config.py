from time import time
from sms import config

my_token = ("testing_token", "test_acct", {})
token, user, perms = my_token


def test_get_invalid_token():
    assert config.get_token(str(time)) == None


def test_add_token():
    config.add_token(*my_token)
    assert token in config.tokens
    assert config.tokens[token].get("user") == user
    assert config.tokens[token].get("perms") == perms
    config.tokens.pop(token)


def test_get_token():
    config.tokens[token] = {"user": user, "perms": perms}
    recv_token = config.get_token(token)
    assert recv_token["user"] == user
    assert recv_token["perms"] == perms


def test_remove_token():
    config.tokens[token] = {"user": user, "perms": perms}
    assert token in config.tokens
    assert config.tokens[token] == config.remove_token(token)
    assert token not in config.tokens

# TODO add test for get_current_session
