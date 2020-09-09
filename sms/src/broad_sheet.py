import os.path
import shutil
from datetime import date
from secrets import token_hex
from time import perf_counter
from zipfile import ZipFile, ZIP_DEFLATED

import imgkit
import pdfkit
from colorama import init, Fore, Style
from flask import render_template, send_from_directory, url_for

# workaround for windows not passing app context to the child process
from sms.config import app as current_app

from sms.config import CACHE_BASE_DIR
from sms.src import course_details
from sms.src.course_reg_utils import process_personal_info, get_optional_courses
from sms.src.results import get_results_for_acad_session, get_results_for_level
from sms.src.script import get_students_by_level
from sms.src.users import access_decorator
from sms.src.utils import multiprocessing_wrapper, compute_degree_class, get_cgpa, dictify, multisort, \
    get_current_session, get_registered_courses, get_level

init()  # initialize colorama


@access_decorator
def get(acad_session, level=None, first_sem_only=False, raw_score=False, to_print=False):
    """
    This function gets the broadsheets for the academic session 'acad_session' for level 'level' if given
    else it gets for all levels during that session

    :param acad_session:
    :param level:
    :param first_sem_only:
    :param raw_score:
    :param to_print: If true generates pdf documents, else generates png images
    :return:
    """
    start = perf_counter()
    registered_students_for_session = get_filtered_student_by_level(acad_session, level)
    print('student list fetched in', perf_counter() - start)

    index_to_display = 0 if raw_score else 1
    file_dir = token_hex(8)
    zip_path = os.path.join(CACHE_BASE_DIR, file_dir)

    # create temporary folder to hold files
    if os.path.exists(os.path.join(CACHE_BASE_DIR, file_dir)):
        shutil.rmtree(file_dir, ignore_errors=True)
    os.makedirs(os.path.join(CACHE_BASE_DIR, file_dir), exist_ok=True)

    # render htmls
    t0 = perf_counter()
    context = (acad_session, index_to_display, file_dir, first_sem_only)
    use_workers = True if len(registered_students_for_session) > 1 else False
    multiprocessing_wrapper(render_html, registered_students_for_session.items(), context, use_workers)
    print('htmls rendered in', perf_counter() - t0, 'seconds')

    # generate pdfs or pngs
    t0 = perf_counter()
    html_names = [file_name for file_name in os.listdir(zip_path) if file_name.endswith('render.html')]
    use_workers = True if len(html_names) > 1 else False
    if to_print:
        render_engine = generate_pdf
        file_format = 'pdf'
    else:
        render_engine = generate_image
        file_format = 'png'
    multiprocessing_wrapper(render_engine, html_names, [zip_path, file_format], use_workers)
    print(f'{file_format}s generated in', perf_counter() - t0, 'seconds')

    # zip
    zip_file_name = 'broad-sheet_' + file_dir + '.zip'
    collect_renders_in_zip(file_dir, zip_file_name, file_format)

    print('===>> total generation done in', perf_counter() - start)
    resp = send_from_directory(os.path.join(CACHE_BASE_DIR, file_dir), zip_file_name, as_attachment=True)
    return resp, 200


def collect_renders_in_zip(file_dir, zip_file_name, file_format):
    zip_path = os.path.join(CACHE_BASE_DIR, file_dir)
    zip_file = os.path.join(CACHE_BASE_DIR, file_dir, zip_file_name)
    with ZipFile(zip_file, 'w', ZIP_DEFLATED) as zf:
        render_names = sorted([file_name for file_name in os.listdir(zip_path) if file_name.endswith('.' + file_format)])
        for render_name in render_names:
            try:
                pdf = open(os.path.join(zip_path, render_name), 'rb').read()
                zf.writestr(render_name, pdf)
            except Exception as e:
                pass


