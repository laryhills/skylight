from sms.config import db, get_current_session
from sms.models.courses import CoursesSchema
from sms.users import access_decorator, load_session

# TODO Create endpoint for teaching departments
# TODO Change primary key of all courses models from it's course_code to an id
#      As it stands, a course's code can't be modified


def get(course_code, retJSON=True):
    level = int(course_code[3]) if course_code[:3] != 'CED' else 4
    exec('from sms.models.courses import Courses{} as Courses'.format(level * 100))
    course = eval('Courses').query.filter_by(course_code=course_code).first_or_404()
    if retJSON:
        return CoursesSchema().dumps(course)
    return CoursesSchema().dump(course)


def get_course_details(course_code=None, level=None, use_curr_session=True):
    if course_code:
        return get_by_course_code(course_code)
    else:
        return get_all(level, use_curr_session=use_curr_session)


def get_by_course_code(course_code):
    return [get(course_code, retJSON=False)], 200


def get_all(level, use_curr_session=True):
    if use_curr_session:
        # curr_session = get_current_session()
        curr_session = 2018     #todo: Change this when 2019 session data is available
        model = load_session('{}_{}'.format(curr_session, curr_session + 1))
        course_codes = model.Courses.query.filter_by(mode_of_entry=1).first()
        level_courses = model.CoursesSchema().dump(course_codes)['level' + str(level)]
        courses = []
        for course_code in level_courses.replace(' ', ',').split(','):
            courses.append(get(course_code, retJSON=False))
        return courses, 200
    else:
        exec('from sms.models.courses import Courses{} as Courses'.format(level))
        courses = eval('Courses').query.all()
        return CoursesSchema(many=True).dump(courses), 200


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
