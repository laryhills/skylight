import csv
import os

from flask import Flask, render_template, url_for
from flask_weasyprint import HTML, render_pdf
import itertools


app = Flask(__name__)
base_dir = os.path.dirname(__file__)
db_path = os.path.join(base_dir, 'database')


@app.route('/update/', defaults={'mat_no': 'ENG1503886', 'session': '2016'})
@app.route('/update/<mat_no>/<session>')
def get_name(mat_no, session):
    results = []
    row_number, column_number = 0, 1
    with open(os.path.join(base_dir,'templates', 'Score_Sheet.csv'), 'r') as scores:
        row = next(itertools.islice(csv.reader(scores), row_number, row_number + 1))
        print('1')
        if (row[column_number+2] == mat_no) and (row[column_number+1] == session):
            results.append((row[column_number], row[column_number+3]))
            print(results)
    return render_template('result_update.html', name=mat_no, results=results[0])


@app.route('/hello/', defaults={'name': 'World'})
@app.route('/hello/<name>/')
def hello_html(name):
    return render_template('result_update.html', name=name)


@app.route('/hello_<name>.pdf')
def hello_pdf(name):
    # Make a PDF straight from HTML in a string.
    html = render_template('result_update.html', name=name)
    return render_pdf(HTML(string=html))


if __name__ == '__main__':
    app.run(debug=True)