def render_html(item, acad_session, index_to_display, file_dir, first_sem_only=False):
    level, mat_nos = item
    color_map = {'F': 'red', 'F *': 'red', 'ABS': 'blue', 'ABS *': 'blue'}
    empty_value = ' '

    # get semester courses (with one placeholder option)
    level_courses = course_details.get_all(level=level, options=False)
    first_sem_courses = multisort([(x['course_code'], x['course_credit'], x['options']) for x in level_courses if
                                   x['course_semester'] == 1])
    second_sem_courses = multisort([(x['course_code'], x['course_credit'], x['options']) for x in level_courses if
                                    x['course_semester'] == 2])

    # get optional courses
    first_sem_options, second_sem_options = get_optional_courses(level)

    courses = {
        'first_sem': dictify(first_sem_courses + first_sem_options),
        'second_sem': dictify(second_sem_courses + second_sem_options)
    }
    students, len_first_sem_carryovers, len_second_sem_carryovers = enrich_mat_no_list(
        mat_nos, acad_session, level, courses)
    students = tuple(students.items())

    fix_table_column_width_error = 7 if first_sem_only else 4

    len_first_sem_carryovers = max(len_first_sem_carryovers, fix_table_column_width_error)
    len_second_sem_carryovers = max(len_second_sem_carryovers, fix_table_column_width_error)

    if first_sem_only or len_first_sem_carryovers + len_second_sem_carryovers < 18: pagination = 15
    elif len(second_sem_courses) == 1: pagination = 15
    else: pagination = 18

    iters = len(students) // pagination

    for ite in range(iters+1):
        left = ite * pagination
        right = (ite + 1) * pagination
        if right <= len(students):
            paginated_students = dictify(students[left:right])
        else:
            paginated_students = dictify(students[left:])

        with current_app.app_context():
            html = render_template(
                'broad_sheet.html', enumerate=enumerate, sum=sum, int=int, url_for=url_for, start_index=left,
                len_first_sem_carryovers=len_first_sem_carryovers, len_second_sem_carryovers=len_second_sem_carryovers,
                index_to_display=index_to_display, empty_value=empty_value, color_map=color_map,
                first_sem_courses=first_sem_courses, second_sem_courses=second_sem_courses,
                first_sem_options=first_sem_options, second_sem_options=second_sem_options,
                students=paginated_students, session=acad_session, level=level, first_sem_only=first_sem_only,
            )
            open(os.path.join(CACHE_BASE_DIR, file_dir, '{}_{}_render.html'.format(level, ite + 1)), 'w').write(html)


def generate_pdf(html_name, file_dir, file_format='pdf'):
    page = html_name.split('_')[1]
    footer_name = html_name.replace('render', 'footer')
    current_date = date.today().strftime("%A, %B %e, %Y")

    # render the broadsheet footer
    with current_app.app_context():
        footer_html = render_template('broad_sheet_footer.html', page=page, current_date=current_date)
        open(os.path.join(CACHE_BASE_DIR, file_dir, footer_name), 'w').write(footer_html)

    options = {
        'footer-html': os.path.join(CACHE_BASE_DIR, file_dir, footer_name),
        'page-size': 'A3',
        'orientation': 'landscape',
        'margin-top': '0.5in',
        'margin-right': '0.3in',
        'margin-bottom': '1.5in',
        'margin-left': '0.3in',
        # 'disable-smart-shrinking': None,
        'enable-local-file-access': None,
        'print-media-type': None,
        'no-outline': None,
        'dpi': 100,
        'log-level': 'warn',  # error, warn, info, none
    }
    pdfkit.from_file(os.path.join(CACHE_BASE_DIR, file_dir, html_name),
                     os.path.join(CACHE_BASE_DIR, file_dir, html_name[:-5] + '.' + file_format),
                     options=options)


def generate_image(html_name, file_dir, file_format='png'):
    options = {
        'format': file_format,
        'enable-local-file-access': None,
        'quality': 50,
        'log-level': 'warn',
    }
    imgkit.from_file(os.path.join(CACHE_BASE_DIR, file_dir, html_name),
                     os.path.join(CACHE_BASE_DIR, file_dir, html_name[:-5] + '.' + file_format),
                     options=options)


# ==============================================================================================
#                                  Utility functions
# ==============================================================================================

def get_filtered_student_by_level(acad_session, level=None):
    levels = [level] if level else list(range(100, 600, 100))
    students_by_level = {}
    for level in levels:
        associated_db = acad_session - level//100 + 1
        students = get_students_by_level(associated_db, level)
        # students = list(filter(lambda mat: get_level_at_acad_session(mat, acad_session) == level, students))
        students_by_level[level] = sorted(students)
    return students_by_level


# def get_level_at_acad_session(mat_no, acad_session):
#     if acad_session == get_current_session():
#         return get_level(mat_no)
#     c_reg = get_registered_courses(mat_no)
#     for key in range(800, 0, -100):
#         if c_reg[key]['course_reg_session'] and c_reg[key]['course_reg_session'] == acad_session:
#             return c_reg[key]['course_reg_level']
#     return ''


