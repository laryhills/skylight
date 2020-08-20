from json import dumps
from sms.config import db
from sms.src.users import access_decorator, load_session
from sms.models.courses import Courses, CoursesSchema
from sms.config import get_current_session

# TODO Create endpoint for teaching departments
# TODO Change primary key of all courses models from it's course_code to an id
#      As it stands, a course's code can't be modified


def get(course_code):
    course = Courses.query.filter_by(course_code=course_code).first()
    return CoursesSchema().dump(course)


def get_course_details(course_code=None, level=None, use_curr_session=True):
    if course_code:
        return [dumps(get(course_code))], 200
    else:
        return get_all(level, use_curr_session=use_curr_session), 200


def get_all(level, use_curr_session=True):
    courses = Courses.query
    if level:
        courses = courses.filter_by(course_level=level)
    if use_curr_session:
        courses = courses.filter_by(active=1)
    return CoursesSchema(many=True).dump(courses.all())


@access_decorator
def post(course):
    course_level = course['course_level']
    exec('from sms.models.courses import Courses{} as Courses'.format(course_level))
    model = eval('Courses')
    course_obj = model(**course)
    db.session.add(course_obj)
    db.session.commit()


@access_decorator
def put(data):
    error_log = []
    for course in data:
        course_level = course['course_level']
        exec('from sms.models.courses import Courses{} as Courses'.format(course_level))
        course_obj = eval('Courses').query.filter_by(course_code=course['course_code']).first()
        if not course_obj:
            msg = course['course_code'] + ' not found'
            error_log.append(msg)
            continue
        for k, v in course.items():
            setattr(course_obj, k, v)
        db.session.add(course_obj)
    db.session.commit()
    return error_log, 200


@access_decorator
def delete(course_code, course_level):
    exec('from sms.models.courses import Courses{} as Courses'.format(course_level))
    course_obj = eval('Courses').query.filter_by(course_code=course_code).first_or_404()
    db.session.delete(course_obj)
    db.session.commit()
