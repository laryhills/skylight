from flask import abort
from sms.models.user import User
from sms.config import app, bcrypt

from itsdangerous import JSONWebSignatureSerializer as Serializer


def login(user):
    stored_user = User.query.filter_by(username=user['username']).first()
    if stored_user and bcrypt.check_password_hash(stored_user.password, user['password']):
        s = Serializer(app.config['SECRET_KEY'])
        token = {'token': s.dumps(stored_user.user_id).decode('utf-8')}
        return token, 200
    abort(400)

