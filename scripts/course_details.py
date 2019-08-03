import pandas as pd
import os, sqlite3

def build_db(conn):
    # Stores the courses by level
    for level in xrange(100, 600, 100):
        tbl_name = 'Courses{}'.format(level)
        curr_frame = frame[frame.COURSE_LEVEL == level]
        curr_frame.to_sql(tbl_name, conn, index=False, if_exists='replace')
    conn.commit()

# Load the csv data
if not os.path.exists(os.path.join(os.getcwd(), 'database')): os.mkdir('database')
path = os.path.join(os.getcwd(), 'data', 'Course_Details.csv')
frame = pd.read_csv(path)

conn = sqlite3.connect(os.path.join(os.getcwd(), 'database', 'courses.db'))
print 'Building courses.db'
build_db(conn)
conn.close()

print 'done'