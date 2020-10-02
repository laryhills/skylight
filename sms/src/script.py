"""
    Utility script much like utils.py for handling frequently called or single use simple utility functions
"""

from sms.config import get_current_session
from sms.src.users import get_level
from sms.src.utils import load_session, get_dept, get_credits, get_category, get_carryovers, \
    get_session_from_level, gpa_credits_poll
from sms.models.courses import Courses
from sms.models.master import Category, Category500
from sms.src.jobs import set_progress, set_increment, update_progress

class_mapping = {
    '1': 'First class honours',
    '2.1': 'Second class honours (upper)',
    '2.2': 'Second class honours (lower)',
    '3': 'Third class honours',
    'pass': 'Pass',
    'fail': 'Fail'
}

course_list = []


def populate_course_list(level):
    """
    Populates the global course_list variable with the courses offered by students in `level` level

    :param level: level in which the courses are offered
    :return: None
    """
    global course_list
    course_list = []

    level = 500 if level > 500 else level
    course_objs = Courses.query.filter_by(level=level).all()
    for obj in course_objs:
        course_list.append(obj.code)


def get_categories(final_year=False):
    """
    Retrieves the students categories from the database

    Returns the categories for final year students if `final_year` is
    True else the categories for non-graduating students

    :param final_year: if true returns the category for final year students
    :return: list of categories
    """
    cat_objs = Category500.query.all() if final_year else Category.query.all()
    categories = []
    for obj in cat_objs:
        categories.append(obj.category)

    return categories


def get_groups_cats():
    """
    Gets the group and category designation of all categories for final year students

    :return: list of tuples of the group and category designation of all categories for final year students
    """
    groups_cats = []
    for obj in Category500.query.all():
        groups_cats.append((obj.group, obj.category))

    return groups_cats


def get_cls_limits(cls, db_name=None, session=None):
    """
    Retrieves the lower and upper limit for `cls` graduating class designation

    :param cls: graduating class designation
    :param db_name: name of the database file of the graduating students
    :param session: session module of the graduating students
    :return: list of the lower and upper limits for the `cls` class designation
    """
    if not session:
        session = load_session(db_name)
    limits = session.DegreeClass.query.filter_by(cls=class_mapping[cls]).first().limits
    return list(map(float, limits.split(',')))


def get_session_failed_courses(mat_no, level, session):
    """
    Retrieves the failed courses that a student with mat_no `mat_no` offered
    in `level` level

    :param mat_no: mat_no of student
    :param level: level of student
    :param session: session module object of student
    :return: list of failed courses
    """
    failed_courses = []
    res_obj = getattr(session, 'Result{}'.format(level)).query.filter_by(mat_no=mat_no).first()
    if level <= 500:
        for course_code in course_list:
            score_grade = getattr(res_obj, course_code)
            if not score_grade:
                continue
            grade = score_grade.split(',')[1]
            if grade == 'F':
                failed_courses.append(course_code)

    carryovers_credits = res_obj.carryovers
    carryovers_credits = carryovers_credits.split(',') if carryovers_credits else ['']
    if carryovers_credits[0]:
        for course_credits_grade in carryovers_credits:
            course, credit, grade = course_credits_grade.split()
            if grade == "F":
                failed_courses.append(course)

    return failed_courses


def get_student_details_for_cat(mat_no, level, session):
    """
    Gets the details of a student

    :param mat_no: mat number of student
    :param level:  level of student
    :param session: session module object for student
    :return: dict containing the student details
    """
    student = session.PersonalInfo.query.filter_by(mat_no=mat_no).first()

    name = student.othernames + ' ' + '<b>{}</b>'.format(student.surname)
    name += ' (Miss)' if student.sex == 'F' else ''

    course_reg_model = getattr(session, 'CourseReg{}'.format(level))
    res_model = getattr(session, 'Result{}'.format(level))
    course_reg_obj = course_reg_model.query.filter_by(mat_no=mat_no).first()
    res_obj = res_model.query.filter_by(mat_no=mat_no).first()
    if res_obj:
        total_credits = getattr(course_reg_obj, 'tcr', 0)
        credits_passed = getattr(res_obj, 'tcp', 0)

        gpa_credits = session.GPA_Credits.query.filter_by(mat_no=mat_no).first()
        if gpa_credits:
            gpa = getattr(gpa_credits, 'level{}'.format(level)).split(',')[0]
            gpa = float(gpa)
        else:
            gpa = 0

        credits_failed = total_credits - credits_passed
        # carryovers_dict = get_carryovers(mat_no, level=level)
        # carryovers_credits = carryovers_dict['first_sem'] + carryovers_dict['second_sem']
        # carryovers = list(map(lambda x: x[0], carryovers_credits))
        outstanding_courses = get_session_failed_courses(mat_no, level, session)

        details = {
            'mat_no': student.mat_no,
            'name': name,
            'credits_passed': credits_passed,
            'credits_failed': credits_failed,
            'outstanding_courses': '  '.join(outstanding_courses),
            'gpa': gpa
        }
    else:
        # Unregistered and absent students
        details = {
            'mat_no': student.mat_no,
            'name': name,
            'credits_passed': ''
        }

    update_progress('senate_version.get')
    return details


