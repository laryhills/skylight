"""
    Utility script much like utils.py for handling frequently called or single use simple utility functions
"""

from pprint import pprint
from sms.utils import load_session, get_carryovers, get_depat, get_credits, get_gpa_credits
from sms.models.master import Category, Category500

class_mapping = {
    '1': 'First class honours',
    '2.1': 'Second class honours (upper)',
    '2.2': 'Second class honours (lower)',
    '3': 'Third class honours',
    'pass': 'Pass',
    'fail': 'Fail'
}


def get_total_credits_registered(mat_no, level, session):
    course_reg_obj = eval('session.CourseReg{}'.format(level))


def total_credits_failed(mat_no, level, session):
    pass


def get_categories(final_year=False):
    cat_objs = Category500.query.all() if final_year else Category.query.all()
    categories = []
    for obj in cat_objs:
        categories.append(obj.category)

    return categories


def get_groups_cats():
    groups_cats = []
    for obj in Category500.query.all():
        groups_cats.append((obj.group, obj.category))

    return groups_cats


def get_cls_limits(cls, db_name=None, session=None):
    if not session:
        session = load_session(db_name)
    cls_obj = eval('session.DegreeClass')
    limits = cls_obj.query.filter_by(cls=class_mapping[cls]).first().limits
    return list(map(float, limits.split(',')))


def get_session_carryover_courses(mat_no, level, session):
    carryovers_credits = eval('session.Result{}'.format(level)).query.filter_by(mat_no=mat_no).first().carryovers
    carryovers_credits = carryovers_credits.split(',') if carryovers_credits else ['']
    carryovers = []
    if carryovers_credits[0]:
        for course_credits_grade in carryovers_credits:
            course, credit, grade = course_credits_grade.split()
            if grade == "F":
                carryovers.append(course)

    return carryovers


def get_student_details_for_cat(mat_no, level, session):
    """
    Gets the details of a student

    :param mat_no: mat number of student
    :param level:  level of student
    :param session: session model for student
    :return: dict containing the student details
    """
    student = session.PersonalInfo.query.filter_by(mat_no=mat_no).first()
    mod = student.mode_of_entry
    total_credits = getattr(session.Credits.query.filter_by(mode_of_entry=mod).first(), 'level{}'.format(level))
    gpa_credits = session.GPA_Credits.query.filter_by(mat_no=mat_no).first()
    if gpa_credits:
        gpa, credits_passed = getattr(gpa_credits, 'level{}'.format(level)).strip().split(',')
        gpa, credits_passed = float(gpa), int(credits_passed)
    else:
        gpa, credits_passed = None, 0
    credits_failed = total_credits - credits_passed
    name = student.othernames + ' ' + '<b>{}</b>'.format(student.surname)
    name += ' (Miss)' if student.sex == 'F' else ''
    # carryovers_dict = get_carryovers(mat_no, level=level, retJSON=False)
    # carryovers_credits = carryovers_dict['first_sem'] + carryovers_dict['second_sem']
    # carryovers = list(map(lambda x: x[0], carryovers_credits))
    carryovers = get_session_carryover_courses(mat_no, level, session)
    details = {
        'mat_no': student.mat_no,
        'name': name,
        'credits_passed': credits_passed,
        'credits_failed': credits_failed,
        'outstanding_courses': '  '.join(carryovers),
        'gpa': gpa
    }

    return details


def get_student_details_for_cls(mat_no, session):
    student = session.PersonalInfo.query.filter_by(mat_no=mat_no).first()
    name = student.othernames + ' ' + '<b>{}</b>'.format(student.surname)
    name += ' (Miss)' if student.sex == 'F' else ''

    details = {
        'mat_no': mat_no,
        'name': name,
        'subject_area': get_depat().capitalize()
    }

    return details


