from sms.config import db, ma


class Master(db.Model):
    __bind_key__ = 'master'
    __tablename__ = 'Main'
    mat_no = db.Column('MATNO', db.String(10), primary_key=True)
    database = db.Column('DATABASE', db.String(12), nullable=False)

class MasterSchema(ma.ModelSchema):
    class Meta:
        model = Master
        sqla_session = db.session
