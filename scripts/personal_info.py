## Note: Entry Mode - 1 PUTME
##                    2 Direct Entry(200)
##                    3 Direct Entry(300)

import numpy as np
import pandas as pd
import os
import sqlite3

# Load the csv data
db_base_dir = os.path.join(os.path.dirname(__file__), '..', 'api', 'sms', 'database')
path = os.path.join(os.path.dirname(__file__), '..', 'data', 'Personal_Data.csv')
frame = pd.read_csv(path, dtype={'PHONE_NO': np.str})

curr_session = 2018


def create_table_schema():
    p_info_stmt = 'CREATE TABLE PersonalInfo(MATNO TEXT PRIMARY KEY, SURNAME TEXT, OTHERNAMES TEXT, MODE_OF_ENTRY INTEGER, SESSION_ADMIT INTEGER, SESSION_GRADUATED REAL, CURRENT_LEVEL INTEGER, OPTION REAL, SEX TEXT, DATE_OF_BIRTH REAL, STATE_OF_ORIGIN TEXT, PHONE_NO TEXT, EMAIL_ADDRESS TEXT, SPONSOR_PHONE_NO REAL, SPONSOR_EMAIL_ADDRESS REAL, GRAD_STATUS REAL, PROBATED_TRANSFERRED INTEGER, IS_SYMLINK INTEGER, DATABASE TEXT);'
    #sym_link_stmt = '''CREATE TABLE SymLink(MATNO TEXT PRIMARY KEY, DATABASE TEXT); '''
    for session in range(2003, curr_session + 1):
        curr_db = '{}-{}.db'.format(session, session + 1)
        conn = sqlite3.connect(os.path.join(db_base_dir, curr_db))
        conn.execute(p_info_stmt)
        #conn.execute(sym_link_stmt)
        conn.close
    print('PersonalInfo and SymLink table created')


def populate_db(conn, session):
    curr_frame = frame[frame.SESSION_ADMIT == session]
    del curr_frame['PASSPORT']
    curr_frame['IS_SYMLINK'], curr_frame['DATABASE'] = 0, ''
    other = curr_session - (curr_frame.CURRENT_LEVEL / 100)
    other = other.map(lambda x: '%d-%d.db'%(x, x + 1))
    curr_frame.IS_SYMLINK.where(curr_frame.CURRENT_LEVEL == ((curr_session - session) * 100), 1, inplace=True)
    curr_frame.DATABASE.where(curr_frame.IS_SYMLINK == 0, other, inplace=True)
    curr_frame.to_sql('PersonalInfo', conn, index=False, if_exists='append')
    conn.commit()
    
    # Symbolic link
        # Regular students
    sym_links_frame = curr_frame[curr_frame.IS_SYMLINK == 1]
    sym_links_group = sym_links_frame.groupby(by='DATABASE')
    groups = [sym_links_group.get_group(x) for x in sym_links_group.groups]
    for group in groups:
        new_db = group['DATABASE'].iloc[0]
        new_conn = sqlite3.connect(os.path.join(os.getcwd(), 'database', new_db))
        group['DATABASE'] = curr_db
        df = group[['MATNO', 'DATABASE']].drop_duplicates(subset='MATNO')
        df.to_sql('SymLink', new_conn, index=False, if_exists='append')
    
        # Direct entry students
    de_frame = frame[(frame.SESSION_ADMIT == session + 1) & (frame.MODE_OF_ENTRY == 2)]
    de_frame['DATABASE'] = '{0}-{1}.db'.format(session + 1, session + 2)
    #de_frame.DATABASE.where(de_frame.CURRENT_LEVEL == ((curr_session + 1 - session) * 100), '{0}-{1}.db'.format(curr_session - (de_frame.CURRENT_LEVEL / 100), curr_session - (int(curr_frame.CURRENT_LEVEL) / 100) + 1), inplace=True)
    sym_de_frame = de_frame[['MATNO', 'DATABASE']].drop_duplicates(subset='MATNO')
    sym_de_frame.to_sql('SymLink', conn, index=False, if_exists='append')
    
    master_frame = curr_frame.MATNO.to_frame()
    master_frame['DATABASE'] = curr_db
    master_frame.to_sql('Main', master, index=False, if_exists='append')
    master.commit()


# master database
master = sqlite3.connect(os.path.join(db_base_dir, 'master.db'))
try: master.execute('CREATE TABLE Main (MATNO TEXT PRIMARY KEY, DATABASE TEXT)')
except sqlite3.OperationalError: pass

create_table_schema()

sessions = range(2003, curr_session)
for session in sessions:
    curr_db = '{0}-{1}.db'.format(session, session + 1)
    conn = sqlite3.connect(os.path.join(db_base_dir, curr_db))
    print('Populating {}...'.format(curr_db))
    populate_db(conn, session)
    conn.close()

master.close()
print('done')
