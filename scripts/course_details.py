import os
import sqlite3
import pandas as pd


def build_db(conn):
    # Stores the courses by level
    for level in range(100, 600, 100):
        tbl_name = 'Courses{}'.format(level)
        curr_frame = frame[frame.COURSE_LEVEL == level]
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