def get_student_details_for_cls(mat_no, session):
    """
    Gets the details of a student with mat_no `mat_no` as required by the successful students
    section of the 500 level senate version

    :param mat_no: mat number of student
    :param session: session module object for student
    :return: dict containing the student details
    """
    student = session.PersonalInfo.query.filter_by(mat_no=mat_no).first()
    name = student.othernames + ' ' + '<b>{}</b>'.format(student.surname)
    name += ' (Miss)' if student.sex == 'F' else ''

    gpa_credits = session.GPA_Credits.query.filter_by(mat_no=mat_no).first()
    if gpa_credits:
        gpa = gpa_credits.level500.split(',')[0]
        gpa = float(gpa)
    else:
        gpa = 0

    details = {
        'mat_no': mat_no,
        'name': name,
        'subject_area': get_dept().capitalize(),
        'gpa': gpa
    }

    return details


def get_details_for_ref_students(mat_no, session):
    """
    Gets the details of a student with mat_no `mat_no` as required by the referred students
    section of the 500 level senate version

    :param mat_no: mat number of student
    :param session: session module object for student
    :return: dict containing the student details
    """
    student = session.PersonalInfo.query.filter_by(mat_no=mat_no).first()
    name = student.othernames + ' ' + '<b>{}</b>'.format(student.surname)
    name += ' (Miss)' if student.sex == 'F' else ''
    level = get_level(mat_no)
    try:
        session_failed_courses = get_session_failed_courses(mat_no, level, session)
        credits_passed_list = list(zip(*gpa_credits_poll(mat_no)[:-1]))[1]
        total_credits_passed = sum(filter(lambda x: x, credits_passed_list))
        total_credits = sum(get_credits(mat_no, session=session.__name__[12:16]))
    except AttributeError:
        # Students who didn't register or sit for the exam
        session_failed_courses = []
        total_credits_passed = 0
        total_credits = 0

    # KeyError for the utils.get_carryovers function
    carryovers_dict = get_carryovers(mat_no, next_level=True)
    carryovers_credits = carryovers_dict['first_sem'] + carryovers_dict['second_sem']
    overall_carryover_courses = list(map(lambda x: x[0], carryovers_credits))
    outstanding_courses = []
    for course_code in overall_carryover_courses:
        if course_code not in session_failed_courses:
            outstanding_courses.append(course_code)

    details = {
        'mat_no': mat_no,
        'name': name,
        'session_carryover_courses': '  '.join(session_failed_courses),
        'cum_credits_to_date': total_credits_passed,
        'outstanding_credits': total_credits - total_credits_passed,
        'outstanding_courses': ' '.join(outstanding_courses)
    }

    update_progress('senate_version_500.get')
    return details


def get_other_students_details(mat_no, session, group):
    """
    Gets the details of a student with mat_no `mat_no` as required by sections other
    than the successful and referred students section of the 500 level senate version

    :param mat_no: mat number of student
    :param session: session module object for student
    :return: dict containing the student details
    """
    student = session.PersonalInfo.query.filter_by(mat_no=mat_no).first()
    name = student.othernames + ' ' + '<b>{}</b>'.format(student.surname)
    name += ' (Miss)' if student.sex == 'F' else ''

    details = {
        'mat_no': mat_no,
        'name': name,
        'remark': ''
    }

    update_progress('senate_version_500.get')
    return details


def get_students_for_course_adviser(level, acad_session=None, retDB=False):
    if not acad_session:
        acad_session = get_current_session()
    entry_session = get_session_from_level(acad_session, level, True)
    return get_students_by_level(entry_session, level, is_course_adviser=True, retDB=retDB)


