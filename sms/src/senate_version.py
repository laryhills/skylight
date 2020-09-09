import os
import time
import secrets
import pdfkit
from num2words import num2words
from jinja2 import Template
from flask import render_template, send_from_directory

from sms.src.users import access_decorator
from sms.src.script import get_students_details_by_category, get_final_year_students_by_category
from sms.models.master import Category, Category500
from sms.config import app, CACHE_BASE_DIR
from sms.src.utils import get_depat, get_num_of_prize_winners, get_entry_session_from_level, get_session_from_level

base_dir = os.path.dirname(__file__)
categories = Category.query.all()
categories_500 = Category500.query.all()

class_mapping = {
    '1': 'First Class Honours',
    '2.1': 'Second Class Honours (Upper Division)',
    '2.2': 'Second Class Honours (Lower Division)',
    '3': 'Third Class Honours',
    'pass': 'Pass',
}

options = {
        'page-size': 'A4',
        'margin-top': '.8in',
        'margin-bottom': '0.5in',
        'margin-left': '0.8in',
        'margin-right': '0.8in',
        'header-spacing': 6.0,
        'footer-right': '[date] [time]',
        'footer-center': '[page]/[toPage]',
        'footer-spacing': 3.0,
        'footer-font-size': 8
    }


def get_groups_dict():
    groups_dict = dict()
    for cat_obj in categories_500:
        if cat_obj.group in ['successful students', 'carryover students', 'prize winners']:
            if cat_obj.group == 'carryover students':
                groups_dict['referred students'] = [cat_obj.category, cat_obj.description, cat_obj.text]
            else:
                groups_dict[cat_obj.group] = [cat_obj.category, cat_obj.description, cat_obj.text]
        else:
            groups_dict[cat_obj.group] = [cat_obj.category, cat_obj.description]

    return groups_dict


def load_cat_section(cat, students, session):
    for cat_obj in categories:
        if cat_obj.category == cat:
            break
    sizes = [int(x) for x in cat_obj.sizes.split(',')]
    headers = cat_obj.headers.split(',')
    no_s = len(students)
    no_sw = num2words(no_s)
    keys = ['mat_no', 'name', 'credits_passed', 'credits_failed', 'outstanding_courses', 'gpa']
    with app.app_context():
        section = render_template('category_block.html', cat=cat_obj, students=students, keys=keys,
                                  sizes=sizes, headers=headers)
    section = Template(section).render(no_s=no_s, no_sw=no_sw, session='{}/{}'.format(session, session + 1))

    return section


def load_cat_section_500(cat, students, session):
    for cat_obj in categories_500:
        if cat_obj.category == cat:
            break
    sizes = [int(x) for x in cat_obj.sizes.split(',')]
    headers = cat_obj.headers.split(',')
    no_s = len(students)
    no_sw = num2words(no_s)
    keys = ['mat_no', 'name', 'remark']
    with app.app_context():
        section = render_template('category_block.html', cat=cat_obj, students=students, keys=keys,
                                  sizes=sizes, headers=headers)
    section = Template(section).render(no_s=no_s, no_sw=no_sw, session='{}/{}'.format(session, session + 1))

    return section


def generate_header(file_name, params):
    header_temp_path = os.path.join(CACHE_BASE_DIR, file_name + '_header.html')
    with app.app_context():
        header_template = render_template('senate_version_header.html', **params)
        open(header_temp_path, 'w').write(header_template)

    return header_temp_path


def get_100_to_400(entry_session, level):
    start_time = time.time()
    stud_categories = get_students_details_by_category(level, entry_session, get_all=True)
    data, acad_session = '', get_session_from_level(entry_session, level)
    for cat in stud_categories:
        data += load_cat_section(cat, stud_categories[cat], acad_session)

    template_dir = os.path.join(base_dir, '../templates', '100_400_senate_version.htm')
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
    try:
        percent = list(map(lambda x: round(x / cat_total_sum * 100, 1), cat_totals))
    except ZeroDivisionError:
        percent = [0] * len(cat_totals)
    for idx in range(len(summary_data)):
        summary_data[idx].append(percent[idx])

    lookup_order = ['successful students', 'carryover students', 'probating students']
    for group in lookup_order:
        for cat_obj in categories:
            if cat_obj.group == group: break
        cat = cat_obj.category
        if stud_categories[cat]:
            best_students, gpa = [], 0
            for stud_dets in stud_categories[cat]:
                stud_gpa = stud_dets['gpa']
                if stud_gpa > gpa:
                    gpa = stud_gpa
                    best_students = [stud_dets]
                elif stud_gpa == gpa:
                    best_students.append(stud_dets)
            break
    else:
        best_students = []

    session = entry_session + int(level / 100) - 1
    params = {
        'session': '{}/{}'.format(session, session + 1),
        'session_2': '{}/{}'.format(session, str(session + 1)[-2:]),
        'dept': get_depat(),
        'level': level,
        'summary_data': summary_data,
        'cat_total_sum': cat_total_sum,
        'best_students': best_students
    }

    header_params = {
        'dept': get_depat(),
        'level': level,
        'session': '{}/{}'.format(session, str(session + 1)[-2:]),
    }

    template = Template(template.replace('{data}', data))
    html = template.render(**params)
    file_name = secrets.token_hex(8) + '.pdf'
    options['header-html'] = generate_header(file_name, header_params)
    pdfkit.from_string(html, os.path.join(CACHE_BASE_DIR, file_name), options=options)
    print(f'Senate version generated in {time.time() - start_time} seconds')

    return send_from_directory(CACHE_BASE_DIR, file_name, as_attachment=True), 200