def enrich_mat_no_list(mat_nos, acad_session, level, level_courses):
    students = {}
    max_len_first_sem_carryovers = 0
    max_len_second_sem_carryovers = 0
    
    for mat_no in mat_nos:

        result_details = get_results_for_acad_session(mat_no, acad_session)

        if result_details[1] != 200:
            # print(Fore.RED + mat_no, 'has no results' + Style.RESET_ALL)
            continue

        result_details = result_details[0]
        level_written = result_details['level_written']

        if (level_written != level) and not (level_written > 500 and level == 500):
            # print(mat_no, "result level", result_details[0]['level_written'], '!=', level)
            continue

        # remove students with no course_reg (only has results in 'unusual_results')
        for key in ['regular_courses', 'carryovers']:
            if result_details[key]['first_sem'] or result_details[key]['second_sem']: break
        else:
            print(Fore.RED + mat_no, 'has no course_reg' + Style.RESET_ALL)
            continue

        personal_info = process_personal_info(mat_no)
        result_details['othernames'] = personal_info['othernames']
        result_details['surname'] = personal_info['surname']
        result_details['grad_status'] = personal_info['grad_status']
        result_details['cgpa'] = round(get_cgpa(mat_no), 2)
        result_details['degree_class'] = compute_degree_class(mat_no, cgpa=result_details['cgpa'])

        # fetch previously passed level results (100 and 500 level)
        if level_written > 500 and level == 500:
            # add the previously passed courses for spill students
            passed_500_courses = get_previously_passed_level_result(mat_no, level, level_written, acad_session, level_courses)
            passed_500_courses['first_sem'].update(result_details['regular_courses']['first_sem'])
            passed_500_courses['second_sem'].update(result_details['regular_courses']['second_sem'])
            result_details['regular_courses'] = passed_500_courses

        elif level_written == 100 and personal_info['is_symlink'] in [1, '1']:
            # todo: refactor this when symlinks has been updated to store history
            # add the previously passed courses for 100 level probation students
            passed_100_courses = get_previously_passed_level_result(mat_no, level, level_written, acad_session, level_courses)
            passed_100_courses['first_sem'].update(result_details['regular_courses']['first_sem'])
            passed_100_courses['second_sem'].update(result_details['regular_courses']['second_sem'])
            result_details['regular_courses'] = passed_100_courses

        # compute stats
        sem_tcp, sem_tcr, sem_tcf, failed_courses = sum_semester_credits(result_details, grade_index=1, credit_index=2)
        result_details['semester_tcp'] = sem_tcp
        result_details['semester_tcr'] = sem_tcr
        result_details['semester_tcf'] = sem_tcf
        result_details['sem_failed_courses'] = failed_courses

        if len(result_details['carryovers']['first_sem']) > max_len_first_sem_carryovers:
            max_len_first_sem_carryovers = len(result_details['carryovers']['first_sem'])

        if len(result_details['carryovers']['second_sem']) > max_len_second_sem_carryovers:
            max_len_second_sem_carryovers = len(result_details['carryovers']['second_sem'])

        students[mat_no] = result_details
    return students, max_len_first_sem_carryovers, max_len_second_sem_carryovers


def sum_semester_credits(result_details, grade_index, credit_index):
    tcp = [0, 0]  # total credits passed
    tcr = [0, 0]  # total credits registered
    tcf = [0, 0]  # total credits failed
    failed_courses = [[], []]

    for index, sem in enumerate(['first_sem', 'second_sem']):
        courses = {**result_details['regular_courses'][sem], **result_details['carryovers'][sem]}
        for course in courses:
            credit = courses[course][credit_index]
            if credit == '': continue
            elif isinstance(credit, str) and credit != '': credit = int(credit.replace(' *', ''))

            if courses[course][grade_index] not in ['F', 'ABS', 'F *', 'ABS *']:
                tcp[index] += credit
            else:
                tcf[index] += credit
                failed_courses[index].append(course)
            tcr[index] += credit

    # test conformity btw results and tcr, tcp columns
    # course_reg = get_course_reg_at_acad_session(result_details['session_written'], mat_no=result_details['mat_no'])
    # if course_reg and (sum(tcp) != result_details['tcp'] or sum(tcr) != course_reg['tcr']):
    #     print('{}AssertionError: {} ==> tcp: {:>2} != {:>2}; tcr: {:>2} != {:>2}'.format(Fore.RED, Style.RESET_ALL
    #           + result_details['mat_no'], sum(tcp), result_details['tcp'], sum(tcr), course_reg['tcr']))

    return tcp, tcr, tcf, failed_courses


def get_previously_passed_level_result(mat_no, broadsheet_level, level_written, acad_session, level_courses):
    regular_courses = {'first_sem': {}, 'second_sem': {}}
    option = {'first_sem': '', 'second_sem': ''}
    results = {}

    levels = [broadsheet_level] if broadsheet_level == 100 else range(500, level_written, 100)
    for level in levels:
        results.update(get_results_for_level(mat_no, level)[0])

    for session in sorted(results.keys()):
        if session >= acad_session:
            continue
        for key in ['regular_courses', 'carryovers']:
            for semester in ['first_sem', 'second_sem']:
                for course in results[session][key][semester]:
                    course_dets = results[session][key][semester][course]
                    # add course
                    if course in level_courses[semester]:  # and (course_dets[1] not in ['F', 'ABS']):
                        # add an asterisk to the score and grade to indicate it's out of session
                        course_dets[0] += ' *'
                        course_dets[1] += ' *'
                        regular_courses[semester][course] = course_dets
                        # replace old option with new one if necessary
                        if level_courses[semester][course][1] > 0 and course != option[semester]:
                            if option[semester] != '': regular_courses[semester].pop(option[semester])
                            option[semester] = course
    return regular_courses

