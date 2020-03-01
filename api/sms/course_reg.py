import os.path
from json import loads
from flask import abort
from sms.config import db
from sms import personal_info
from sms import utils
from sms.utils import get_carryovers


def get(mat_no, acad_session=None):
    person = personal_info.get(mat_no, 0)
    phone_no = person['phone_no'] if person['phone_no'] else None
    mode_of_entry = ["PUTME", "DE(200)", "DE(300)"][person["mode_of_entry"] - 1]
    entry_session = person['session_admitted']
    graduation_status = int(person['grad_stats']) if person['grad_stats'] else None
    sex = ['Female', 'Male'][person['sex'] == 'M']
    if person["sex"] == 'F':
        person['surname'] += " (Miss)"
    depat = utils.get_depat('long')

    # for new registrations, the assumption is that the level has been updated by admin
    current_level = str(utils.get_level(mat_no))
    current_session = utils.get_current_session()

    course_reg_frame = {}
    some_personal_info = {'surname': person['surname'], 'othernames': person['othernames'].upper(),
                          'depat': depat, 'mode_of_entry': mode_of_entry, 'current_level': current_level,
                          'phone_no': phone_no, 'sex': sex, 'email': person['email_address'],
                          'state_of_origin': person['state_of_origin'],
                          'lga_of_origin': person['lga_of_origin'] if 'lga_of_origin' in person else ''}

    # use last course_reg table to account for temp withdrawals
    # these guys break any computation that relies on sessions
    table_to_populate = ''
    crs = utils.get_registered_courses(mat_no, level=None, true_levels=False)
    for key in range(800, 0, -100):
        if crs[key]['courses']:
            table_to_populate = crs[key+100]['table']
            break
    # if no previous course_reg: either new student or temp withdrawal at 100 level
    # I guess that still qualifies as new student
    if table_to_populate == '':
        table_to_populate = 'CourseReg100'

    if not acad_session and (int(table_to_populate[-3:]) + 100 > 800):
        course_reg_frame = {'personal_info': some_personal_info,
                            'table_to_populate': '',
                            'course_reg_session': current_session,
                            'course_reg_level': None,
                            'courses': {'first_sem': [],
                                        'second_sem': []},
                            'error': 'Student cannot carry out course reg as he has exceeded the 8-year limit'}

    elif not acad_session and (graduation_status != 1 if graduation_status else True):
        # condition checks to confirm that this is a new registration
        # if not, it means we are just getting data for viewing (go to else)
        carryovers = loads(get_carryovers(mat_no))
        first_sem = carryovers['first_sem']
        if first_sem:
            first_sem_carryover_courses, first_sem_carryover_credits = list(zip(*first_sem))
        else:
            first_sem_carryover_courses, first_sem_carryover_credits = [], []

        second_sem = carryovers['second_sem']
        if second_sem:
            second_sem_carryover_courses, second_sem_carryover_credits = list(zip(*second_sem))
        else:
            second_sem_carryover_courses, second_sem_carryover_credits = [], []
        if utils.get_level(mat_no) == 400:
            # Force only reg of UBITS for incoming 400L
            second_sem_carryover_courses, second_sem_carryover_credits = ["UBT400"], ["6"]
        if utils.get_level(mat_no) == 500:
            if "UBT400" in second_sem_carryover_courses:
                second_sem_carryover_courses = list(second_sem_carryover_courses)
                second_sem_carryover_credits = list(second_sem_carryover_credits)
                second_sem_carryover_courses.remove("UBT400")
                second_sem_carryover_credits.remove("6")

        course_reg_frame = {'personal_info': some_personal_info,
                            'table_to_populate': table_to_populate,
                            'course_reg_session': current_session,
                            'course_reg_level': current_level,
                            'courses': {'first_sem': first_sem_carryover_courses,
                                        'second_sem': second_sem_carryover_courses},
                            'error': ''}
    else:
        course_reg = utils.get_registered_courses(mat_no, level=None, true_levels=False)
        course_registration = {}
        for key in course_reg:
            db_entry = course_reg[key]
            if db_entry['course_reg_session'] == acad_session:
                course_registration = db_entry

        if course_registration == {}:
            course_reg_frame = {'personal_info': some_personal_info,
                                'table_to_populate': '',
                                'course_reg_session': acad_session,
                                'course_reg_level': None,
                                'courses': {'first_sem': [],
                                            'second_sem': []},
                                'error': 'No course registration for entered session'}
        else:
            course_reg_level   = course_registration['course_reg_level']
            course_reg_session = course_registration['course_reg_session']
            table_to_get       = course_registration['table']
            courses_registered = course_registration['courses']
            level_courses      = [[], []]        # first_sem, second_sem
            carryovers         = [[], []]        # first_sem, second_sem
            for course in courses_registered:
                course_dets = utils.course_details.get(course, 0)
                if course_dets['course_level'] == course_reg_level:
                    level_courses[course_dets['course_semester']-1].append((course, course_dets['course_credit']))
                else:
                    carryovers[course_dets['course_semester']-1].append((course, course_dets['course_credit']))
            first_sem = carryovers[0] + level_courses[0]
            second_sem = carryovers[1] + level_courses[1]

            course_reg_frame = {'personal_info': some_personal_info,
                                'table_to_populate': table_to_get,
                                'course_reg_session': course_reg_session,
                                'course_reg_level': course_reg_level,
                                'courses': {'first_sem': first_sem,
                                            'second_sem': second_sem},
                                'error': ''}
    return course_reg_frame


