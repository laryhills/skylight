import os.path
import secrets
from pathlib import Path
from json import loads
from flask import render_template
from weasyprint import HTML
from sms.config import app
from sms.utils import get_carryovers
from sms import personal_info
from sms import utils

base_dir = os.path.dirname(__file__)
uniben_logo_path = 'file:///' + os.path.join(base_dir, 'templates', 'static', 'Uniben_logo.png')


def get(mat_no, session=None):
    person = personal_info.get(mat_no, 0)
    phone_no = list(person['phone_no']) if person['phone_no'] else None
    mode_of_entry = ["PUTME", "DE(200)", "DE(300)"][person["mode_of_entry"]-1]
    sex = ['Female', 'Male'][person['sex'] == 'M']
    if person["sex"] == 'F':
        person['surname'] += " (Miss)"
    depat = utils.get_depat('long')
    level = list(str(utils.get_level(mat_no, 1)))
    session = utils.get_current_session() if not session else session

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

    with app.app_context():
        html = render_template('course_reg_template.htm', mat_no=mat_no, uniben_logo_path=uniben_logo_path, session='{}/{}'.format(session, session + 1),
                               surname=person['surname'], othernames=person['othernames'].upper(),
                               depat=depat, mode_of_entry=mode_of_entry,
                               level=level, phone_no=phone_no, sex=sex,
                               email=person['email_address'], state=person['state_of_origin'],
                               lga=person['lga'],
                               first_sem_carryover_courses=first_sem_carryover_courses,
                               first_sem_carryover_credits=first_sem_carryover_credits,
                               second_sem_carryover_courses=second_sem_carryover_courses,
                               second_sem_carryover_credits=second_sem_carryover_credits)
        file_name = secrets.token_hex(8) + '.png'
        uri = os.path.join(os.path.expanduser('~'), 'sms', 'cache_mechanical', 'pdfs', file_name)
        data = {'pdf': HTML(string=html).write_pdf()}
        HTML(string=html).write_pdf(uri)

        return data
