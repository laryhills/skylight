from sms.config import db, ma


class Courses(db.Model):
    __bind_key__ = 'courses'
    __tablename__ = 'Courses'
    code = db.Column('COURSE_CODE', db.String(6), primary_key=True)
    title = db.Column('COURSE_TITLE', db.String(80))
    credit = db.Column('COURSE_CREDIT', db.Integer)
    semester = db.Column('COURSE_SEMESTER', db.Integer)
    level = db.Column('COURSE_LEVEL', db.Integer)
    teaching_dept = db.Column('TEACHING_DEPT', db.String(3))
    start_date = db.Column('START_DATE', db.Integer)
    end_date = db.Column('END_DATE', db.Integer)
    options = db.Column('OPTIONS', db.Integer)
    active = db.Column('ACTIVE', db.Integer)


class CoursesSchema(ma.ModelSchema):
    class Meta:
        model = Courses
        sqla_session = db.session
