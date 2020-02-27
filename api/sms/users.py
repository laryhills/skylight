from flask import abort
from time import localtime
from sms.models.user import User
from sms.config import app, bcrypt, add_token, get_token, tokens
from base64 import b64encode
from hashlib import md5

from itsdangerous import JSONWebSignatureSerializer as Serializer


def login(token):
    try:
        user = detokenize(token)
        stored_user = User.query.filter_by(username=user['username']).first()
        if bcrypt.check_password_hash(stored_user.password, user['password']):
            token_dict = {'token': token}
            add_token(token, user['username'])
            return token_dict, 200
        abort(400)
    except Exception:
        abort(400)


def tokenize(text):
    # Use on client side, this is just for testing
    s = Serializer(hash_key())
    return s.dumps(text).decode('utf-8')


def detokenize(token):
    s = Serializer(hash_key())
    return dict(zip(*[("username","password"),s.loads(token).split(':')]))


def session_key():
    # TODO expose this on swagger to be called by client on login
    return app.config['SECRET_KEY']


def hash_key():
    session_key_sum = str(sum([int(x) for x in session_key() if x in "0123456789"]))
    session_bytes = bytes(session_key_sum, "utf-8")
    return b64encode(md5(session_bytes).digest()).decode("utf-8").strip("=")

