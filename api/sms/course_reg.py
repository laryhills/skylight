import os
import secrets
from flask import render_template
from weasyprint import HTML
from sms.config import app
from sms.utils import get_carryovers
from sms import personal_info
from json import loads
from sms import utils


def get(mat_no, session=None):
    pass #if mat_no in generated_pdfs:
    pass #    uri = os.path.join(os.path.expanduser('~'), 'sms', 'cache', generated_pdfs[mat_no])
    pass #    return uri

    person = personal_info.get(mat_no,0)
    phone_no = list(person['phone_no']) if person['phone_no'] else None
    mode_of_entry = ["PUTME", "DE(200)", "DE(300)"][person["mode_of_entry"]-1]
    sex = ['Female', 'Male'][person['sex'] == 'M']
    if person["sex"] == 'F':
        person['surname'] += " (Miss)"
    level = list(str(utils.get_level(mat_no,1)))

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
    if utils.get_level(mat_no,1) == 400:
        # Force only reg of UBTS for incoming 400L
        second_sem_carryover_courses, second_sem_carryover_credits = ["UBT400"], ["6"]
    if utils.get_level(mat_no) == 400 and utils.get_level(mat_no,1) == 500:
        if "UBT400" in second_sem_carryover_courses:
            second_sem_carryover_courses = list(second_sem_carryover_courses)
            second_sem_carryover_credits = list(second_sem_carryover_credits)
            second_sem_carryover_courses.remove("UBT400")
            second_sem_carryover_credits.remove("6")

    with app.app_context():
        html = render_template('course_reg_template.htm', mat_no=mat_no, session='{}/{}'.format(2019, 2019 + 1),
                               surname=person['surname'], othernames=person['othernames'].upper(),
                               depat='MECHANICAL ENGINEERING', mode_of_entry=mode_of_entry,
                               level=level, phone_no=phone_no, sex=sex,
                               email=person['email_address'], state=person['state_of_origin'],
                               first_sem_carryover_courses=first_sem_carryover_courses,
                               first_sem_carryover_credits=first_sem_carryover_credits,
                               second_sem_carryover_courses=second_sem_carryover_courses,
                               second_sem_carryover_credits=second_sem_carryover_credits)
        file_name = secrets.token_hex(8) + '.pdf'
        file_name = mat_no + '.pdf'
        uri = os.path.join(os.path.expanduser('~'), 'sms', 'cache_mechanical', 'levels', str(utils.get_level(mat_no,1)), file_name)
        uri2 = os.path.join(os.path.expanduser('~'), 'sms', 'cache_mechanical', 'mats', mat_no[:5], file_name)
        HTML(string=html).write_pdf(uri)
        HTML(string=html).write_pdf(uri2)
        #generated_pdfs[mat_no] = file_name
        print (uri,uri2)
