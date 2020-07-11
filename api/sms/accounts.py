from sms.config import db, bcrypt
from sms.users import access_decorator, accounts_decorator
from sms.models.user import User, UserSchema


@accounts_decorator
def get(username=None):
    accounts = []
    if username == None:
        users = User.query.all()
    else:
        users = [User.query.filter_by(username=username).first()]
    for user in UserSchema(many=True).dump(users):
        accounts.append(user)
    return accounts, 200


@accounts_decorator
def post(data):
    # TODO not recv this in plain-text
    hashed_password = bcrypt.generate_password_hash(data["password"]).decode("utf-8")
    data["password"] = hashed_password
    new_user = UserSchema().load(data)
    db.session.add(new_user)
    try:
        db.session.commit()
    except:
        return None, 500
    return None, 200


@accounts_decorator
def put(data):
    username, password = data["username"], data["password"]
    # TODO not recv password in plain text, do decode here
    data['password'] = bcrypt.generate_password_hash(password)
    User.query.filter_by(username=username).update(data)
    try:
        db.session.commit()
    except:
        return None, 500
    return None, 200


@accounts_decorator
def manage(data):
    username, password = data["username"], data["password"]
    # TODO not recv password in plain text, do decode here
    data['password'] = bcrypt.generate_password_hash(password)
    if "permissions" in data:
        data.pop("permissions")
    User.query.filter_by(username=username).update(data)
    try:
        db.session.commit()
    except:
        return None, 500
    return None, 200


@accounts_decorator
def delete(username):
    user = User.query.filter_by(username=username).first()
    db.session.delete(user)
    try:
        db.session.commit()
    except:
        return None, 500
    return None, 200
