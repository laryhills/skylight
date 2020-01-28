import os
import secrets
from flask import render_template
from weasyprint import HTML
from sms.config import app, base_dir
from sms.utils import get_carryovers
from sms import generated_pdfs, personal_info
from json import loads


def get(mat_no, session):
    if mat_no in generated_pdfs:
        uri = os.path.join(os.path.expanduser('~'), 'sms', 'cache', generated_pdfs[mat_no])
        return uri

    person = loads(personal_info.get(mat_no))
    level = list(str(person['current_level']))
    phone_no = list(person['phone_no'])
    mode_of_entry = 'PUTME' if person['mode_of_entry'] == 1 else ['DE(200)', 'DE(300)'][person['mode_of_entry'] == 3]
    sex = ['Female', 'Male'][person['sex'] == 'M']

    carryovers = loads(get_carryovers(mat_no, person['current_level']))
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
    with app.app_context():
        html = render_template('course_reg_template.htm', mat_no=mat_no, session='{}/{}'.format(session, session + 1),
                               surname=person['surname'], othernames=person['othernames'].upper(),
                               depat='MECHANICAL ENGINEERING', mode_of_entry=mode_of_entry,
                               level=level, phone_no=phone_no, sex=sex,
                               email=person['email_address'], state=person['state_of_origin'],
                               first_sem_carryover_courses=first_sem_carryover_courses,
                               first_sem_carryover_credits=first_sem_carryover_credits,
                               second_sem_carryover_courses=second_sem_carryover_courses,
                               second_sem_carryover_credits=second_sem_carryover_credits)
        file_name = secrets.token_hex(8) + '.pdf'
        uri = os.path.join(os.path.expanduser('~'), 'sms', 'cache', file_name)
        HTML(string=html).write_pdf(uri)
        generated_pdfs[mat_no] = file_name
        return uri
