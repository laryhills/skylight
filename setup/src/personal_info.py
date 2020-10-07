"""
Note: Entry Mode - 1 PUTME
                   2 Direct Entry(200)
                   3 Direct Entry(300)
"""

import numpy as np
import pandas as pd
import os
import sqlite3

from imports import db_base_dir, setup_data_dir

# Load the csv data
path = os.path.join(setup_data_dir, 'Personal_Data.csv')
frame = pd.read_csv(path, dtype={'PHONE_NO': np.str})

start_session = 2003
curr_session = 2019


def format_options(data):
    if isinstance(data, float): return np.nan
    return '{},{}2'.format(data, data[:-1])


def create_props():
    with open(os.path.join(os.path.dirname(__file__), 'props.sql')) as fd:
        master.executescript(fd.read())


def create_table_schema():
    # p_info_stmt = 'CREATE TABLE PersonalInfo(MATNO TEXT PRIMARY KEY, SURNAME TEXT, OTHERNAMES TEXT, MODE_OF_ENTRY ' \
    #               'INTEGER, SESSION_ADMIT INTEGER, SESSION_GRADUATED REAL, CURRENT_LEVEL INTEGER, OPTION REAL, ' \
    #               'SEX TEXT, DATE_OF_BIRTH REAL, STATE_OF_ORIGIN TEXT, LGA_OF_ORIGIN TEXT, PHONE_NO TEXT, ' \
    #               'EMAIL_ADDRESS TEXT, SPONSOR_PHONE_NO TEXT, SPONSOR_EMAIL_ADDRESS TEXT, GRAD_STATUS INTEGER, ' \
    #               'PROBATED_TRANSFERRED INTEGER, IS_SYMLINK INTEGER, DATABASE TEXT); '
    p_info_stmt = 'CREATE TABLE PersonalInfo(MATNO TEXT PRIMARY KEY, SURNAME TEXT, OTHERNAMES TEXT, MODE_OF_ENTRY ' \
                  'INTEGER, SESSION_ADMIT INTEGER, SESSION_GRADUATED INTEGER, CURRENT_LEVEL INTEGER, OPTION REAL, ' \
                  'SEX TEXT, DATE_OF_BIRTH REAL, STATE_OF_ORIGIN TEXT, LGA_OF_ORIGIN TEXT, PHONE_NO TEXT, ' \
                  'EMAIL_ADDRESS TEXT, SPONSOR_PHONE_NO TEXT, SPONSOR_EMAIL_ADDRESS TEXT, PROBATED_TRANSFERRED ' \
                  'INTEGER, IS_SYMLINK INTEGER, DATABASE TEXT);'
    sym_link_stmt = 'CREATE TABLE SymLink(MATNO TEXT PRIMARY KEY' + \
                    ''.join(map(lambda x: ', DATABASE_{} TEXT'.format(x), range(1, 9))) + ');'
    for session in range(start_session, curr_session + 1):
        curr_db = '{}-{}.db'.format(session, session + 1)
        conn = sqlite3.connect(os.path.join(db_base_dir, curr_db))
        conn.execute(p_info_stmt)
        conn.execute(sym_link_stmt)
        conn.close()
    print('PersonalInfo and SymLink table created')


def populate_db(conn, session):
    curr_frame = frame[frame.SESSION_ADMIT == session]
    curr_frame.drop_duplicates(subset='MATNO', inplace=True)
    del curr_frame['PASSPORT'], curr_frame['GRAD_STATUS']
    curr_frame['IS_SYMLINK'], curr_frame['DATABASE'] = 0, ''
    # other = curr_session - (curr_frame.CURRENT_LEVEL / 100)
    # other = other.map(lambda x: '%d-%d.db'%(x, x + 1))
    # curr_frame.IS_SYMLINK.where(curr_frame.CURRENT_LEVEL == ((curr_session - session) * 100), 1, inplace=True)
    # curr_frame.DATABASE.where(curr_frame.IS_SYMLINK == 0, other, inplace=True)
    curr_frame.OPTION = curr_frame.OPTION.apply(format_options)
    curr_frame['LGA_OF_ORIGIN'] = ''
    curr_frame.to_sql('PersonalInfo', conn, index=False, if_exists='append')
    conn.commit()

    master_frame = curr_frame[['MATNO', 'SURNAME']].copy()
    master_frame['DATABASE'] = curr_db
    master_frame.to_sql('Main', master, index=False, if_exists='append')
    master.commit()


# master database
master = sqlite3.connect(os.path.join(db_base_dir, 'master.db'))
try: master.execute('CREATE TABLE Main (MATNO TEXT PRIMARY KEY, SURNAME TEXT, DATABASE TEXT)')
except sqlite3.OperationalError: pass

create_table_schema()

sessions = range(start_session, curr_session + 1)
for session in sessions:
    curr_db = '{0}-{1}.db'.format(session, session + 1)
    conn = sqlite3.connect(os.path.join(db_base_dir, curr_db))
    print('Populating {}...'.format(curr_db))
    populate_db(conn, session)
    conn.close()

create_props()
master.close()
print('done')
