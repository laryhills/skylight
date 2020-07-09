from sms.config import db, bcrypt
from sms.users import access_decorator
from sms.models.user import User, UserSchema

'''
perm_title = {
    '{"read": true, "write": true, "superuser": true, "levels": [100, 200, 300, 400, 500, 600]}': 'Head of department',
    '{"read": true, "write": true, "superuser": false, "levels": [100, 200, 300, 400, 500, 600]}': 'Exam officer',
    '{"read": true, "write": true, "superuser": false, "levels": [100]}': '100 level course adviser',
    '{"read": true, "write": true, "superuser": false, "levels": [200]}': '200 level course adviser',
    '{"read": true, "write": true, "superuser": false, "levels": [300]}': '300 level course adviser',
    '{"read": true, "write": true, "superuser": false, "levels": [400]}': '400 level course adviser',
    '{"read": true, "write": true, "superuser": false, "levels": [500]}': '500 level course adviser',
    '{"read": true, "write": true, "superuser": false, "levels": [600]}': '500 level course adviser(2)',
    '{"read": true, "write": false, "superuser": false, "levels": [100, 200, 300, 400, 500, 600]}': 'Secretary',
}
'''


@access_decorator
def get():
    all_users = User.query.all()
    user_schema = UserSchema(many=True)
    accounts = []
    for user in user_schema.dump(all_users):
        accounts.append(user)
    return accounts, 200


@access_decorator
def post(data):
    title = data.pop('title')
    password = data.pop('password')
    data['permissions'] = [key for key, val in perm_title.items() if val == title][0]
    data['user_id'] = User.query.count() + 1
    user_schema = UserSchema()
    new_user = user_schema.load(data)
    new_user.password = bcrypt.generate_password_hash(password)
    db.session.add(new_user)
    db.session.commit()


@access_decorator
def put(data):
    uid = data['user_id']
    password = data['password']
    user = User.query.filter_by(user_id=uid).first()
    user.password = bcrypt.generate_password_hash(password)
    db.session.add(user)
    db.session.commit()


@access_decorator
def delete(uid):
    user = User.query.filter_by(user_id=uid).first()
    db.session.delete(user)
    db.session.commit()
