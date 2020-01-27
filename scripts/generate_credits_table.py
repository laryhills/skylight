import sqlite3
import os
import sys

start_session = 2003
curr_session = 2018

db_base_dir = os.path.join(os.path.dirname(__file__), '..', 'api', 'sms', 'database')
if not os.path.exists(os.path.join(db_base_dir, 'courses.db')): sys.exit('Run course_details.py first')
conn = sqlite3.connect(os.path.join(db_base_dir, 'courses.db'))
stmt = 'SELECT COURSE_CODE, COURSE_CREDIT, START_DATE, END_DATE from courses{};'
courses = [conn.execute(stmt.format(x * 100)).fetchall() for x in range(1, 6)]
conn.close()


def generate_credits_table(conn, session):
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE Credits(MODE_OF_ENTRY INTEGER PRIMARY KEY, LEVEL100 INTEGER, LEVEL200 INTEGER, LEVEL300 INTEGER, LEVEL400 INTEGER, LEVEL500 INTEGER);')
    credits, level = [], 0
    for level_course in courses:
        level_credit = 0
        level += 1
        for course in level_course:
            if course[2] <= session and session <= course[3]:
                level_credit += course[1]
        if level == 5: level_credit -= (8 * 3)
        credits.append(level_credit)
    cursor.execute('INSERT INTO Credits VALUES (1, ?, ?, ?, ?, ?);', credits)
    credits[0] = 0
    credits[1] += 10
    cursor.execute('INSERT INTO Credits VALUES (2, ?, ?, ?, ?, ?);', credits)
    conn.commit()


if __name__ == '__main__':
    for session in range(start_session, curr_session):
        curr_db = '{}-{}.db'.format(session, session + 1)
        conn = sqlite3.connect(os.path.join(db_base_dir, curr_db))
        generate_credits_table(conn, session)
        conn.close()
    print('Done')
