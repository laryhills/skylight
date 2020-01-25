import os
import sqlite3
import pandas as pd

curr_session = 2018
courses = []        # List of course codes
courses_dict = []   # List of course codes and credit dictionaries

db_base_dir = os.path.join(os.path.dirname(__file__), '..', 'api', 'sms', 'database')
if not os.path.exists(os.path.join(db_base_dir, 'master.db')):
    os.sys.exit('Run the personal_info.py script first')
if not os.path.exists(os.path.join(db_base_dir, 'courses.db')):
    os.sys.exit('Run the course_details.py script first')


def create_table_schema():
    global courses_dict, courses
    # Generate result and course reg tables
    stmt = 'SELECT COURSE_CODE, COURSE_CREDIT FROM Courses{}'
    conn = sqlite3.connect(os.path.join(db_base_dir, 'courses.db'))
    courses = [conn.execute(stmt.format(x)).fetchall() for x in range(100, 600, 100)]
    courses_dict = [dict(x) for x in courses]
    courses = [list(x.keys()) for x in courses_dict]
    conn.close()
    
    for course_list in courses[1:]:
        course_list.append('CARRYOVERS')

    sessions = range(2003, curr_session)
    for session in sessions:
        curr_db = '{}-{}.db'.format(session, session + 1)
        result_stmt = 'CREATE TABLE Result{}(MATNO TEXT PRIMARY_KEY, {}, CATEGORY TEXT)'
        course_reg_stmt = 'CREATE TABLE CourseReg{}(MATNO TEXT PRIMARY_KEY, {}, PROBATION INTEGER, OTHERS TEXT)'
        conn = sqlite3.connect(os.path.join(db_base_dir, curr_db))
        for result_session in range(session, session + 8):
            if result_session - session > 4:
                # spill over students
                arg = 'CARRYOVERS TEXT'
            else:
                course_list = [str(x) for x in courses[result_session - session]]
                arg = ' TEXT, '.join(course_list[:]) + ' TEXT'
            try:
                conn.execute(result_stmt.format(((result_session - session + 1) * 100), arg))
                conn.execute(course_reg_stmt.format(((result_session - session + 1) * 100), arg))
            except sqlite3.OperationalError: pass
        conn.close()
    print('Result and course reg tables created')


def generate_table_dtype():    
    result_dtype = []
    course_reg_dtype = []
    
    for num in range(8):
        if num > 4:
            result_dtype.append({'MATNO': 'TEXT', 'CARRYOVERS': 'TEXT', 'CATEGORY': 'TEXT'})
            course_reg_dtype.append({'MATNO': 'TEXT', 'CARRYOVERS': 'TEXT', 'PROBATION': 'INTEGER', 'OTHERS': 'TEXT'})
        else:
            course_list = courses[num]
            dtype = ['TEXT'] * len(course_list)
            tbl_dtype = dict(list(zip(course_list, dtype)))
            tbl_dtype['MATNO'] = 'TEXT'
            tbl_dtype['CATEGORY'] = 'TEXT'
            result_dtype.append(tbl_dtype.copy())
            del tbl_dtype['CATEGORY']
            tbl_dtype['PROBATION'] = 'INTEGER'
            tbl_dtype['OTHERS'] = 'TEXT'
            course_reg_dtype.append(tbl_dtype)
    
    return result_dtype, course_reg_dtype


# Master database
conn = sqlite3.connect(os.path.join(db_base_dir, 'master.db'))
student_frame = pd.read_sql('SELECT * FROM Main', conn)
conn.close()

# Loads the students results
path = os.path.join(os.path.dirname(__file__), '..', 'data', 'Score_Sheet.csv')
result_frame = pd.read_csv(path)


def total_credits(level, course_reg_df):
    total_credit = 0
    if level <= 5:
        reg_courses_df = course_reg_df[course_reg_df != 0].dropna(axis=1)
        if level == 1: course_codes = reg_courses_df.columns[1: -1]
        else:
            reg_courses_df['PROBATION'] = course_reg_df['PROBATION']
            course_codes = reg_courses_df.columns[1: -2]
        course_credit_dict = courses_dict[level - 1]
        for course_code in course_codes:
            total_credit += course_credit_dict[course_code]

    if level > 1:
        carryovers_courses = course_reg_df['CARRYOVERS'].tolist()[0].split(',')
        for course_code in carryovers_courses:
            if not course_code: break
            course_level = int(course_code[3] if course_code[:3] != 'CED' else 4)
            total_credit += courses_dict[course_level - 1][course_code]
    
    return total_credit


