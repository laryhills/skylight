from sms.config import db, ma


class Courses(db.Model):
    __bind_key__ = 'courses'
    __tablename__ = 'Courses100'
    course_code = db.Column('COURSE_CODE', db.String(6), primary_key=True)
    course_title = db.Column('COURSE_TITLE', db.String(80))
    course_credit = db.Column('COURSE_CREDIT', db.Integer)
    course_semester = db.Column('COURSE_SEMESTER', db.Integer)
    course_level = db.Column('COURSE_LEVEL', db.Integer)
    teaching_dept = db.Column('TEACHING_DEPARTMENT', db.String(3))
    start_date = db.Column('START_DATE', db.Integer)
    end_date = db.Column('END_DATE', db.Integer)
    options = db.Column('OPTIONS', db.Integer)
    active = db.Column('OPTIONS', db.Integer)


class Options(db.Model):
    __bind_key__ = 'courses'
    __tablename__ = 'Options'
    options_group = db.Column('OPTIONS_GROUP', db.Integer, primary_key=True)
    members = db.Column('MEMBERS', db.Text)
    default_member = db.Column('DEFAULT_MEMBER', db.Text)


class CoursesSchema(ma.ModelSchema):
    class Meta:
        model = Courses
        sqla_session = db.session


class OptionsSchema(ma.ModelSchema):
    class Meta:
        model = Options
        sqla_session = db.session
