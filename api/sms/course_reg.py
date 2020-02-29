import os.path
import secrets
from pathlib import Path
from json import loads
from flask import abort

from flask import render_template
from weasyprint import HTML
from sms.config import app
from sms.config import db
from sms import utils
from sms import personal_info
from sms import utils
from sms.utils import get_carryovers
from sms.models.master import Master, MasterSchema

base_dir = os.path.dirname(__file__)
uniben_logo_path = 'file:///' + os.path.join(base_dir, 'templates', 'static', 'Uniben_logo.png')


def get(mat_no, session=None):
    person = personal_info.get(mat_no, 0)
    phone_no = person['phone_no'] if person['phone_no'] else None
    mode_of_entry = ["PUTME", "DE(200)", "DE(300)"][person["mode_of_entry"] - 1]
    entry_session = person['session_admitted']
    graduation_status = int(person['grad_stats'])
    sex = ['Female', 'Male'][person['sex'] == 'M']
    if person["sex"] == 'F':
        person['surname'] += " (Miss)"
    depat = utils.get_depat('long')

    # for new registrations, the assumption is that the level has been updated by admin
    current_level = str(utils.get_level(mat_no))

    course_reg_frame = {}
    some_personal_info = {'surname': person['surname'], 'othernames': person['othernames'].upper(),
                          'depat': depat, 'mode_of_entry': mode_of_entry, 'current_level': current_level,
                          'phone_no': phone_no, 'sex': sex, 'email': person['email_address'],
                          'state_of_origin': person['state_of_origin'], 'lga_of_origin': person['lga_of_origin']}

    # Get the table to populate and check if the student has reached the 8-year limit

    crs, table_to_populate = utils.get_most_recent_course_reg(mat_no)
    table_to_populate = table_to_populate[:-3] + str(int(table_to_populate[-3:]) + 100)
    if int(table_to_populate[-3:]) + 100 > 800:
        return course_reg_frame['personal_info': some_personal_info,
                                'table_to_populate': table_to_populate,
                                'courses': {'first_sem': [],
                                            'second_sem': []},
                                'error': 'Student cannot carry out course reg as he has exceeded the 8-year limit']

    if session is None and graduation_status != 1:
        # condition checks if this a new registration
        # if not, it means we are just getting data for viewing
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
        if utils.get_level(mat_no, 1) == 400:
            # Force only reg of UBTS for incoming 400L
            second_sem_carryover_courses, second_sem_carryover_credits = ["UBT400"], ["6"]
        if utils.get_level(mat_no) == 400 and utils.get_level(mat_no, 1) == 500:
            if "UBT400" in second_sem_carryover_courses:
                second_sem_carryover_courses = list(second_sem_carryover_courses)
                second_sem_carryover_credits = list(second_sem_carryover_credits)
                second_sem_carryover_courses.remove("UBT400")
                second_sem_carryover_credits.remove("6")

        return course_reg_frame['personal_info': some_personal_info,
                                'table_to_populate': table_to_populate,
                                'courses': {'first_sem': first_sem_carryover_courses,
                                            'second_sem': second_sem_carryover_courses},
                                'error': '']
    else:
        current_session = utils.get_current_session()
        db_lev = 100 * (current_session-entry_session + 1)
        table_to_get = 'CourseReg' + str(db_lev)
        courses_registered = utils.get_registered_courses(mat_no, db_lev, true_levels=False)['courses']
        first_sem, second_sem = [], []
        for course in courses_registered:
            # get course details
            pass


def post(course_reg):
    """ ======= FORMAT ======
        mat_no: 'ENGxxxxxxx'
        table_to_populate: CourseRegxxx
        courses:
            first_sem: []
            second_sem: []
    """
    global CourseRegxxxSchema
    # todo: Get "session_admitted" from "current_session" in master.db for 100l
    # todo: On opening the personal info tab, the backend should supply this data
    session = int(course_reg['session_admitted'])
    db_name = '{}_{}.db'.format(session, session + 1)

    mat_no = course_reg['mat_no']
    table_to_populate = course_reg['table_to_populate']
    level = utils.get_level(mat_no)

    try:
        exec('from sms.models._{0} import {1}Schema'.format(db_name[:-3], table_to_populate))
    except ImportError:
        # create and import new database model
        abort(400)
    db_name = db_name.replace('_', '-')

    CourseRegxxxSchema = locals()[table_to_populate+'Schema']
    course_reg_xxx_schema = CourseRegxxxSchema()
    # course_registration = course_reg_xxx_schema.load(course_reg)

    # db.session.add(course_registration)
    # db.session.commit()