def get_details_for_ref_students(mat_no, session):
    student = session.PersonalInfo.query.filter_by(mat_no=mat_no).first()
    name = student.othernames + ' ' + '<b>{}</b>'.format(student.surname)
    name += ' (Miss)' if student.sex == 'F' else ''
    session_carryover_courses = get_session_carryover_courses(mat_no, 500, session)
    credits_passed_list = get_gpa_credits(mat_no, session)[1]
    total_credits_passed = sum(filter(lambda x: x, credits_passed_list))
    total_credits = sum(get_credits(mat_no, session=session))

    # KeyError for the utils.get_carryovers function
    # try:
    #     carryovers_dict = get_carryovers(mat_no, retJSON=False)
    # except KeyError as err:
    #     print(mat_no)
    #     raise KeyError(str(err))
    # carryovers_credits = carryovers_dict['first_sem'] + carryovers_dict['second_sem']
    # overall_carryover_courses = list(map(lambda x: x[0], carryovers_credits))
    # outstanding_courses = []
    # for course_code in overall_carryover_courses:
    #     if course_code not in session_carryover_courses:
    #         outstanding_courses.append(course_code)

    details = {
        'mat_no': mat_no,
        'name': name,
        'session_carryover_courses': '  '.join(session_carryover_courses),
        'cum_credits_to_date': total_credits_passed,
        'outstanding_credits': total_credits - total_credits_passed,
        'outstanding_courses': '' # ' '.join(outstanding_courses)
    }

    return details


def get_other_students_details(mat_no, session, group):
    student = session.PersonalInfo.query.filter_by(mat_no=mat_no).first()
    name = student.othernames + ' ' + '<b>{}</b>'.format(student.surname)
    name += ' (Miss)' if student.sex == 'F' else ''

    details = {
        'mat_no': mat_no,
        'name': name,
        'remark': ''
    }

    return details


def get_students_by_level(acad_session, retDB=False):
    """
    Gets all the mat numbers of students in a particular db

    This only includes the regular students that entered during the `acad_session` session, DE and probating students
    that somehow have ties to this db.

    :param acad_session: entry session
    :param retDB: if True, returns a dict
    :return: list of mat numbers if not `retDB` else a dictionary of db name being mapped to a list of mat numbers
    """
    db_name = '{}_{}'.format(acad_session, acad_session + 1)
    session = load_session(db_name)
    students = session.PersonalInfo.query.filter_by(is_symlink=0).all()
    if retDB:
        students = {db_name: list(map(lambda stud: stud.mat_no, students))}
    else:
        students = list(map(lambda stud: stud.mat_no, students))

    other_students = session.SymLink.query.all()    # DE and probating students
    if retDB:
        # groups the students by their database name
        stud_db_map = {}
        for stud in other_students:
            db_name = stud.database[:-3].replace('-', '_')
            try:
                stud_db_map[db_name].append(stud.mat_no)
            except KeyError:
                stud_db_map[db_name] = [stud.mat_no]
        students.update(stud_db_map)
    else:
        other_students = list(map(lambda stud: stud.mat_no, other_students))
        students.extend(other_students)

    return students


def filter_students_by_category(level, category, db_name, students):
    session = load_session(db_name)
    resObj = eval('session.Result{}'.format(level))
    studs, unreg_studs = [], []
    for mat_no in students:
        stud = resObj.query.filter_by(mat_no=mat_no).first()
        if stud:
            if stud.category == category:
                studs.append(mat_no)
        else:
            unreg_studs.append(mat_no)

    return studs


def get_students_by_category(level, acad_session, category=None, get_all=False):
    """
    Gets all students within a category

    If `get_all` is supplied, `category` is ignored

    :param level: level of students
    :param acad_session: entry session of students
    :param category: (Optional) category to fetch
    :param get_all: (Optional) if True return all categories of students
    :return: list of students if not `get_all` else dictionary of all category mapping to list of students
    """
    mat_no_dict = get_students_by_level(acad_session, retDB=True)
    if get_all:
        students = dict.fromkeys(mat_no_dict, {})
        categories = get_categories(final_year=(level == 500))
        for category in categories:
            for db_name in mat_no_dict.keys():
                filtered_studs = filter_students_by_category(level, category, db_name, mat_no_dict[db_name])
                if students[db_name]:
                    students[db_name][category] = filtered_studs
                else:
                    students[db_name] = {category: filtered_studs}
    else:
        students = dict.fromkeys(mat_no_dict)
        for db_name in mat_no_dict.keys():
            filtered_studs = filter_students_by_category(level, category, db_name, mat_no_dict[db_name])
            students[db_name] = filtered_studs

    return students