def failed_credits(entry_session, level, result_df):
    total_credits_failed = 0
    if level <= 5:
        course_credit_dict = courses_dict[level - 1]
        if level == 1: course_codes = result_df.columns[1:]
        else: course_codes = result_df.columns[1: -1]
        courses_df = result_df[course_codes]
        if entry_session <= 2013:
            failed_courses_df = courses_df[courses_df[course_codes] <= 39]
        else:
            failed_courses_df = courses_df[courses_df[course_codes] <= 44]
        failed_courses_df.dropna(axis=1, inplace=True)
        for course_code in failed_courses_df.columns:
            total_credits_failed += course_credit_dict[course_code]
    
    if level > 1:
        carryovers_courses_scores = result_df['CARRYOVERS'].tolist()[0].split(',')
        for course_score in carryovers_courses_scores:
            if not course_score: break
            course_code, score = course_score.split()
            if entry_session <= 2013:
                if float(score) <= 39:
                    course_level = int(course_code[3] if course_code[:3] != 'CED' else 4)
                    total_credits_failed += courses_dict[course_level - 1][course_code]
            else:
                if float(score) <= 44:
                    course_level = int(course_code[3] if course_code[:3] != 'CED' else 4)
                    total_credits_failed += courses_dict[course_level - 1][course_code]
    
    return total_credits_failed


def get_category(entry_session, level, result_df, course_reg_df):
    total_credits_failed = failed_credits(entry_session, level, result_df)
    total_credits_registered = total_credits(level, course_reg_df)
    total_credits_passed = float(total_credits_registered - total_credits_failed)
    if not total_credits_failed: return 'A'
    if level == 1 and entry_session == 2014:
        if total_credits_passed >= 36: return 'B'
        elif total_credits_passed >= 23 and total_credits_passed < 36: return 'C'
        else:
            bool_df = course_reg_df['PROBATION'] == 1
            if bool_df.all(): return 'E' # Handle condition for transfer
            else: return 'D'
    else:
        percent_passed = total_credits_passed / total_credits_registered * 100
        if percent_passed >= 50: return 'B'
        elif percent_passed >= 25 and percent_passed < 50: return 'C'
        else:
            bool_df = course_reg_df['PROBATION'] == 0
            if bool_df.all(): return 'D'
            else: return 'E'


def get_grade(score, entry_session):
    if not score: return ''
    if score >= 70: return 'A'
    elif score >= 60: return 'B'
    elif score >= 50: return 'C'
    elif score >= 45: return 'D'
    else:
        if entry_session >= 2013: return 'F'
        else:
            if score >= 40: return 'E'
            else: return 'F'


def store_unusual_students(mat_no, entry_session):
    fd = open(os.path.join(os.getcwd(), 'error.txt'), 'a')
    fd.write('{} ==> {}\n'.format(mat_no, entry_session))
    fd.close()


