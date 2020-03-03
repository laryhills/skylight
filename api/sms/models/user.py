from sms.config import db


class User(db.Model):
    user_id = db.Column(db.Integer, primary_key=True, nullable=False)
    username = db.Column(db.String(32), unique=True, nullable=False)
    password = db.Column(db.String(80), nullable=False)
    permissions = db.Column(db.Text, nullable=False)