def get_students_by_level(entry_session, level, is_course_adviser=False, retDB=False):
    """
    Gets all the mat numbers of students in a particular db

    This only includes the regular students that entered during the `entry_session` session, DE and probating students
    that somehow have ties to this db.

    :param entry_session: entry session
    :param level: level of students
    :param is_course_adviser: if true returns the students associated with the level course adviser
    :param retDB: if True, returns a dict
    :return: list of mat numbers if not `retDB` else a dictionary of db name being mapped to a list of mat numbers
    """
    entry_session_db_name = '{}_{}'.format(entry_session, entry_session + 1)
    session = load_session(entry_session_db_name)
    num_students = 0

    # Regular students
    if level > 500 and is_course_adviser:
        students = []
    else:
        students = session.PersonalInfo.query.filter_by(is_symlink=0).filter_by(mode_of_entry=1).all()
    if retDB:
        students = {entry_session_db_name: list(map(lambda stud: stud.mat_no, students))}
    else:
        students = list(map(lambda stud: stud.mat_no, students))
    num_students += len(students)

    level_num = level // 100
    other_students = session.SymLink.query.filter(getattr(session.SymLink, f'database_{level_num}') != None)\
        .order_by(f'DATABASE_{level_num}').all()    # DE and probating students

    # Spillover students
    if level_num == 5 and not is_course_adviser:
        for num in range(6, 9):
            other_students.extend(session.SymLink.query.filter(getattr(session.SymLink, f'database_{num}') != None)
                                  .order_by(f'DATABASE_{num}').all())
    elif level_num > 5 and is_course_adviser:
        for num in range(7, 9):
            other_students.extend(session.SymLink.query.filter(getattr(session.SymLink, f'database_{num}') != None)
                                  .order_by(f'DATABASE_{num}').all())
    num_students += len(other_students)
    set_increment('senate_version.get', increment_basis=num_students)
    set_increment('senate_version_500.get', increment_basis=num_students)
    if retDB:
        # groups the students by their database name
        stud_db_map, num = {}, [5, 6][is_course_adviser]
        for stud in other_students:
            if level_num == [5, 6][is_course_adviser]:
                try:
                    db = getattr(stud, f'database_{num}')
                    assert db is not None
                    db_name = db[:-3].replace('-', '_')
                except AssertionError:
                    num += 1
                    db_name = getattr(stud, f'database_{num}')[:-3].replace('-', '_')
            else:
                db_name = getattr(stud, f'database_{level_num}')[:-3].replace('-', '_')
            try:
                stud_db_map[db_name].append(stud.mat_no)
            except KeyError:
                stud_db_map[db_name] = [stud.mat_no]
        if entry_session_db_name in stud_db_map:
            de_probating_students = stud_db_map.pop(entry_session_db_name)
            students[entry_session_db_name].extend(de_probating_students)
        students.update(stud_db_map)
    else:
        other_students = list(map(lambda stud: stud.mat_no, other_students))
        students.extend(other_students)

    return students


def filter_students_by_category(level, category, db_name, students):
    """
    Strips and returns students with category `category` from a list of students

    :param level: level of the students
    :param category: category to match students against
    :param db_name: name of the database file of the students
    :param students: list of students
    :return: list of students with ctagory `category`
    """
    session = load_session(db_name)
    res_obj = getattr(session, 'Result{}'.format(level))
    studs = []
    for mat_no in students:
        stud = res_obj.query.filter_by(mat_no=mat_no).first()
        if stud:
            if stud.category == category:
                studs.append(mat_no)

    return studs


def get_students_by_category(level, entry_session, category=None, get_all=False):
    """
    Gets all students within a category

    If `get_all` is supplied, `category` is ignored

    :param level: level of students
    :param entry_session: entry session of students
    :param category: (Optional) category to fetch
    :param get_all: (Optional) if True return all categories of students
    :return: list of students if not `get_all` else dictionary of all category mapping to list of students
    """
    set_progress('senate_version.get', description='Fetching students...')
    set_increment('senate_version.get', duration=18)

    set_progress('senate_version_500.get', description='Fetching students...')
    set_increment('senate_version_500.get', duration=3.8)

    mat_no_dict = get_students_by_level(entry_session, level, retDB=True)
    acad_session = get_session_from_level(entry_session, level)
    if get_all:
        students = dict.fromkeys(mat_no_dict)
        categories = get_categories(final_year=(level == 500))

        cat_dict = dict(zip(categories, [[]] * len(categories)))
        for db_name in mat_no_dict:
            students[db_name] = cat_dict.copy()
            session = load_session(db_name)
            for mat_no in mat_no_dict[db_name]:
                # level = level if level != 500 else get_level(mat_no)  # Accounts for spillover students
                cat = get_category(mat_no, level, acad_session, session)
                if students[db_name].get(cat):
                    students[db_name][cat].append(mat_no)
                else:
                    students[db_name][cat] = [mat_no]
                update_progress('senate_version.get')
    else:
        students = dict.fromkeys(mat_no_dict)
        for db_name in mat_no_dict:
            filtered_studs = filter_students_by_category(level, category, db_name, mat_no_dict[db_name])
            students[db_name] = filtered_studs

    set_progress('senate_version.get', progress=20)
    set_progress('senate_version_500.get', progress=4)
    return students