def populate_db(conn, mat_no, entry_session, mod):
    global result_dtype_glob, course_reg_dtype_glob
    # Loads all the student's results
    curr_frame = result_frame[result_frame.MATNO == mat_no]
    curr_frame_group = curr_frame.groupby(by='SESSION')
    groups = [curr_frame_group.get_group(x) for x in curr_frame_group.groups]
    groups = sorted(groups, key=lambda x: x.SESSION.iloc[0])
    levels = [groups[num].SESSION.iloc[0] for num in range(len(groups))]
    if not levels or levels[0] != entry_session or len(groups) > (9 - mod):
        store_unusual_students(mat_no, entry_session)
        return
    progressive_sum = int(len(levels) / 2.0 * (2 * levels[0] + len(levels) - 1))
    if sum(levels) != progressive_sum:
        store_unusual_students(mat_no, entry_session)
        return
    count, on_probation = mod - 1, 0
    for group in groups:
        count += 1
        group.drop_duplicates(subset='COURSE_CODE', inplace=True)
        result_dtype, course_reg_dtype = result_dtype_glob[count - 1], course_reg_dtype_glob[count - 1]
        
        if count == 4:
            group['COURSE_CODE'].replace('CED300', 'CED400', inplace=True)
        level_result = group[group.COURSE_CODE.str.match(r'\w{3}%d\d{2}'%count)]
        if count == 4:
            group['COURSE_CODE'].replace('CED400', 'CED300', inplace=True)
            level_result['COURSE_CODE'].replace('CED400', 'CED300', inplace=True)
        student_result = pd.DataFrame([[mat_no] + level_result.SCORE.tolist()], columns = ['MATNO'] + level_result.COURSE_CODE.tolist())
        if count > 1:
            carryovers = pd.concat([group, level_result]).drop_duplicates(subset='COURSE_CODE', keep=False)
            carryover_list = carryovers[['COURSE_CODE', 'SCORE']].values.tolist()
            student_result['CARRYOVERS'] = ','.join(list(['{} {}'.format(*x) for x in carryover_list]))
        
        course_reg_dtype_keys = list(course_reg_dtype.keys())
        if count > 1: course_reg_dtype_keys.remove('CARRYOVERS')
        course_reg_dtype_keys.remove('MATNO')
        course_reg_dtype_keys.remove('PROBATION')
        course_reg_dtype_keys.remove('OTHERS')
        course_reg_df = pd.DataFrame([[mat_no] + [1] * len(course_reg_dtype_keys)], columns=['MATNO'] + course_reg_dtype_keys)
        diff = [x for x in course_reg_dtype_keys if x not in student_result.columns]
        if diff:
            for course_code in diff:
                course_reg_df[course_code] = 0
        if count > 1:
            course_reg_df['CARRYOVERS'] = ','.join(carryovers['COURSE_CODE'].tolist())
        
        course_reg_df['PROBATION'] = on_probation
        student_result['CATEGORY'] = get_category(entry_session, count, student_result, course_reg_df)
        bool_df = student_result['CATEGORY'] == 'C'
        if bool_df.all() : on_probation = 1
        else: on_probation = 0
        
        for col_name, series in student_result.items():
            if col_name in ['MATNO', 'CATEGORY']: continue
            if col_name == 'CARRYOVERS' and bool(series[0]):
                items = series[0].split(',')
                new_items_list = []
                for item in items:
                    course, score = item.split()
                    try:
                        course, score = item.split()
                        score = int(float(score))
                        grade = get_grade(score, entry_session)
                    except ValueError:
                        course, score, grade = item, '0', 'F'
                    new_items_list.append(' '.join([course, str(score), grade]))
                series.replace(series[0], ','.join(new_items_list), inplace=True)
            else:
                try:
                    score = int(series[0])
                    grade = get_grade(score, entry_session)
                except ValueError:
                    score, grade = '0', 'F'
                series.replace(series[0], str(score) + ',' + grade, inplace=True)
        
         # store result and course_reg in the database
        try:
            result_tbl_name = 'Result{}'.format(count * 100)
            course_reg_tbl_name = 'CourseReg{}'.format(count * 100)
            student_result.to_sql(result_tbl_name, conn, index=False, if_exists='append', dtype=result_dtype)
            course_reg_df.to_sql(course_reg_tbl_name, conn, index=False, if_exists='append', dtype=course_reg_dtype)
        except sqlite3.OperationalError:
            pass
    
    conn.commit()


if __name__ == '__main__':
    create_table_schema()
    result_dtype_glob, course_reg_dtype_glob = generate_table_dtype()
    for index, series in student_frame.iterrows():
        print('Populating result for {}...'.format(series.MATNO))
        curr_db = series.DATABASE
        entry_session = int(curr_db[:4])
        conn = sqlite3.connect(os.path.join(db_base_dir, curr_db))
        mod = conn.execute('SELECT MODE_OF_ENTRY FROM PersonalInfo WHERE MATNO = ?', (series.MATNO,)).fetchone()[0]
        populate_db(conn, series.MATNO, entry_session, mod)
        conn.close()

print('done')
