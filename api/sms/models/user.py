from sms.config import db, ma


class User(db.Model):
    user_id = db.Column(db.Integer, primary_key=True, nullable=False)
    firstname = db.Column(db.String(90), unique=False, nullable=False)
    lastname = db.Column(db.String(90), unique=False, nullable=False)
    email = db.Column(db.String(90), nullable=False)
    username = db.Column(db.String(32), unique=True, nullable=False)
    password = db.Column(db.String(80), nullable=False)
    permissions = db.Column(db.Text, nullable=False)


class UserSchema(ma.ModelSchema):
    class Meta:
        model = User
        exclude = ('password',)
        sqla_session = db.session
