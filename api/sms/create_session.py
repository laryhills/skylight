import os
import sqlite3
from sms import utils

def create(session=utils.get_current_session()):
    base_dir = os.path.dirname(__file__)
    db_base_dir = os.path.join(base_dir, 'database')
    curr_db = '{}-{}.db'.format(session, session + 1)
    conn = sqlite3.connect(os.path.join(db_base_dir, curr_db))
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE PersonalInfo(MATNO TEXT PRIMARY KEY, SURNAME TEXT, OTHERNAMES TEXT, MODE_OF_ENTRY INTEGER, SESSION_ADMIT INTEGER, SESSION_GRADUATED REAL, CURRENT_LEVEL INTEGER, OPTION REAL, SEX TEXT, DATE_OF_BIRTH REAL, STATE_OF_ORIGIN TEXT, PHONE_NO TEXT, EMAIL_ADDRESS TEXT, SPONSOR_PHONE_NO REAL, SPONSOR_EMAIL_ADDRESS REAL, GRAD_STATUS REAL, PROBATED_TRANSFERRED INTEGER, IS_SYMLINK INTEGER, DATABASE TEXT);')
    cursor.execute('CREATE TABLE Courses(MODE_OF_ENTRY INTEGER PRIMARY KEY, LEVEL100 TEXT, LEVEL200 TEXT, LEVEL300 TEXT, LEVEL400 TEXT, LEVEL500 TEXT);')
    cursor.execute('CREATE TABLE Credits(MODE_OF_ENTRY INTEGER PRIMARY KEY, LEVEL100 INTEGER, LEVEL200 INTEGER, LEVEL300 INTEGER, LEVEL400 INTEGER, LEVEL500 INTEGER);')
    cursor.execute('CREATE TABLE SymLink(MATNO TEXT, DATABASE TEXT);')
    result_stmt = 'CREATE TABLE Result{}(MATNO TEXT PRIMARY KEY, {} CATEGORY TEXT);'
    course_reg_stmt = 'CREATE TABLE CourseReg{}(MATNO TEXT PRIMARY KEY, {} PROBATION INTEGER, OTHERS TEXT);'

    # Get courses to use in populating Resultx00, CourseRegx00, Courses, Credits columns
    conn_courses = sqlite3.connect(os.path.join(db_base_dir, 'courses.db'))
    courses_stmt = 'SELECT COURSE_CODE, COURSE_CREDIT, COURSE_SEMESTER, START_DATE, END_DATE, OPTIONS from Courses{};'
    courses = [conn_courses.execute(courses_stmt.format(x * 100)).fetchall() for x in range(1, 6)]
    conn_courses.close()

    # Populate fields and INSERT into DB
    options = {}
    level_credits = [0,0,0,0,0]
    de_level_credits = [0,0,0,0]
    de300_level_credits = [0,0,0]
    level_courses = [["",""],["",""],["",""],["",""],["",""]]
    de_level_courses = [["",""],["",""],["",""],["",""]]
    de300_level_courses = [["",""],["",""],["",""]]
    for level in range(5):
        args = ""
        for course in courses[level]:
            code, credit, semester, start_date, end_date, option = course
            if start_date <= (session+level-1) <= end_date:
                if option:
                    if option not in options:
                        options[option] = (code, credit, semester)
                else:
                    level_credits[level] += credit
                    level_courses[level][semester-1] += code+','
                args += (code + ' TEXT,')
        if level != 0:
            args += ' CARRYOVERS TEXT,'
        for opt in options:
            code, credit, semester = options[opt]
            level_credits[level] += credit
            level_courses[level][semester-1] += code+','
        level_courses[level][0]=level_courses[level][0][:-1]
        level_courses[level][1]=level_courses[level][1][:-1]
        cursor.execute(result_stmt.format((level+1)*100, args))
        cursor.execute(course_reg_stmt.format((level+1)*100, args))
    level_courses = [" ".join([lvl_course[0],lvl_course[1]]) for lvl_course in level_courses]
    de_level_courses, de300_level_courses = [None] + level_courses[1:], [None, None] + level_courses[2:]
    de_first_sem = ','.join(de_level_courses[1].split(' ')[0].split(',')+['GST111','GST112'])
    de_sec_sem = ','.join(de_level_courses[1].split(' ')[1].split(',')+['GST121','GST122','GST123'])
    de300_first_sem = ','.join(de300_level_courses[2].split(' ')[0].split(',')+['GST111','GST112'])
    de300_sec_sem = ','.join(de300_level_courses[2].split(' ')[1].split(',')+['GST121','GST122','GST123'])
    de_level_courses[1] = " ".join([de_first_sem, de_sec_sem])
    de300_level_courses[2] = " ".join([de300_first_sem, de300_sec_sem])
    de_level_credits = [None, level_credits[1]+10] + level_credits[2:]
    de300_level_credits = [None, None, level_credits[2]+10] + level_credits[3:]
    cursor.execute('INSERT INTO Courses VALUES (?, ?, ?, ?, ?, ?);', [1]+level_courses)
    cursor.execute('INSERT INTO Credits VALUES (?, ?, ?, ?, ?, ?);', [1]+level_credits)
    cursor.execute('INSERT INTO Courses VALUES (?, ?, ?, ?, ?, ?);', [2]+de_level_courses)
    cursor.execute('INSERT INTO Credits VALUES (?, ?, ?, ?, ?, ?);', [2]+de_level_credits)
    cursor.execute('INSERT INTO Courses VALUES (?, ?, ?, ?, ?, ?);', [3]+de300_level_courses)
    cursor.execute('INSERT INTO Credits VALUES (?, ?, ?, ?, ?, ?);', [3]+de300_level_credits)

    for level in range(5,8):
        args = 'CARRYOVERS TEXT,'
        cursor.execute(result_stmt.format((level+1)*100, args))
        cursor.execute(course_reg_stmt.format((level+1)*100, args))

    conn.commit()
    conn.close()
