## Note: Entry Mode - 1 PUTME
##                    2 Direct Entry & Transfer
##                    3 Not so sure

import numpy as np
import pandas as pd
import os, sqlite3

# Load the csv data
if not os.path.exists(os.path.join(os.getcwd(), 'database')): os.mkdir('database')
path = os.path.join(os.getcwd(), 'data', 'Personal_Data.csv')
frame = pd.read_csv(path, dtype={'PHONE_NO': np.str})

def populate_db(conn, session):
    # 1, Account for entry_session & mode_of_entry
    # 2, Account for current level
    utme_frame = frame[(frame.SESSION_ADMIT == session) & (frame.MODE_OF_ENTRY == 1)]     # PUTME students
    de_frame = frame[(frame.SESSION_ADMIT == session + 1) & (frame.MODE_OF_ENTRY == 2)]     # Direct entry and tranfer students
    # Account for students with mode 0f entry == 3
    curr_frame = pd.concat([utme_frame, de_frame])
    curr_frame.to_sql('PersonalInfo', conn, index=False, if_exists='replace')
    conn.commit()

sessions = xrange(2003, 2018)
for session in sessions:
    curr_db = '{0}-{1}.db'.format(session, session + 1)
    conn = sqlite3.connect(os.path.join(os.getcwd(), 'database', curr_db))
    print 'Populating {}'.format(curr_db,)
    populate_db(conn, session)
    conn.close()

print 'done'