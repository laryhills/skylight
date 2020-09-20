from sms.config import db
from sms.src.users import access_decorator
from sms.models.courses import Courses, CoursesSchema


def get(course_code):
    course = Courses.query.filter_by(course_code=course_code).first()
    return CoursesSchema().dump(course)


def get_options(group=None):
    groups, options = [], [{group}, set([x.options for x in Courses.query.all()])][group == None]
    for opt in options - {0}:
        option = {"members": [c.course_code for c in Courses.query.filter_by(options=opt).all()]}
        if option["members"]:
            course = get(option["members"][0])
            option.update((("group", opt), ("level", course["course_level"]), ("semester", course["course_semester"])))
            groups.append(option)
    return groups[0] if group != None and len(groups) else groups


def get_all(level=None, options=True, inactive=False):
    courses = Courses.query
    if level:
        courses = courses.filter_by(course_level=level)
    if not inactive:
        courses = courses.filter_by(active=1)
    if options:
        course_list = courses.all()
    else:
        course_list = courses.filter_by(options=0).all()
        for option_group in [x["group"] for x in get_options()]:
            option_member = courses.filter_by(options=option_group).first()
            if option_member:
                course_list += [option_member]
    return CoursesSchema(many=True).dump(course_list)


def get_course_details(course_code=None, level=None, options=True, inactive=False):
    if course_code:
        output = get(course_code)
        if not output:
            return None, 404
        output = [output]
    else:
        output = get_all(level, options, inactive)
    return output, 200


@access_decorator
def post(course):
    if Courses.query.filter_by(course_code=course["course_code"]).first():
        return "Course already exists", 400
    course_obj = Courses(**course)
    db.session.add(course_obj)
    db.session.commit()
    return None, 200


@access_decorator
def patch(data):
    courses = [Courses.query.filter_by(course_code=course["course_code"]).first() for course in data]
    if all(courses):
        for course, course_obj in zip(data, courses):
            for k, v in course.items():
                setattr(course_obj, k, v)
            db.session.add(course_obj)
        db.session.commit()
        return None, 200
    return None, 404


@access_decorator
def delete(course_code):
    course_obj = Courses.query.filter_by(course_code=course_code).first()
    if not course_obj:
        return None, 404
    db.session.delete(course_obj)
    db.session.commit()
    return None, 200
