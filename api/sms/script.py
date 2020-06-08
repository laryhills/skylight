"""
    Utility script much like utils.py for handling frequently called or single use simple utility functions
"""

from sms.utils import load_session, get_carryovers
from sms.models.master import Category


def get_student_details(mat_no, level, session):
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
    name = student.surname + ' ' + student.othernames
    name += ' (Miss)' if student.sex == 'F' else ''
    # carryovers_dict = get_carryovers(mat_no, level=level, retJSON=False)
    # carryovers_credits = carryovers_dict['first_sem'] + carryovers_dict['second_sem']
    # carryovers = list(map(lambda x: x[0], carryovers_credits))
    carryovers_credits = eval('session.Result{}'.format(level)).query.filter_by(mat_no=mat_no).first().carryovers
    carryovers_credits = carryovers_credits.split(',')
    if carryovers_credits[0]:
        carryovers = list(map(lambda x: x.split()[0], carryovers_credits))
    else:
        carryovers = []
    details = {
        'mat_no': student.mat_no,
        'name': name,
        'credits_passed': credits_passed,
        'credits_failed': credits_failed,
        'outstanding_courses': '  '.join(carryovers),
        'gpa': gpa
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


def get_student_by_category(level, category, db_name, students):
    """
    Strips all students with `category` category from `students`

    :param level: level of students
    :param category: category to fetch
    :param db_name: name of the db
    :param students: list of students
    :return: list of dicts of students details
    """
    session = load_session(db_name)
    resObj = eval('session.Result{}'.format(level))
    studs = list(map(lambda stud: get_student_details(stud.mat_no, level, session), resObj.query.filter_by(category=category).all()))
    studs = list(filter(lambda x: x['mat_no'] in students, studs))

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
        students = {}
        categories = []
        for obj in Category.query.all():
            categories.append(obj.category)
        for category in categories:
            studs = []
            for db_name in mat_no_dict.keys():
                studs.extend(get_student_by_category(level, category, db_name, mat_no_dict[db_name]))
            students[category] = studs
    else:
        students = []
        for db_name in mat_no_dict.keys():
            studs = get_student_by_category(level, category, db_name)
            students.extend(studs)

    return students
