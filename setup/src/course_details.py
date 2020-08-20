import pandas as pd
import os
import sqlite3

from imports import db_base_dir, setup_data_dir


def build_db(conn):
    # Stores the courses by level
    for level in range(100, 200, 100):
        tbl_name = 'Courses'
        curr_frame = frame#[frame.COURSE_LEVEL == level]
        curr_frame['START_DATE'] = 1970
        curr_frame['END_DATE'] = 2999
        curr_frame['OPTIONS'] = 0
        curr_frame['ACTIVE'] = 1
        curr_frame['START_DATE'].where(curr_frame['COURSE_CODE'] != 'UBT400', 2012, inplace=True)
        optional_courses = ['MEE531', 'MEE541', 'MEE561', 'MEE581', 'MEE591']
        curr_frame['START_DATE'].where(~curr_frame['COURSE_CODE'].isin(['MEE505', 'MEE506']), 2009, inplace=True)
        curr_frame['OPTIONS'].where(~curr_frame['COURSE_CODE'].isin(optional_courses), 1, inplace=True)
        optional_courses_2 = ['MEE532', 'MEE542', 'MEE562', 'MEE582', 'MEE592']
        curr_frame['OPTIONS'].where(~curr_frame['COURSE_CODE'].isin(optional_courses_2), 2, inplace=True)
        curr_frame.drop(curr_frame[curr_frame['COURSE_CODE'] == 'MEE500'].index, inplace=True)
        curr_frame.to_sql(tbl_name, conn, index=False)#, if_exists='replace')
    conn.commit()


def build_options(conn):
    cursor = conn.cursor()
    optional_courses = ['MEE531', 'MEE541', 'MEE561', 'MEE581', 'MEE591']
    optional_courses_2 = ['MEE532', 'MEE542', 'MEE562', 'MEE582', 'MEE592']
    cursor.execute('CREATE TABLE Options(OPTIONS_GROUP INTEGER PRIMARY KEY, MEMBERS TEXT, DEFAULT_MEMBER TEXT);')
    cursor.execute('INSERT INTO Options VALUES (?, ?, ?);',[1, ','.join(optional_courses), optional_courses[0]])
    cursor.execute('INSERT INTO Options VALUES (?, ?, ?);',[2, ','.join(optional_courses_2), optional_courses_2[0]])
    conn.commit()


# Load the csv data
path = os.path.join(setup_data_dir, 'Course_Details.csv')
frame = pd.read_csv(path)

conn = sqlite3.connect(os.path.join(db_base_dir, 'courses.db'))
print('Building courses.db...')
build_db(conn)
build_options(conn)
conn.close()

print('done')
