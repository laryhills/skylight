import sqlite3
import os
import sys

from imports import db_base_dir

start_session = 2003
# start_session = 2017
curr_session = 2019


if not os.path.exists(os.path.join(db_base_dir, 'courses.db')): sys.exit('Run course_details.py first')
conn = sqlite3.connect(os.path.join(db_base_dir, 'courses.db'))
stmt = 'SELECT COURSE_CODE, COURSE_CREDIT, COURSE_SEMESTER, START_DATE, END_DATE, OPTIONS from Courses where ' \
       'COURSE_LEVEL = {}; '
courses = [conn.execute(stmt.format(x * 100)).fetchall() for x in range(1, 6)]
conn.close()


def generate_courses_and_credits_table(conn, session):
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE Courses(MODE_OF_ENTRY INTEGER PRIMARY KEY, LEVEL100 TEXT, LEVEL200 TEXT, LEVEL300 '
                   'TEXT, LEVEL400 TEXT, LEVEL500 TEXT);')
    cursor.execute('CREATE TABLE Credits(MODE_OF_ENTRY INTEGER PRIMARY KEY, LEVEL100 INTEGER, LEVEL200 INTEGER, '
                   'LEVEL300 INTEGER, LEVEL400 INTEGER, LEVEL500 INTEGER);')
    options = {}
    _credits = [0, 0, 0, 0, 0]
    level_courses = [["", ""], ["", ""], ["", ""], ["", ""], ["", ""]]
    for level in range(5):
        for course in courses[level]:
            code, credit, semester, start_date, end_date, option = course
            if start_date <= session <= end_date:
                if option:
                    if option not in options:
                        options[option] = (code, credit, semester)
                else:
                    _credits[level] += credit
                    level_courses[level][semester-1] += code+','
        for opt in options:
            code, credit, semester = options[opt]
            _credits[level] += credit
            level_courses[level][semester-1] += code+','
        level_courses[level][0]=level_courses[level][0][:-1]
        level_courses[level][1]=level_courses[level][1][:-1]
    level_courses = [" ".join([lvl_course[0],lvl_course[1]]) for lvl_course in level_courses]
    cursor.execute('INSERT INTO Courses VALUES (?, ?, ?, ?, ?, ?);', [1]+level_courses)
    cursor.execute('INSERT INTO Credits VALUES (?, ?, ?, ?, ?, ?);', [1]+_credits)
    de_level_courses, de_credits = level_courses[:], _credits[:]
    de_credits[0], de_level_courses[0] = None, None
    de_credits[1] += 10
    de_first_sem, de_sec_sem = de_level_courses[1].split()
    de_first_sem += ',GST111,GST112'
    de_sec_sem += ',GST121,GST122,GST123'
    de_level_courses[1] = " ".join([de_first_sem, de_sec_sem])
    cursor.execute('INSERT INTO Courses VALUES (?, ?, ?, ?, ?, ?);', [2]+de_level_courses)
    cursor.execute('INSERT INTO Credits VALUES (?, ?, ?, ?, ?, ?);', [2]+de_credits)
    de300_level_courses, de300_credits = level_courses[:], _credits[:]
    de300_credits[0], de300_level_courses[0], de300_credits[1], de300_level_courses[1] = None, None, None, None
    de300_credits[2] += 10
    de300_first_sem, de300_sec_sem = de300_level_courses[2].split()
    de300_first_sem += ',GST111,GST112'
    de300_sec_sem += ',GST121,GST122,GST123'
    de300_level_courses[2] = " ".join([de300_first_sem, de300_sec_sem])
    cursor.execute('INSERT INTO Courses VALUES (?, ?, ?, ?, ?, ?);', [3]+de300_level_courses)
    cursor.execute('INSERT INTO Credits VALUES (?, ?, ?, ?, ?, ?);', [3]+de300_credits)
    conn.commit()


if __name__ == '__main__':
    for session in range(start_session, curr_session):
        curr_db = '{}-{}.db'.format(session, session + 1)
        conn = sqlite3.connect(os.path.join(db_base_dir, curr_db))
        generate_courses_and_credits_table(conn, session)
        conn.close()
    print('Done')
