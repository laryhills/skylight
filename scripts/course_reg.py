'''         STRUCTURE
    *database_name.db
    *    CourseReg100
    *    CouresReg200
    *    CouresReg300
    *    CouresReg400
    *    CouresReg500
'''
## 100 level fields - [session(int), course_1(int), course_2(int), ..., Fees(int), Probation(int), Others(str)]
## 200 - 500 level fields - [session(int), CarryOver(list), course_1(int), course_2(int), ..., Fees(int), Probation(int), Others(str)]

import os
import glob
from numpy import nan
import pandas as pd
import sqlite3


def remove_na(row):
    for num in range(row.count(nan)): row.remove(nan)
    return row


def populate_table(conn, reg_session, session):
    tbl_name = 'CourseReg{0}00'.format(reg_session - session + 1,)  # table name
    frame = frames[reg_session - session]
    curr_frame = frame[frame.MATNO.apply(lambda x: 'ENG' + str(session)[-2:] in x)]     # Filters the required session's data
    if reg_session > session:   # Accounts for the carry over field for 200 to 500 level
        num = 10 if (reg_session - session + 1 == 4) else 20
        carry_overs_frame = curr_frame.iloc[:, 2:num + 2]
        curr_frame = curr_frame.drop(curr_frame.iloc[:, 2:num + 2].columns, axis=1)
        carry_overs_frame.dropna(axis=1, how='all', inplace=True)
        carry_overs = carry_overs_frame.values.tolist()
        curr_frame['CARRYOVER'] = [str(remove_na(x)) for x in carry_overs]
    
    curr_frame.to_sql(tbl_name, conn, index=False, if_exists='replace')
    frames[reg_session - session] = frame.drop(curr_frame.index)     # Frees up memory


def build_db(conn, session):
    cursor = conn.cursor()
    for reg_session in range(session, session + 5):
        if reg_session > 2017: break
        header = list(frames[reg_session - session].columns)    # List of table fields
        if reg_session == session:  # 100 level
            stmt = 'CREATE TABLE CourseReg{0}00('.format(reg_session - session + 1,) + ','.join([x + ' INTEGER' for x in header[:-1]]) + ',{} TEXT'.format(header[-1]) + ')'
        else:   # 200 - 500 level
            header = [header[0]] + ['CARRYOVER'] + header[header.index('J') + 1:] if (reg_session - session + 1 == 4) else [header[0]] + ['CARRYOVER'] + header[header.index('T') + 1:]
            stmt = 'CREATE TABLE CourseReg{0}00({1} INTEGER, {2} TEXT,'.format(reg_session - session + 1, header[0], header[1]) + ','.join([x + ' INTEGER' for x in header[2:-1]]) + ',{} TEXT'.format(header[-1]) + ')'
        try:
            print('{0}: Working on CourseReg{1}00 table'.format(curr_db, reg_session - session + 1))
            cursor.execute(stmt)   # Creates the database table
        except sqlite3.OperationalError as err: print(err)
        try: populate_table(conn, reg_session, session)     # Populates the database table
        except sqlite3.OperationalError as err: print(err)
    conn.commit()


db_base_dir = os.path.join(os.path.dirname(__file__), '..', 'api', 'sms', 'database')
paths = glob.glob(os.path.join(os.path.dirname(__file__), '..', 'data', '[1-5]*.csv'))    # List of couse reg paths

# Read the course reg data
frames = []
for path in paths:
    frames.append(pd.read_csv(path))    # Loads all the csv data

sessions = range(2009, 2018)
for session in sessions:
    curr_db = '{0}-{1}.db'.format(session, session + 1)
    conn = sqlite3.connect(os.path.join(db_base_dir, curr_db))
    build_db(conn, session)
    conn.close()

print('done')
