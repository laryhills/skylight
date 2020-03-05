from sms.config import db
from sms.models.courses import CoursesSchema
from sms.users import access_decorator


def get(course_code, retJSON=True):
    level = int(course_code[3]) if course_code[:3] != 'CED' else 4
    exec('from sms.models.courses import Courses{} as Courses'.format(level * 100))
    course = eval('Courses').query.filter_by(course_code=course_code).first_or_404()
    if retJSON:
        return CoursesSchema().dumps(course)
    return CoursesSchema().dump(course)


@access_decorator
def post(course):
    course_schema = CoursesSchema()
    course = course_schema.load(course)
    db.session.add(course)
    db.session.commit()
