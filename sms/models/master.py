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
    group = db.Column(db.String(40), nullable=False)
    description = db.Column(db.String(100), nullable=False)
    text = db.Column(db.String(500))
    headers = db.Column(db.String(100))
    sizes = db.Column(db.String(100))


class Category500(db.Model):
    __bind_key__ = 'master'
    __tablename__ = 'Category500'
    category = db.Column(db.String(1), primary_key=True)
    group = db.Column(db.String(40), nullable=False)
    description = db.Column(db.String(100), nullable=False)
    text = db.Column(db.String(500))
    headers = db.Column(db.String(100))
    sizes = db.Column(db.String(100))


class Props(db.Model):
    __bind_key__ = 'master'
    __tablename__ = 'Props'
    key = db.Column(db.Text, primary_key=True)
    value = db.Column(db.Text)


class MasterSchema(ma.ModelSchema):
    class Meta:
        model = Master
        sqla_session = db.session
