from sms.config import db, ma


class Logs(db.Model):
    __bind_key__ = 'logs'
    __tablename__ = 'Logs'
    user = db.Column('USER', db.Text, nullable=False, primary_key=True)
    operation = db.Column('OPERATION', db.Text, nullable=False)
    params = db.Column('PARAMS', db.Text, nullable=True)
    timestamp = db.Column('TIMESTAMP', db.Integer, nullable=False)


class LogsSchema(ma.ModelSchema):
    class Meta:
        model = Logs
        sqla_session = db.session
