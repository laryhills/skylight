import os
import secrets
import pdfkit
import imgkit
import time
import threading
import concurrent.futures
from string import capwords
from zipfile import ZipFile, ZIP_DEFLATED
from flask import render_template, send_from_directory
from sms import result_statement
from sms.config import app, cache_base_dir
from sms.utils import get_gpa_credits, get_level_weightings
from sms.users import access_decorator
from sms.html_parser import split_html


base_dir = os.path.dirname(__file__)
uniben_logo_path = 'file:///' + os.path.join(base_dir, 'templates', 'static', 'Uniben_logo.png')

@access_decorator
def get(mat_no, raw_score=True, to_print=False):
    result_stmt = result_statement.get(mat_no, 0)

    no_of_pages = len(result_stmt['results']) + 1
    name = result_stmt['name'].replace(',', '')
    depat = capwords(result_stmt['depat'])
    dob = result_stmt['dob']
    mod = ['PUTME', 'DE(200)', 'DE(300)'][result_stmt['mode_of_entry'] - 1]
    entry_session = result_stmt['entry_session']
    grad_session = result_stmt['grad_session']
    results = result_stmt['results']
    credits = result_stmt['credits']
    gpas, level_credits = get_gpa_credits(mat_no)
    gpas = list(map(lambda x: x if x else 0, gpas))
    level_credits = list(map(lambda x: x if x else 0, level_credits))
    level_weightings = get_level_weightings(result_stmt['mode_of_entry'])
    weighted_gpas = list(map(lambda x, y: round(x * y, 4), gpas, level_weightings))

    with app.app_context():
        html = render_template('student_update_template.htm', uniben_logo_path=uniben_logo_path,
                               no_of_pages=no_of_pages, mat_no=mat_no, name=name, depat=depat, dob=dob,
                               mode_of_entry=mod, entry_session=entry_session, grad_session=grad_session,
                               results=results, credits=credits, gpas=gpas, level_weightings=level_weightings,
                               weighted_gpas=weighted_gpas, enumerate=enumerate, raw_score=raw_score,
                               level_credits=level_credits)

    options = {
        'page-size': 'A4',
        'print-media-type': None,
        'margin-top': '0.5in',
        'margin-right': '0.5in',
        'margin-bottom': '0.5in',
        'margin-left': '0.5in',
        'minimum-font-size': 15
    }

    def generate_img(args):
        i, page = args
        img = imgkit.from_string(page, None)
        arcname = file_name + '_{}.png'.format(i)
        with lock:
            zf.writestr(arcname, data=img)

    def generate_archive():
        with concurrent.futures.ThreadPoolExecutor() as executor:
            executor.map(generate_img, enumerate(htmls))

    if to_print:
        file_name = secrets.token_hex(8) + '.pdf'
        start_time = time.time()
        pdfkit.from_string(html, os.path.join(cache_base_dir, file_name), options=options)
        print(f'pdf generated in {time.time() - start_time} seconds')
        resp = send_from_directory(cache_base_dir, file_name, as_attachment=True)
    else:
        file_name = secrets.token_hex(8)
        file_path = os.path.join(cache_base_dir, file_name + '.zip')
        start_time = time.time()
        htmls = split_html(html)
        lock = threading.Lock()
        with ZipFile(file_path, 'w', ZIP_DEFLATED) as zf:
            generate_archive()
        print(f'{len(htmls)} images generated and archived in {time.time() - start_time} seconds')
        resp = send_from_directory(cache_base_dir, file_name + '.zip', as_attachment=True)

    return resp
