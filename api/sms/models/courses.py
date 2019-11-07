from sms.config import db, ma


class Courses(db.Model):
    __bind_key__ = 'courses'
    __tablename__ = 'Course100'
    course_code = db.Column('COURSE_CODE', db.String(6))
    course_title = db.Column('COURSE_TITLE', db.String(80))
    course_credit = db.Column('COURSE_CREDIT', db.Integer)
    course_semester = db.Column('COURSE_SEMESTER', db.Integer)
    course_level = db.Column('COURSE_LEVEL', db.Integer)
    teaching_dept = db.Column('TEACHING_DEPARTMENT', db.String(3))


class CoursesSchema(ma.ModelSchema):
    class Meta:
        model = Courses
        sqla_session = db.session
