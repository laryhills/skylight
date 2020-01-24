from flask import render_template
from weasyprint import HTML
from sms.config import app, base_dir
from sms.result_statement import get_carryovers
from sms import personal_info
from os.path import join
from json import loads


def get(mat_no, session):
    carryovers = loads(get_carryovers(mat_no))
    person = loads(personal_info.get(mat_no))
    level = list(str(person['current_level']))
    phone_no = list(person['phone_no'])
    mode_of_entry = 'PUTME' if person['mode_of_entry'] == 1 else ['DE(200)', 'DE(300)'][person['mode_of_entry'] == 3]
    sex = ['Female', 'Male'][person['sex'] == 'M']
    with app.app_context():
        html = render_template('course_reg_template.htm', mat_no=mat_no, session='{}/{}'.format(session, session + 1),
                               surname=person['surname'], othernames=person['othernames'].upper(),
                               depat='MECHANICAL ENGINEERING', mode_of_entry=mode_of_entry,
                               level=level, phone_no=phone_no, sex=sex,
                               email=person['email_address'], state=person['state_of_origin'],
                               first_sem=carryovers['first_sem'], second_sem=carryovers['second_sem'])
        HTML(string=html).write_pdf('course_form.pdf')