def get_500(entry_session):
    start_time = time.time()
    acad_session = get_session_from_level(entry_session, 500)
    all_students = get_final_year_students_by_category(entry_session, get_all=True)
    groups_dict = get_groups_dict()
    students_sum, total_students = dict(), 0
    percent_distribution = dict()

    # Sum of students
    for group in all_students:
        if group == 'successful students':
            students_sum[group] = []
            for grad_class in all_students['successful students']:
                studs_sum = len(all_students['successful students'][grad_class])
                students_sum[group].append(studs_sum)
                total_students += studs_sum
        else:
            students_sum[group] = len(all_students[group])
            total_students += students_sum[group]

    # Distribution of students by percent
    if total_students != 0:
        for group in students_sum:
            if group == 'successful students':
                percent_distribution['successful students'] = []
                for idx in range(len(students_sum['successful students'])):
                    percent_distribution['successful students'].append(round(students_sum['successful students'][idx] / total_students * 100, 1))
            else:
                percent_distribution[group] = round(students_sum[group] / total_students * 100, 1)
    else:
        percent_distribution = dict.fromkeys(all_students, 0)

    successful_students = all_students.pop('successful students')

    referred_students = all_students.pop('referred students')
    prize_winners = all_students.pop('prize winners')
    data = ''
    for group in all_students:
        category = groups_dict[group][0]
        data += load_cat_section_500(category, all_students[group], acad_session)

    template_dir = os.path.join(base_dir, '../templates', '500_senate_version.htm')
    with open(template_dir) as fd:
        template = fd.read()

    total_num_of_successful_students = sum(students_sum['successful students'])
    total_num_of_referred_students = students_sum['referred students']

    # Best student & prize winners
    best_students = []
    num_of_prize_winners = get_num_of_prize_winners()
    prize_winners = [''] * num_of_prize_winners
    for key in class_mapping:
        if successful_students[key]:
            gpa = 0
            cgpas = [0] * num_of_prize_winners
            for student in successful_students[key]:
                if student['gpa'] > gpa:
                    best_students = [student]
                    gpa = student['gpa']
                elif student['gpa'] == gpa:
                    best_students.append(student)

                min_cgpa = min(cgpas)
                idx = cgpas.index(min_cgpa)
                if student['cgpa'] > min_cgpa:
                    cgpas[idx] = student['cgpa']
                    prize_winners[idx] = student
                elif student['cgpa'] == min_cgpa:
                    # todo: find a way to resolve ties
                    pass
            break
    keys = list(class_mapping.keys())
    if not all(prize_winners) and keys[-1] != key:
        # Continue looping through successful_students
        idx = keys.index(key)
        for i in range(idx + 1, len(keys)):
            for student in successful_students[keys[i]]:
                min_cgpa = min(cgpas)
                idx = cgpas.index(idx)
                if student['cgpa'] > min_cgpa:
                    cgpas[idx] = student['cgpa']
                    prize_winners[idx] = student
                elif student['cgpa'] == min_cgpa:
                    # find a way to resolve ties
                    pass

    session = entry_session + 4
    params = {
        'session': session,
        'session_2': '{}/{}'.format(session, str(session + 1)[-2:]),
        'dept': get_depat(),
        'successful_students': successful_students,
        'referred_students': referred_students,
        'prize_winners': prize_winners,
        'class_mapping': class_mapping,
        'groups_dict': groups_dict,
        'total_students': total_students,
        'students_sum': students_sum,
        'percent_distribution': percent_distribution,
        'best_students': best_students
    }

    header_params = {
        'dept': get_depat(),
        'level': 500,
        'session': '{}/{}'.format(session, str(session + 1)[-2:]),
    }

    template = Template(template.replace('{data}', data))
    html = template.render(**params).replace('{{ no_s }}', str(total_num_of_successful_students)).replace(
        '{{ no_sw }}', num2words(total_num_of_successful_students))
    html = html.replace('{{ no_s }}', str(total_num_of_referred_students)).replace('{{ no_sw }}', num2words(
        total_num_of_referred_students))
    file_name = secrets.token_hex(8) + '.pdf'
    options['header-html'] = generate_header(file_name, header_params)
    pdfkit.from_string(html, os.path.join(CACHE_BASE_DIR, file_name), options=options)
    print(f'Senate version generated in {time.time() - start_time} seconds')

    return send_from_directory(CACHE_BASE_DIR, file_name, as_attachment=True), 200


@access_decorator
def get(acad_session, level):
    entry_session = get_entry_session_from_level(acad_session, level)

    if level == 500:
        return get_500(entry_session)
    else:
        return get_100_to_400(entry_session, level=level)
