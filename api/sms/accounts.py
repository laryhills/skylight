from sms.config import db, bcrypt
from sms.users import access_decorator, accounts_decorator
from sms.models.user import User, UserSchema


@accounts_decorator
def get():
    all_users = User.query.all()
    user_schema = UserSchema(many=True)
    accounts = []
    for user in user_schema.dump(all_users):
        accounts.append(user)
    return accounts, 200


@accounts_decorator
def post(data):
    # TODO not recv this in plain-text
    password = data.pop('password')
    user_schema = UserSchema()
    new_user = user_schema.load(data)
    new_user.password = bcrypt.generate_password_hash(password)
    db.session.add(new_user)
    db.session.commit()
    return None, 200


@accounts_decorator
def put(data):
    username, password = data["username"], data["password"]
    # TODO not recv password in plain text, do decode here
    data['password'] = bcrypt.generate_password_hash(password)
    User.query.filter_by(username=username).update(data)
    db.session.commit()
    return None, 200


@accounts_decorator
def manage(data):
    username, password = data["username"], data["password"]
    # TODO not recv password in plain text, do decode here
    data['password'] = bcrypt.generate_password_hash(password)
    if "permissions" in data:
        data.pop("permissions")
    User.query.filter_by(username=username).update(data)
    db.session.commit()
    return None, 200


@accounts_decorator
def delete(username):
    user = User.query.filter_by(username=username).first()
    db.session.delete(user)
    db.session.commit()
    return None, 200
