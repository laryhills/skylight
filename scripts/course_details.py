import pandas as pd
import os
import sqlite3


def build_db(conn):
    # Stores the courses by level
    for level in range(100, 600, 100):
        tbl_name = 'Courses{}'.format(level)
        curr_frame = frame[frame.COURSE_LEVEL == level]
        curr_frame['START_DATE'] = 1970
        curr_frame['END_DATE'] = 2999
        curr_frame['OPTIONS'] = 0
        if level == 400:
            curr_frame['START_DATE'].where(curr_frame['COURSE_CODE'] != 'UBT400', 2012, inplace=True)
        elif level == 500:
            optional_courses = ['MEE531', 'MEE541', 'MEE561', 'MEE591', 'MEE581', 'MEE532', 'MEE542', 'MEE562', 'MEE592', 'MEE582']
            curr_frame['START_DATE'].where(~curr_frame['COURSE_CODE'].isin(['MEE505', 'MEE506']), 2009, inplace=True)
            curr_frame['OPTIONS'].where(~curr_frame['COURSE_CODE'].isin(optional_courses), 1, inplace=True)
            curr_frame.drop(curr_frame[curr_frame['COURSE_CODE'] == 'MEE500'].index, inplace=True)
        curr_frame.to_sql(tbl_name, conn, index=False, if_exists='replace')
    conn.commit()


# Load the csv data
db_base_dir = os.path.join(os.path.dirname(__file__), '..', 'api', 'sms', 'database')
path = os.path.join(os.path.dirname(__file__), '..', 'data', 'Course_Details.csv')
frame = pd.read_csv(path)

conn = sqlite3.connect(os.path.join(db_base_dir, 'courses.db'))
print('Building courses.db...')
build_db(conn)
conn.close()
print('done')
