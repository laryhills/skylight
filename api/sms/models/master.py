from sms.config import db, ma


class Master(db.Model):
    __bind_key__ = 'master'
    __tablename__ = 'Main'
    mat_no = db.Column('MATNO', db.String(10), primary_key=True)
    database = db.Column('DATABASE', db.String(12), nullable=False)


class Category(db.Model):
    __bind_key__ = 'master'
    __tablename__ = 'Category'
    category = db.Column(db.String(1), primary_key=True)
    description = db.Column(db.String(100), nullable=False)
    text = db.Column(db.String(500))
    headers = db.Column(db.String(100))
    sizes = db.Column(db.String(100))


class MasterSchema(ma.ModelSchema):
    class Meta:
        model = Master
        sqla_session = db.session
