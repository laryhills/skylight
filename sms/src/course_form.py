import os.path
import secrets
import pdfkit
import imgkit
from collections import defaultdict
from flask import render_template, send_from_directory
from sms.src import course_reg
from sms.config import app, CACHE_BASE_DIR, UNIBEN_LOGO_PATH
from sms.src.users import access_decorator
from sms.src.utils import get_current_session, get_dept


@access_decorator
def get(mat_no=None, session=None, to_print=False):
    current_session = get_current_session()
    session = session if session else current_session

    if mat_no:
        course_registration = course_reg.init_new_course_reg(mat_no)
        if session != current_session or course_registration[0] == 'Course Registration already exists':
            course_registration = course_reg.get_existing_course_reg(mat_no, session)

        if course_registration[1] != 200:
            return course_registration

        course_registration = course_registration[0]
        department = get_dept()

    else:
        mat_no = ''
        department = ''
        course_registration = {
            'personal_info': defaultdict(str),
            'course_reg_session': session,
            'course_reg_level': '',
            'carryovers': {'first_sem': [], 'second_sem': []}
        }
    session = course_registration['course_reg_session']
    person = course_registration['personal_info']
    level = list(str(course_registration['course_reg_level']))
    courses = course_registration['carryovers']

    first_sem_courses, _, first_sem_credits = list(zip(*courses['first_sem']))[:3] or ([], [], [])
    second_sem_courses, _, second_sem_credits = list(zip(*courses['second_sem']))[:3] or ([], [], [])

    with app.app_context():
        html = render_template('course_form_template.htm', mat_no=mat_no, uniben_logo_path=UNIBEN_LOGO_PATH,
                               session='{}/{}'.format(session, session + 1), dept=department,
                               surname=person['surname'], othernames=person['othernames'].upper(),
                               phone_no=person['phone_no'], sex=person['sex'], lga=person['lga'],
                               email=person['email_address'], state=person['state_of_origin'],
                               level=level, mode_of_entry=person['mode_of_entry_text'],
                               first_sem_courses=first_sem_courses, first_sem_credits=first_sem_credits,
                               second_sem_courses=second_sem_courses, second_sem_credits=second_sem_credits)

        file_name = secrets.token_hex(8)
        if to_print:
            options = {
                'page-size': 'A4',
                'enable-local-file-access': None,
                'disable-smart-shrinking': None,
                'print-media-type': None,
                'no-outline': None,
                'margin-left': '0.5in',
                'margin-right': '0.5in',
                'margin-top': '0.6in',
                'margin-bottom': '0.5in',
                'dpi': 100,
                'log-level': 'warn',
            }
            pdfkit.from_string(html, os.path.join(CACHE_BASE_DIR, file_name + '.pdf'), options=options)
            resp = send_from_directory(CACHE_BASE_DIR, file_name + '.pdf', as_attachment=True)
        else:
            img_fmt = 'png'
            options = {
                'format': img_fmt,
                'enable-local-file-access': None,
                'disable-smart-width': None,
                'quality': 50,
                'log-level': 'warn',
            }
            imgkit.from_string(html, os.path.join(CACHE_BASE_DIR, file_name + '.' + img_fmt), options=options)
            resp = send_from_directory(CACHE_BASE_DIR, file_name + '.' + img_fmt, as_attachment=True)
        return resp, 200
