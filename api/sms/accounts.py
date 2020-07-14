from sms.config import db, bcrypt
from sms.users import access_decorator, accounts_decorator
from sms.models.user import User, UserSchema


all_fields = {"username", "password", "permissions", "title", "fullname", "email"}
required = {"username", "password", "permissions", "title", "fullname", "email"}


@accounts_decorator
def get(username=None):
    accounts = []
    if username == None:
        users = User.query.all()
    else:
        users = [User.query.filter_by(username=username).first()]
    for user in UserSchema(many=True).dump(users):
        accounts.append(user)
    if username and not user:
        return accounts, 404
    return accounts, 200


@accounts_decorator
def post(data):
    if not all([data.get(prop) for prop in required]) or (data.keys() - all_fields):
        # Empty value supplied or Invalid field supplied or Missing field present
        return None, 400
    # TODO not recv this in plain-text
    hashed_password = bcrypt.generate_password_hash(data["password"]).decode("utf-8")
    data["password"] = hashed_password
    if User.query.filter(
        (User.username == data["username"]) | (User.title == data["title"])
    ).first():
        # username or title already taken
        return None, 400
    new_user = UserSchema().load(data)
    db.session.add(new_user)
    db.session.commit()
    return None, 200


@accounts_decorator
def put(data):
    if not all([data.get(prop) for prop in (required & data.keys())]) or (data.keys() - all_fields):
        # Empty value supplied or Invalid field supplied
        return None, 400
    username, password = data.get("username"), data.get("password")
    # TODO not recv password in plain text, do decode here
    if not User.query.filter_by(username=username).first():
        return None, 404
    if password:
        data["password"] = bcrypt.generate_password_hash(password).decode("utf-8")
    User.query.filter_by(username=username).update(data)
    try:
        db.session.commit()
    except:
        # Duplicate title
        return None, 400
    return None, 200


@accounts_decorator
def manage(data):
    if "permissions" in data:
        data.pop("permissions")
    if not all([data.get(prop) for prop in (required & data.keys())]) or (data.keys() - all_fields):
        # Empty value supplied or Invalid field supplied
        return None, 400
    username, password = data.get("username"), data.get("password")
    # TODO not recv password in plain text, do decode here
    if not User.query.filter_by(username=username).first():
        return None, 404
    if password:
        data["password"] = bcrypt.generate_password_hash(password).decode("utf-8")
    User.query.filter_by(username=username).update(data)
    try:
        db.session.commit()
    except:
        # Duplicate title
        return None, 400
    return None, 200


@accounts_decorator
def delete(username):
    user = User.query.filter_by(username=username).first()
    if not user:
        return None, 404
    db.session.delete(user)
    db.session.commit()
    return None, 200