def get_students_details_by_category(level, acad_session, category=None, get_all=False):
    students = get_students_by_category(level, acad_session, category=category, get_all=get_all)
    categories = get_categories()
    if get_all:
        students_details = {}
        for db_name in students.keys():
            session = load_session(db_name)
            for category in categories:
                dets = list(map(lambda stud: get_student_details_for_cat(stud, level, session), students[db_name][category]))
                if students_details.get(category):
                    students_details[category].extend(dets)
                else:
                    students_details[category] = dets
    else:
        students_details = []
        for db_name in students:
            session = load_session(db_name)
            dets = list(map(lambda stud: get_student_details_for_cat(stud, level, session), students[db_name]))
            students_details.extend(dets)

    return students_details


def split_students_by_category(category_students):
    # TODO Create class for the categories

    category_mapping = dict(get_groups_cats())
    groups = category_mapping.keys()
    all_students = dict.fromkeys(groups, {})

    for db_name in category_students:
        for group in groups:
            studs = category_students[db_name][category_mapping[group]]
            if all_students.get(group):
                all_students[group][db_name] = studs
            else:
                all_students[group] = {db_name: studs}

    return all_students


def filter_students_by_degree_class(level, degree_class, db_name, students):
    session = load_session(db_name)
    limits = get_cls_limits(degree_class, session=session)
    cgpa_obj = eval('session.GPA_Credits')
    studs = []
    for stud in students:
        cgpa = cgpa_obj.query.filter_by(mat_no=stud).first().cgpa
        if limits[0] <= cgpa <= limits[1]:
            details = get_student_details_for_cls(stud, session)
            details['cgpa'] = cgpa
            studs.append(details)

    return studs


def get_final_year_students_by_category(acad_session, category=None, get_all=False):
    students_categories = get_students_by_category(500, acad_session, category=category, get_all=get_all)
    all_students_by_category = split_students_by_category(students_categories)
    if get_all:
        all_students = {}

        # Successful students
        successful_students = all_students_by_category.pop('successful students')
        students = {}
        classes = class_mapping.keys()
        for degree_class in classes:
            studs = []
            for db_name in successful_students:
                studs.extend(filter_students_by_degree_class(500, degree_class, db_name, successful_students[db_name]))
            students[degree_class] = studs
        all_students['successful students'] = students

        # Referred students
        referred_students = all_students_by_category.pop('carryover students')
        studs = []
        for db_name in referred_students:
            session = load_session(db_name)
            studs.extend(list(map(
                lambda mat_no: get_details_for_ref_students(mat_no, session), referred_students[db_name])))
        all_students['referred students'] = studs

        # Other students
        for group in all_students_by_category:
            studs, other_students = [], all_students_by_category[group]
            for db_name in other_students:
                session = load_session(db_name)
                studs.extend(list(map(
                    lambda mat_no: get_other_students_details(mat_no, session, group), other_students[db_name])))
            all_students[group] = studs

        return all_students
    # else:
    #     group = tuple(map(lambda x: x[0] == category, get_groups_cats()))[0]
    #     students_with_category = all_students_by_category[group]
    #     students = []
    #     classes = class_mapping.keys()
    #     if group == 'successful students':
    #         for db_name in students_with_category.keys():
    #             studs = filter_students_by_degree_class(500, degree_class, db_name, students_with_category[db_name])
    #             students.extend(studs)
    #     else:
    #         pass
    #
    #     return students
