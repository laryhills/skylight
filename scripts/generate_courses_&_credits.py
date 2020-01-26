import sqlite3
import os
import sys

start_session = 2003
curr_session = 2018

db_base_dir = os.path.join(os.path.dirname(__file__), '..', 'api', 'sms', 'database')
if not os.path.exists(os.path.join(db_base_dir, 'courses.db')): sys.exit('Run course_details.py first')
conn = sqlite3.connect(os.path.join(db_base_dir, 'courses.db'))
stmt = 'SELECT COURSE_CODE, COURSE_CREDIT, START_DATE, END_DATE, OPTIONS from courses{};'
courses = [conn.execute(stmt.format(x * 100)).fetchall() for x in range(1, 6)]
conn.close()


def generate_courses_and_credits_table(conn, session):
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE Courses(MODE_OF_ENTRY INTEGER PRIMARY_KEY, LEVEL100 TEXT, LEVEL200 TEXT, LEVEL300 TEXT, LEVEL400 TEXT, LEVEL500 TEXT);')
    cursor.execute('CREATE TABLE Credits(MODE_OF_ENTRY INTEGER PRIMARY_KEY, LEVEL100 INTEGER, LEVEL200 INTEGER, LEVEL300 INTEGER, LEVEL400 INTEGER, LEVEL500 INTEGER);')
    options = {}
    credits = [0,0,0,0,0]
    level_courses = ["","","","",""]
    for level in range(5):
        for course in courses[level][::-1]:
            code, credit, start_date, end_date, option = course
            if start_date <= session <= end_date:
                if option:
                    options[option] = (code, credit)
                else:
                    credits[level] += credit
                    level_courses[level] += code+','
        for opt in options:
            code, credit = options[opt]
            credits[level] += credit
            level_courses[level]+=code+','
        level_courses[level]=level_courses[level][:-1]
    cursor.execute('INSERT INTO Courses VALUES (?, ?, ?, ?, ?, ?);', [1]+level_courses)
    cursor.execute('INSERT INTO Credits VALUES (?, ?, ?, ?, ?, ?);', [1]+credits)
    de_level_courses, de_credits = level_courses[:], credits[:]
    de_credits[0], de_level_courses[0] = None, None
    de_credits[1] += 10
    de_level_courses[1] += ',GST111,GST112,GST121,GST122,GST123'
    cursor.execute('INSERT INTO Courses VALUES (?, ?, ?, ?, ?, ?);', [2]+de_level_courses)
    cursor.execute('INSERT INTO Credits VALUES (?, ?, ?, ?, ?, ?);', [2]+de_credits)
    conn.commit()


if __name__ == '__main__':
    for session in range(start_session, curr_session):
        curr_db = '{}-{}.db'.format(session, session + 1)
        conn = sqlite3.connect(os.path.join(db_base_dir, curr_db))
        generate_courses_and_credits_table(conn, session)
        conn.close()
    print('Done')