def get_students_details_by_category(level, entry_session, category=None, get_all=False):
    """
    Gets the details for students in `level` level as required by the senate version for
    non-graduating students

    If `get_all` is supplied, `category` is ignored

    :param level: level of students
    :param entry_session: entry session of students
    :param category: (Optional) category to fetch
    :param get_all: (Optional) if true return the details of all categories of students
    :return: list of dicts of the details students with all categories if `get_all` is true else
             list of dicts of the details students with `category` category
    """
    populate_course_list(level)

    students = get_students_by_category(level, entry_session, category=category, get_all=get_all)

    set_progress('senate_version.get', description='Formatting student\'s data...')
    set_increment('senate_version.get', duration=33)

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

    set_progress('senate_version.get', progress=53)
    return students_details


def group_students_by_category(students):
    """
    Groups the dict of students by their categories

    :param students: dictionary of students as returned by the `get_students_by_category` function
    :return: dict of students grouped by their category grouping
    """
    category_mapping = dict(get_groups_cats())
    groups = category_mapping.keys()
    all_students = dict.fromkeys(groups, {})

    for db_name in students:
        for group in groups:
            studs = students[db_name][category_mapping[group]]
            if all_students.get(group):
                all_students[group][db_name] = studs
            else:
                all_students[group] = {db_name: studs}

    return all_students


def filter_students_by_degree_class(degree_class, db_name, students):
    """
    Strips and returns the details of students with `degree_class` graduating class
    designation from the list of students

    :param degree_class: graduating class designation
    :param db_name: name of the database file of the graduating students
    :param students: list of graduating students
    :return: list of dicts of graduating students
    """
    session = load_session(db_name)
    limits = get_cls_limits(degree_class, session=session)
    cgpa_obj = getattr(session, 'GPA_Credits')
    studs = []
    for stud in students:
        cgpa = cgpa_obj.query.filter_by(mat_no=stud).first().cgpa
        if limits[0] <= cgpa <= limits[1]:
            details = get_student_details_for_cls(stud, session)
            details['cgpa'] = float(cgpa)
            studs.append(details)
            students.remove(stud)
        update_progress('senate_version_500.get')

    return studs


def get_final_year_students_by_category(entry_session, category=None, get_all=False):
    """
    Gets the details for students required by the senate version for graduating students

    If `get_all` is supplied, `category` is ignored

    :param entry_session: entry session of students
    :param category: (Optional) category to fetch
    :param get_all: (Optional) if true return the details of all categories of students
    :return: list of dicts of the details students with all categories if `get_all` is true else
             list of dicts of the details students with `category` category
    """
    populate_course_list(500)

    students_categories = get_students_by_category(500, entry_session, category=category, get_all=get_all)

    set_progress('senate_version_500.get', description='Formatting student\'s data...')
    set_increment('senate_version_500.get', duration=92.7)

    all_students_by_category = group_students_by_category(students_categories)
    if get_all:
        all_students = {}

        # Successful students
        successful_students = all_students_by_category.pop('successful students')
        students = {}
        classes = class_mapping.keys()
        for degree_class in classes:
            studs = []
            for db_name in successful_students:
                studs.extend(filter_students_by_degree_class(degree_class, db_name, successful_students[db_name]))
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

        set_progress('senate_version_500.get', progress=96.7)
        return all_students
    # else:
    #     group = tuple(map(lambda x: x[0] == category, get_groups_cats()))[0]
    #     students_with_category = all_students_by_category[group]
    #     students = []
    #     classes = class_mapping.keys()
    #     if group == 'successful students':
    #         for db_name in students_with_category.keys():
    #             studs = filter_students_by_degree_class(degree_class, db_name, students_with_category[db_name])
    #             students.extend(studs)
    #     else:
    #         pass
    #
    #     return students
