from flask import Flask, render_template, url_for
from flask_weasyprint import HTML, render_pdf

app = Flask(__name__)


@app.route('/update/<mat_no>', defaults={'mat_no': 'ENG1503886'})
def get_name(mat_no):
    return render_template('result_update.html', name=mat_no)


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
