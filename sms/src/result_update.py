import os
import time
import pdfkit
import imgkit
import secrets
import threading
import concurrent.futures
from string import capwords
from zipfile import ZipFile, ZIP_DEFLATED
from flask import render_template, send_from_directory

from sms.src import result_statement
from sms.config import app as current_app, CACHE_BASE_DIR
from sms.src.users import access_decorator
from sms.src.ext.html_parser import split_html
from sms.src.utils import get_gpa_credits, get_level_weightings, get_carryovers

base_dir = os.path.dirname(__file__)
uniben_logo_path = 'file:///' + os.path.join(os.path.split(base_dir)[0], 'templates', 'static', 'Uniben_logo.png')


@access_decorator
def get(mat_no, raw_score=False, to_print=False):
    result_stmt = result_statement.get(mat_no)

    name = result_stmt['name'].replace(',', '')
    dept = capwords(result_stmt['depat'])
    dob = result_stmt['dob']
    mod = ['PUTME', 'DE(200)', 'DE(300)'][result_stmt['mode_of_entry'] - 1]
    entry_session = result_stmt['entry_session']
    grad_session = result_stmt['grad_session']
    results = multisort(remove_empty(result_stmt['results']))
    no_of_pages = len(results) + 1
    credits = result_stmt['credits']
    gpas, level_credits = get_gpa_credits(mat_no)
    gpas = list(map(lambda x: x if x else 0, gpas))
    level_credits = list(map(lambda x: x if x else 0, level_credits))
    level_weightings = get_level_weightings(result_stmt['mode_of_entry'])
    weighted_gpas = list(map(lambda x, y: round(x * y, 4), gpas, level_weightings))

    owed_courses = get_carryovers(mat_no, retJSON=False)
    owed_courses = owed_courses['first_sem'] + owed_courses['second_sem']
    gpa_check = [''] * 5
    for course in owed_courses:
        index = course[2] // 100 - 1
        gpa_check[index] = '*'

    with current_app.app_context():
        html = render_template('result_update_template.htm', uniben_logo_path=uniben_logo_path, any=any,
                               no_of_pages=no_of_pages, mat_no=mat_no, name=name, dept=dept, dob=dob,
                               mode_of_entry=mod, entry_session=entry_session, grad_session=grad_session,
                               results=results, credits=credits, gpas=gpas, level_weightings=level_weightings,
                               weighted_gpas=weighted_gpas, enumerate=enumerate, raw_score=raw_score,
                               level_credits=level_credits, gpa_check=gpa_check)

    def generate_img(args):
        i, page = args
        img = imgkit.from_string(page, None, options=options)
        arcname = file_name + '_{}.png'.format(i)
        with lock:
            zf.writestr(arcname, data=img)

    def generate_archive():
        with concurrent.futures.ThreadPoolExecutor() as executor:
            executor.map(generate_img, enumerate(htmls))

    if to_print:
        options = {
            'page-size': 'A4',
            'disable-smart-shrinking': None,
            'print-media-type': None,
            'margin-top': '0.6in',
            'margin-right': '0.5in',
            'margin-bottom': '0.6in',
            'margin-left': '0.5in',
            # 'minimum-font-size': 12,
            'encoding': "UTF-8",
            'enable-local-file-access': None,
            'no-outline': None,
            'log-level': 'warn',
            'dpi': 100,
        }
        file_name = secrets.token_hex(8) + '.pdf'
        start_time = time.time()
        pdfkit.from_string(html, os.path.join(CACHE_BASE_DIR, file_name), options=options)
        print(f'pdf generated in {time.time() - start_time} seconds')
        resp = send_from_directory(CACHE_BASE_DIR, file_name, as_attachment=True)
    else:
        options = {
            'format': 'png',
            'enable-local-file-access': None,
            'log-level': 'warn',
            'quality': 50,
        }
        file_name = secrets.token_hex(8)
        file_path = os.path.join(CACHE_BASE_DIR, file_name + '.zip')
        start_time = time.time()
        htmls = split_html(html)
        lock = threading.Lock()
        with ZipFile(file_path, 'w', ZIP_DEFLATED) as zf:
            generate_archive()
        print(f'{len(htmls)} images generated and archived in {time.time() - start_time} seconds')
        resp = send_from_directory(CACHE_BASE_DIR, file_name + '.zip', as_attachment=True)

    return resp, 200


def multisort(results):
    for session in range(len(results)):
        semesters = ['first_sem', 'second_sem'] if 'second_sem' in results[session] else ['first_sem']
        for semester in semesters:
            fail_indices = [ind for ind, crs in enumerate(results[session][semester]) if crs[5] in ['F', 'ABS']]
            fails = []
            if fail_indices:
                fail_indices = sorted(fail_indices, reverse=True)
                fails = [results[session][semester].pop(ind) for ind in fail_indices]

            results[session][semester] = sorted(results[session][semester], key=lambda x: x[1])
            results[session][semester] = sorted(results[session][semester], key=lambda x: x[1][3])

            if fails:
                fails = sorted(fails, key=lambda x: x[1])
                fails = sorted(fails, key=lambda x: x[1][3])
                results[session][semester].extend(fails)
    return results


def remove_empty(results):
    """
    This function is to remove result records which contain only "unusual results", that is, no course registration

    :param results:
    :return:
    """
    for index, result in enumerate(results):
        if not (result['first_sem'] or result['second_sem']):
            results[index] = []
    while [] in results:
        results.remove([])
    return results
