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

from sms.config import app as current_app, CACHE_BASE_DIR
from sms.src import course_details, result_statement
from sms.src.course_reg_utils import get_optional_courses
from sms.src.results import get_results_for_acad_session
from sms.src.script import get_students_by_level
from sms.src.users import access_decorator
from sms.src.utils import multiprocessing_wrapper, get_degree_class, dictify, multisort, get_dept, \
    get_session_from_level

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

    index_to_display = 2 if raw_score else 3
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
    render_engine, file_format = (generate_pdf, 'pdf') if to_print else (generate_image, 'png')
    use_workers = True if len(html_names) > 1 else False
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
    dept = get_dept()
    dept_title_case = ' '.join(map(str.capitalize, dept.split(' ')))
    empty_value = ' '

    # get semester courses (with one placeholder option)
    level_courses = course_details.get_all(level=level, options=False)
    first_sem_courses = multisort([(x['code'], x['credit'], x['options']) for x in level_courses if
                                   x['semester'] == 1])
    second_sem_courses = multisort([(x['code'], x['credit'], x['options']) for x in level_courses if
                                    x['semester'] == 2])

    # get optional courses
    first_sem_options, second_sem_options = get_optional_courses(level)

    courses = {
        'first_sem': dictify(first_sem_courses + first_sem_options),
        'second_sem': dictify(second_sem_courses + second_sem_options)
    }
    students, len_first_sem_carrys, len_second_sem_carrys = enrich_mat_no_list(mat_nos, acad_session, level, courses)
    students = tuple(students.items())

    fix_table_column_width_error = 8 if first_sem_only else 4
    len_first_sem_carrys = max(len_first_sem_carrys, fix_table_column_width_error)
    len_second_sem_carrys = max(len_second_sem_carrys, fix_table_column_width_error)

    if first_sem_only or len_first_sem_carrys + len_second_sem_carrys < 18: pagination = 15
    elif len(second_sem_courses) == 1: pagination = 15
    else: pagination = 18

    iters = len(students) // pagination

    for ite in range(iters+1):
        left = ite * pagination
        right = (ite + 1) * pagination
        paginated_students = dict(students[left:right])

        with current_app.app_context():
            html = render_template(
                'broad_sheet.html', enumerate=enumerate, sum=sum, int=int, url_for=url_for, start_index=left,
                len_first_sem_carryovers=len_first_sem_carrys, len_second_sem_carryovers=len_second_sem_carrys,
                index_to_display=index_to_display, empty_value=empty_value, color_map=color_map,
                first_sem_courses=first_sem_courses, second_sem_courses=second_sem_courses,
                first_sem_options=first_sem_options, second_sem_options=second_sem_options,
                students=paginated_students, session=acad_session, level=level, first_sem_only=first_sem_only,
                dept_title_case=dept_title_case,
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
                     os.path.join(CACHE_BASE_DIR, file_dir, html_name.replace('html', file_format)),
                     options=options)


def generate_image(html_name, file_dir, file_format='png'):
    options = {
        'format': file_format,
        'enable-local-file-access': None,
        'quality': 50,
        'log-level': 'warn',
    }
    imgkit.from_file(os.path.join(CACHE_BASE_DIR, file_dir, html_name),
                     os.path.join(CACHE_BASE_DIR, file_dir, html_name.replace('html', file_format)),
                     options=options)


# ==============================================================================================
#                                  Utility functions
# ==============================================================================================

def get_filtered_student_by_level(acad_session, level=None):
    levels = [level] if level else list(range(100, 600, 100))
    students_by_level = {}
    for level in levels:
        associated_db = get_session_from_level(acad_session, level, True)
        students = get_students_by_level(associated_db, level)
        students_by_level[level] = sorted(students)
    return students_by_level


def enrich_mat_no_list(mat_nos, acad_session, level, level_courses):
    students = {}
    max_len_first_sem_carryovers = 0
    max_len_second_sem_carryovers = 0
    
    for mat_no in mat_nos:

        result_details = get_results_for_acad_session(mat_no, acad_session)
        if result_details[1] != 200: continue
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

        person = result_details['personal_info']
        result_details['othernames'] = person['othernames']
        result_details['surname'] = person['surname'] + ["", " (Miss)"][person["sex"] == 'F']
        result_details['grad_status'] = person['grad_status']
        result_details['cgpa'] = round(float(result_details['cgpa']), 2)
        result_details['degree_class'] = get_degree_class(mat_no, cgpa=result_details['cgpa'])

        # fetch previously passed level results (100 and 500 level)
        if (level_written > 500 and level == 500) or (level_written == 100 and person['is_symlink'] == 1):
            # todo: refactor this when symlinks has been updated to store history
            prev_written_courses = get_prev_level_results(mat_no, level, level_written, acad_session, level_courses)
            prev_written_courses['first_sem'].update(result_details['regular_courses']['first_sem'])
            prev_written_courses['second_sem'].update(result_details['regular_courses']['second_sem'])
            result_details['regular_courses'] = prev_written_courses

        # compute stats
        sem_tcp, sem_tcr, sem_tcf, failed_courses = sum_semester_credits(result_details, 3, 1)
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
            elif isinstance(credit, str): credit = int(credit.replace(' *', ''))

            if courses[course][grade_index] not in ['F', 'ABS', 'F *', 'ABS *']:
                tcp[index] += credit
            else:
                tcf[index] += credit
                failed_courses[index].append(course)
            tcr[index] += credit

    return tcp, tcr, tcf, failed_courses


def get_prev_level_results(mat_no, broadsheet_level, level_written, acad_session, level_courses):
    regular_courses = {'first_sem': {}, 'second_sem': {}}
    option = {'first_sem': '', 'second_sem': ''}
    results = {}

    levels = [broadsheet_level] if broadsheet_level == 100 else range(500, level_written, 100)
    res_from_stmt = result_statement.get(mat_no)['results']
    [results.update({res['session']: res}) for res in res_from_stmt if res['level'] in levels]

    for session in sorted(results.keys()):
        if session >= acad_session:
            continue
        for sem_idx, semester in enumerate(['first_sem', 'second_sem']):
            for index in range(len(results[session][semester])):
                course_dets = results[session][semester][index]
                course, course_dets = course_dets[1], list(course_dets[2:7])
                # add course
                if course in level_courses[semester]:  # and (course_dets[1] not in ['F', 'ABS']):
                    # add an asterisk to the score and grade to indicate it's out of session
                    course_dets[2] = str(course_dets[2]) + ' *'
                    course_dets[3] += ' *'
                    regular_courses[semester][course] = course_dets
                    # replace old option with new one if necessary
                    if level_courses[semester][course][1] > 0 and course != option[semester]:
                        if option[semester] != '': regular_courses[semester].pop(option[semester])
                        option[semester] = course
                results[session][semester][index] = dictify([[course] + course_dets])
    return regular_courses
