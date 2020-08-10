from sms.config import db
from sms.src.users import accounts_decorator, detokenize
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
        user.pop("password", None)
        accounts.append(user)
    if username and not user:
        return "Invalid username", 404
    return accounts, 200


@accounts_decorator
def post(data):
    if not all([data.get(prop) for prop in required]) or (data.keys() - all_fields):
        # Empty value supplied or Invalid field supplied or Missing field present
        return "Invalid field supplied or missing a compulsory field", 400
    if not detokenize(data["password"], parse=False):
        return "Invalid password hash", 400
    if User.query.filter(
        (User.username == data["username"]) | (User.title == data["title"])
    ).first():
        # username or title already taken
        return "Username or title already taken", 400
    new_user = UserSchema().load(data)
    db.session.add(new_user)
    db.session.commit()
    return None, 200


@accounts_decorator
def put(data):
    if not all([data.get(prop) for prop in (required & data.keys())]) or (data.keys() - all_fields):
        # Empty value supplied or Invalid field supplied
        return "Invalid field supplied", 400
    username, password = data.get("username"), data.get("password")
    # TODO not recv password in plain text, do decode here
    if not User.query.filter_by(username=username).first():
        return "Invalid username", 404
    if password and not detokenize(data["password"], parse=False):
        return "Invalid password hash", 400
    if "title" in data:
        user = User.query.filter_by(title=data["title"]).first()
        if user and user.username != username:
            return "Duplicate title supplied", 400
    User.query.filter_by(username=username).update(data)
    db.session.commit()
    return None, 200


@accounts_decorator
def manage(data):
    if "permissions" in data:
        data.pop("permissions")
    if not all([data.get(prop) for prop in (required & data.keys())]) or (data.keys() - all_fields):
        # Empty value supplied or Invalid field supplied
        return "Invalid field supplied", 400
    username, password = data.get("username"), data.get("password")
    # TODO not recv password in plain text, do decode here
    if not User.query.filter_by(username=username).first():
        return "Invalid username", 404
    if password and not detokenize(data["password"], parse=False):
        return "Invalid password hash", 400
    if "title" in data:
        user = User.query.filter_by(title=data["title"]).first()
        if user and user.username != username:
            return "Duplicate title supplied", 400
    User.query.filter_by(username=username).update(data)
    db.session.commit()
    return None, 200


@accounts_decorator
def delete(username):
    user = User.query.filter_by(username=username).first()
    if not user:
        return "Invalid username", 404
    db.session.delete(user)
    db.session.commit()
    return None, 200
