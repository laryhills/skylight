import os
import sqlite3
from __init__ import db_base_dir

start_session = 2003
curr_session = 2019


def generate_grading_rule():
    for session in range(start_session, curr_session + 1):
        if 2013 <= session <= 2017:
            stmt = 'CREATE TABLE GradingRule (Rule TEXT PRIMARY KEY);'
            grade_weight_stmt = 'INSERT INTO GradingRule Values ("A 5 70,B 4 60,C 3 50,D 2 45,F 0 0")'
        else:
            stmt = 'CREATE TABLE GradingRule (Rule TEXT PRIMARY KEY);'
            grade_weight_stmt = 'INSERT INTO GradingRule Values ("A 5 70,B 4 60,C 3 50,D 2 45,E 1 40,F 0 0")'
        db_name = '{}-{}.db'.format(session, session + 1)
        conn = sqlite3.connect(os.path.join(db_base_dir, db_name))
        
        conn.execute(stmt)
        conn.execute(grade_weight_stmt)
        
        conn.commit()
        conn.close()


if __name__ == '__main__':
    generate_grading_rule()
    print('done')
