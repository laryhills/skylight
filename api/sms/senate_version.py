import os
import time
import secrets
import pdfkit
from num2words import num2words
from jinja2 import Template
from flask import render_template, send_from_directory

from sms.users import access_decorator
from sms.script import get_students_by_category
from sms.models.master import Category
from sms.config import app, cache_base_dir, get_current_session
from sms.utils import get_depat

base_dir = os.path.dirname(__file__)
categories = Category.query.all()
keys = ['mat_no', 'name', 'credits_passed', 'credits_failed', 'outstanding_courses', 'gpa']


def load_cat_section(cat, students, session):
    for cat_obj in categories:
        if cat_obj.category == cat:
            break
    sizes = [int(x) for x in cat_obj.sizes.split(',')]
    headers = cat_obj.headers.split(',')
    no_s = len(students)
    no_sw = num2words(no_s)
    with app.app_context():
        section = render_template('category_block.html', cat=cat_obj, students=students, keys=keys,
                                  sizes=sizes, headers=headers)
    section = Template(section).render(no_s=no_s, no_sw=no_sw, session='{}/{}'.format(session, session + 1))

    return section


def get_100_to_400(acad_session, level=None):
    start_time = time.time()
    stud_categories = get_students_by_category(level, acad_session, get_all=True)
    data = ''
    for cat in stud_categories:
        data += load_cat_section(cat, stud_categories[cat], acad_session)

    template_dir = os.path.join(base_dir, 'templates', '100_400_senate_version.htm')
    with open(template_dir) as fd:
        template = fd.read()

    # First page data
    summary_data = []
    cat_totals = []
    for cat_obj in categories:
        cat = cat_obj.category
        cat_total = len(stud_categories[cat])
        summary_data.append([cat, cat_obj.description, cat_total])
        cat_totals.append(cat_total)
    cat_total_sum = sum(cat_totals)
    percent = list(map(lambda x: round(x / cat_total_sum * 100, 1), cat_totals))
    for idx in range(len(summary_data)):
        summary_data[idx].append(percent[idx])

    best_student = stud_categories['A'][0]

    params = {
        'session': '{}/{}'.format(acad_session, acad_session + 1),
        'session_2': '{}/{}'.format(acad_session, str(acad_session + 1)[-2:]),
        'dept': get_depat(),
        'level': level,
        'summary_data': summary_data,
        'cat_total_sum': cat_total_sum,
        'best_student': best_student
    }
    template = Template(template.replace('{data}', data))
    html = template.render(**params)
    file_name = secrets.token_hex(8) + '.pdf'
    pdfkit.from_string(html, os.path.join(cache_base_dir, file_name))
    print(f'Senate version generated in {time.time() - start_time} seconds')

    return send_from_directory(cache_base_dir, file_name, as_attachment=True)


def get_500(acad_session):
    level = 500
    pass


@access_decorator
def get(acad_session, level=None):
    if not level:
        level = (get_current_session() - acad_session) * 100

    if level == 500:
        return get_500(acad_session)
    else:
        return get_100_to_400(acad_session, level=level)
