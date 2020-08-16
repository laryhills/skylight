import os
import sqlite3

from imports import db_base_dir

start_session = 2003
curr_session = 2019

class_of_degree = {
    'First class honours': '4.50,5.00',
    'Second class honours (upper)': '3.50,4.4999',
    'Second class honours (lower)': '2.40,3.4999',
    'Third class honours': '1.50,2.3999',
    'Pass': '1.00,1.4999',
    'Fail': '0,0.9999'
}


def generate_db():
    for session in range(start_session, curr_session + 1):
        curr_db = '{}-{}.db'.format(session, session + 1)
        conn = sqlite3.connect(os.path.join(db_base_dir, curr_db))
        stmt = 'CREATE TABLE DegreeClass(Class PRIMARY_KEY TEXT, Limits TEXT);'
        conn.execute(stmt)
        stmt = 'INSERT INTO DegreeClass VALUES (?, ?);'
        for cls, limit in class_of_degree.items():
            conn.execute(stmt, (cls, limit))
        conn.commit()
        conn.close()


if __name__ == '__main__':
    generate_db()

    print('Done')
