import os.path
import secrets
from flask import render_template, send_from_directory
from sms.src import course_reg
from sms.config import app, cache_base_dir
from sms.src.users import access_decorator
from sms.src.utils import get_current_session
from sms.src.ext.pdf_image_converter import pdftoimage

base_dir = os.path.dirname(__file__)
uniben_logo_path = 'file:///' + os.path.join(os.path.split(base_dir)[0], 'templates', 'static', 'Uniben_logo.png')


@access_decorator
def get(mat_no=None, session=None, to_print=False):
    # TODO: Clear the cache directory
    current_session = get_current_session()
    if mat_no:
        if session == current_session:
            course_registration = course_reg.init_new(mat_no)
        else:
            course_registration = course_reg.get(mat_no, session)

        if course_registration[1] == 200:
            course_registration = course_registration[0]
        else:
            return course_registration
    else:
        mat_no = ''
        course_registration = {
            'personal_info': defaultdict(str),
            'course_reg_session': session if session else current_session,
            'course_reg_level': '',
            'courses': {'first_sem': [], 'second_sem': []}
        }
    session = course_registration['course_reg_session']
    person = course_registration['personal_info']
    level = list(str(course_registration['course_reg_level']))

    first_sem = course_registration['courses']['first_sem']
    second_sem = course_registration['courses']['second_sem']
    if first_sem:
        first_sem_carryover_courses, first_sem_carryover_titles, first_sem_carryover_credits = list(zip(*first_sem))
    else:
        first_sem_carryover_courses, first_sem_carryover_credits = [], []
    if second_sem:
        second_sem_carryover_courses, second_sem_carryover_titles, second_sem_carryover_credits = list(zip(*second_sem))
    else:
        second_sem_carryover_courses, second_sem_carryover_credits = [], []

    with app.app_context():
        html = render_template('course_reg_template.htm', mat_no=mat_no, uniben_logo_path=uniben_logo_path,
                               session='{}/{}'.format(session, session + 1),
                               surname=person['surname'], othernames=person['othernames'].upper(),
                               depat=person['department'], mode_of_entry=person['mode_of_entry'],
                               level=level, phone_no=person['phone_no'], sex=person['sex'],
                               email=person['email_address'], state=person['state_of_origin'],
                               lga=person['lga'],
                               first_sem_carryover_courses=first_sem_carryover_courses,
                               first_sem_carryover_credits=first_sem_carryover_credits,
                               second_sem_carryover_courses=second_sem_carryover_courses,
                               second_sem_carryover_credits=second_sem_carryover_credits)

        file_name = secrets.token_hex(8)
        HTML(string=html).write_pdf(os.path.join(cache_base_dir, file_name + '.pdf'))

        if to_print:
            resp = send_from_directory(cache_base_dir, file_name + '.pdf', as_attachment=True)
        else:
            img_fmt = 'png'
            pdftoimage(os.path.join(cache_base_dir, file_name + '.pdf'), fmt=img_fmt)
            resp = send_from_directory(cache_base_dir, file_name + '.' + img_fmt, as_attachment=True)
        return resp
