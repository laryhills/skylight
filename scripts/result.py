'''                         DESIGN ARCHITECTURE
Regular Stdents: All session results up to the current session are stored in the
                 entry session's database
Probating Students: Treated as regular students up until the session of probation before
                    all further results are stored in the new entry session's database
Carry overs:

     Results are stored in separate tables, one for each level, with the level's courses
     as fields and the scores as their values
     
     Example
     -------
     
     mat_no = ENG15xxxxx
    
    Table Result100
       MATN0   | PHY111 | PHY113 | CHM111 | ...
    -------------------------------------------
    ENG15xxxxx     68      24      84
'''

import os
import sqlite3
import pandas as pd

curr_session = 2018
sessions = range(2003, curr_session)
# Generate result tables
stmt = 'SELECT COURSE_CODE FROM Courses{}'
conn = sqlite3.connect(os.path.join(os.getcwd(), 'database', 'Courses.db'))
courses = [conn.execute(stmt.format(x)).fetchall() for x in range(100, 600, 100)]
conn.close()
for session in sessions:
    curr_db = '{}-{}.db'.format(session, session + 1)
    stmt = 'CREATE TABLE Result{}(MATNO TEXT, {})'
    conn = sqlite3.connect(os.path.join(os.getcwd(), 'database', curr_db))
    for result_session in range(session, session + 5):
        if result_session == curr_session: break
        course_list = [x[0] for x in courses[result_session - session]]
        arg = ' INTEGER, '.join(course_list[: -1]) + ' INTEGER, ' + course_list[-1] + ' INTEGER'
        try: conn.execute(stmt.format(((result_session - session + 1) * 100), arg))
        except sqlite3.OperationalError: pass
    conn.close()
print('Result table created')

# Load the data
db_base_dir = os.path.join(os.path.dirname(__file__), '..', 'api', 'sms', 'database')
# master database
path = os.path.join(db_base_dir, 'master.db')
conn = sqlite3.connect(path)
student_frame = pd.read_sql('SELECT * FROM Main', conn)
conn.close()
# Results
path = os.path.join(os.path.dirname(__file__), '..', 'data', 'Score_Sheet.csv')
result_frame = pd.read_csv(path)


def populate_db(conn, mat_no):
    # is_symlink, db = conn.execute('SELECT IS_SYMLINK, DATABASE FROM PersonalInfo WHERE MATNO = ?', mat_no).fetchone()
    # if is_symlink: pass
    curr_frame = result_frame[result_frame.MATNO == mat_no]
    curr_frame_group = curr_frame.groupby(by='SESSION')
    groups = [curr_frame_group.get_group(x) for x in curr_frame_group.groups]
    groups = sorted(groups, key=lambda x: x.SESSION.iloc[0])
    count = 0
    for group in groups:
        count += 1  # current level for regular students
        group.drop_duplicates(subset='COURSE_CODE', inplace=True)
        for num in range(1, group['SESSION'].iloc[0] - entry_session + 2):
            tbl_name = 'Result{}'.format(num * 100)
            level_result = group[group.COURSE_CODE.str.match(r'\w{3}%d\d{2}'%num)]
            if not level_result.COURSE_CODE.any(): continue
            
            # Account for CED300
            if num == 4: level_result.append(group[group.COURSE_CODE == 'CED300'], ignore_index=True)
            elif num == 3: level_result.drop(group[group.COURSE_CODE == 'CED300'].index, inplace=True)
            
            arg = entry_session + count - num
            new_db = '{}-{}.db'.format(arg, arg + 1)
            new_conn = sqlite3.connect(os.path.join(os.getcwd(), 'database',new_db))
            scores = pd.DataFrame([[mat_no] + level_result.SCORE.tolist()], columns = ['MATNO'] + level_result.COURSE_CODE.tolist())
            scores.to_sql(tbl_name, new_conn, index=False, if_exists='append')
            new_conn.commit(); new_conn.close()
    conn.commit()


print('Adding results...')
# Account for probating students
for index, series in student_frame.iterrows():
    curr_db = series.DATABASE
    entry_session = int(curr_db[:4])
    conn = sqlite3.connect(os.path.join(db_base_dir, curr_db))
    populate_db(conn, series.MATNO)
    conn.close()

print('done')
