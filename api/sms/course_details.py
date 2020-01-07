from sms.config import db
from sms.models.courses import CoursesSchema

Courses = None


def get(course_code):
    global Courses
    level = int(course_code[3]) if course_code[:3] != 'CED' else 4
    exec('from sms.models.courses import Courses{} as Courses'.format(level * 100))
    Courses = locals()['Courses']
    course = Courses.query.filter_by(course_code=course_code).first_or_404()
    course_schema = CoursesSchema()

    return course_schema.dumps(course)


def post(course):
    course_schema = CoursesSchema()
    course = course_schema.load(course)
    db.session.add(course)
    db.session.commit()