def post(course_reg):
    # The 'session_acad' variable is to enable edits
    #
    """ ======= FORMAT =======
        mat_no: 'ENGxxxxxxx'
        table_to_populate: 'CourseRegxxx'
        course_reg_session = 20xx
        course_reg_level = x00
        courses:
            first_sem: []
            second_sem: []
        =======================

    example...
    course_reg = {'mat_no': 'ENG1503886', 'table_to_populate': 'CourseReg500', 'course_reg_session' = 20xx,
                  'course_reg_level' = x00, 'courses': {'first_sem': [], 'second_sem': []}}
    """

    # todo: Get "session_admitted" from "current_session" in master.db for 100l
    # todo: On opening the personal info tab, the backend should supply this data

    courses = []
    courses.extend(course_reg['courses']['first_sem'])
    courses.extend(course_reg['courses']['second_sem'])
    courses = sorted(courses)

    mat_no = course_reg['mat_no']
    table_to_populate = course_reg['table_to_populate']
    course_reg_session = course_reg['course_reg_session']
    course_reg_level = course_reg['course_reg_level']

    db_name = utils.get_DB(mat_no)[:-3]
    session = utils.load_session(db_name)

    try:
        exec('from sms.models._{0} import {1}Schema'.format(db_name, table_to_populate))
        exec('from sms.models._{0} import {1}'.format(db_name, table_to_populate))
    except ImportError:
        abort(400)

    CourseRegxxxSchema = locals()[table_to_populate+'Schema']
    CourseRegxxx = locals()[table_to_populate]

    table_columns = utils.get_attribute_names(CourseRegxxx)
    registration = {}
    for col in table_columns:
        if col in courses:
            registration[col] = '1'
            courses.remove(col)
        elif col not in ['mat_no', 'carryovers', 'probation', 'others', 'level', 'session']:
            registration[col] = '0'
    registration['carryovers'] = ','.join(courses)
    registration['mat_no'] = mat_no
    registration['probation'] = '0'
    registration['others'] = None
    registration['level'] = course_reg_level
    registration['session'] = course_reg_session

    course_reg_xxx_schema = CourseRegxxxSchema()
    course_registration = course_reg_xxx_schema.load(registration)
    db.session.add(course_registration)
    db.session.commit()

    return 'course registration successful'
