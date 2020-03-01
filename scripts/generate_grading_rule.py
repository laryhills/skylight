import os
import sqlite3

start_session = 2003
curr_session = 2019

db_base_dir = os.path.join(os.path.dirname(__file__), '..', 'api', 'sms', 'database')


def generate_grading_rule():
    for session in range(start_session, curr_session + 1):
        if 2013 <= session <= 2017:
            stmt = 'CREATE TABLE GradingRule (Rule TEXT);'
            grade_weight_stmt = 'INSERT INTO GradingRule Values ("A 5,B 4,C 3,D 2,F 0")'
        else:
            stmt = 'CREATE TABLE GradingRule (Rule TEXT);'
            grade_weight_stmt = 'INSERT INTO GradingRule Values ("A 5,B 4,C 3,D 2,E 1,F 0")'
        db_name = '{}-{}.db'.format(session, session + 1)
        conn = sqlite3.connect(os.path.join(db_base_dir, db_name))
        
        conn.execute(stmt)
        conn.execute(grade_weight_stmt)
        
        conn.commit()
        conn.close()


if __name__ == '__main__':
    generate_grading_rule()
    print('done')
