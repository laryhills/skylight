import os
import sqlite3
import pandas as pd

start_session = 2003
#start_session = 2017
curr_session = 2019
courses = []        # List of course codes
courses_dict = []   # List of course codes and credit dictionaries
num_probation = 0

db_base_dir = os.path.join(os.path.dirname(__file__), '..', 'api', 'sms', 'database')
if not os.path.exists(db_base_dir) and not os.path.exists(os.path.join(db_base_dir, 'master.db')):
    os.sys.exit('Run the personal_info.py script first')


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

    sessions = range(start_session, curr_session)
    for session in sessions:
        curr_db = '{}-{}.db'.format(session, session + 1)
        result_stmt = 'CREATE TABLE Result{}(MATNO TEXT PRIMARY KEY, {}, LEVEL INTEGER, SESSION INTEGER, CATEGORY TEXT)'
        course_reg_stmt = 'CREATE TABLE CourseReg{}(MATNO TEXT PRIMARY KEY, {}, LEVEL INTEGER, SESSION INTEGER, PROBATION INTEGER, OTHERS TEXT)'
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
            result_dtype.append({'MATNO': 'TEXT', 'LEVEL': 'INTEGER', 'SESSION': 'INTEGER', 'CARRYOVERS': 'TEXT', 'CATEGORY': 'TEXT'})
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
result_frame = result_frame[result_frame.COURSE_CODE != 'MEE122']
result_frame = result_frame[result_frame.COURSE_CODE != 'MEE123']
result_frame.COURSE_CODE.replace('CHM112', 'CHM122', inplace=True)


def total_registered_credits(level, course_reg_df):
    total_credit = 0
    if level <= 5:
        reg_courses_df = course_reg_df[course_reg_df != 0].dropna(axis=1)
        if level == 1:
            if not course_reg_df['PROBATION'].any(): course_codes = reg_courses_df.columns[1:]
            else: course_codes = reg_courses_df.columns[1: -1]
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


def get_total_credits(conn, level, mod, course_reg_df):
    if level >= 6 or mod == 3:
        return total_registered_credits(level, course_reg_df)
    if course_reg_df['PROBATION'].any():
        if level in [1, 5]:
            return total_registered_credits(level, course_reg_df)
        level -= num_probation
    total_credits = conn.execute('SELECT LEVEL{} FROM Credits WHERE MODE_OF_ENTRY = {}'.format(level * 100, mod)).fetchone()[0]
    if mod == 2 and level == 2:
        total_credits -= 2
    elif mod == 2 and level == 3:
        total_credits += 2
    return total_credits


def get_passed_credits(entry_session, level, result_df):
    total_credits_passed = 0
    if level <= 5:
        course_credit_dict = courses_dict[level - 1]
        if level == 1: course_codes = result_df.columns[1:]
        else: course_codes = result_df.columns[1: -1]
        courses_df = result_df[course_codes]
        if entry_session <= 2013 or entry_session > 2017:
            passed_courses_df = courses_df[courses_df[course_codes] > 39]
        else:
            passed_courses_df = courses_df[courses_df[course_codes] > 44]
        passed_courses_df.dropna(axis=1, inplace=True)
        for course_code in passed_courses_df.columns:
            total_credits_passed += course_credit_dict[course_code]
    
    if level > 1:
        carryovers_courses_scores = result_df['CARRYOVERS'].tolist()[0].split(',')
        for course_score in carryovers_courses_scores:
            if not course_score: break
            course_code, score = course_score.split()
            if entry_session <= 2013 or entry_session > 2017:
                if float(score) > 39:
                    course_level = int(course_code[3] if course_code[:3] != 'CED' else 4)
                    total_credits_passed += courses_dict[course_level - 1][course_code]
            else:
                if float(score) > 44:
                    course_level = int(course_code[3] if course_code[:3] != 'CED' else 4)
                    total_credits_passed += courses_dict[course_level - 1][course_code]
    
    return total_credits_passed


def failed_credits(entry_session, level, result_df):
    total_credits_failed = 0
    if level <= 5:
        course_credit_dict = courses_dict[level - 1]
        if level == 1: course_codes = result_df.columns[1:]
        else: course_codes = result_df.columns[1: -1]
        courses_df = result_df[course_codes]
        if entry_session <= 2013 or entry_session > 2017:
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
            if entry_session <= 2013 or entry_session > 2017:
                if float(score) <= 39:
                    course_level = int(course_code[3] if course_code[:3] != 'CED' else 4)
                    total_credits_failed += courses_dict[course_level - 1][course_code]
            else:
                if float(score) <= 44:
                    course_level = int(course_code[3] if course_code[:3] != 'CED' else 4)
                    total_credits_failed += courses_dict[course_level - 1][course_code]
    
    return total_credits_failed


def get_category(conn, entry_session, level, mod, result_df, course_reg_df):
    #total_credits_failed = failed_credits(entry_session, level, result_df)
    total_credits = get_total_credits(conn, level, mod, course_reg_df)
    total_credits_passed = get_passed_credits(entry_session, level, result_df)
    if total_credits == total_credits_passed: return 'A'
    if level == 1 and entry_session >= 2014:
        if total_credits_passed >= 36: return 'B'
        elif total_credits_passed >= 23 and total_credits_passed < 36: return 'C'
        else:
            bool_df = course_reg_df['PROBATION'] == 1
            if bool_df.all(): return 'E' # Handle condition for transfer
            else: return 'D'
    else:
        percent_passed = total_credits_passed / total_credits * 100
        if percent_passed >= 50: return 'B'
        elif percent_passed >= 25 and percent_passed < 50: return 'C'
        else:
            bool_df = course_reg_df['PROBATION'] == 0
            if bool_df.all(): return 'D'
            else: return 'E'


def get_grade(score, entry_session):
    if not score: return 'F'
    if score >= 70: return 'A'
    elif score >= 60: return 'B'
    elif score >= 50: return 'C'
    elif score >= 45: return 'D'
    else:
        if 2013 <= entry_session < 2018: return 'F'
        else:
            if score >= 40: return 'E'
            else: return 'F'


def create_gpa_schema():
    try:
        stmt = 'CREATE TABLE GPA(MATNO TEXT PRIMARY KEY, LEVEL100 REAL, LEVEL200 REAL, LEVEL300 REAL, LEVEL400 REAL, LEVEL500 REAL);'
        for session in range(start_session, curr_session + 1):
            db_name = '{}-{}.db'.format(session, session + 1)
            conn = sqlite3.connect(os.path.join(db_base_dir, db_name))
            conn.execute(stmt)
            conn.close()
    except sqlite3.OperationalError:
        pass


def store_gpa(conn, mat_no, level, result_frame, on_probation, mod):
    level = 5 if level > 5 else level
    grade_weight = {'A': 5, 'B': 4, 'C': 3, 'D': 2, 'E': 1, 'F': 0}
    if level == 1:
        level_results = result_frame.iloc[0, 1: len(result_frame.columns) - 1]
        carryovers = ['']
    else:
        level_results = result_frame.iloc[0, 1: len(result_frame.columns) - 2]
        carryovers = result_frame['CARRYOVERS'].values.tolist()
    total_credits = conn.execute('SELECT * FROM Credits;').fetchall()[mod - 1][level]
    level_courses = courses_dict[level - 1]
    prod_sum = 0
    
    if on_probation and level in [1, 5]:
        level_gpa = conn.execute('SELECT LEVEL{} FROM GPA WHERE MATNO = "{}"'.format(level * 100, mat_no)).fetchone()[0]
        level_gpa = level_gpa if level_gpa else 0
        for course_code, score_grade in level_results.iteritems():
            prev_result = conn.execute('SELECT {} FROM RESULT{} WHERE MATNO = "{}"'.format(course_code, level * 100, mat_no)).fetchone()
            prev_result = prev_result[0] if prev_result else '0,F'
            try:
                prev_score, prev_grade = prev_result.split(',')
                score, grade = score_grade.split(',')
                level_gpa += (grade_weight.get(grade, 0) - grade_weight.get(prev_grade, 0)) * level_courses[course_code] / total_credits
            except ValueError:
                pass
    else:
        for course_code, score_grade in level_results.iteritems():
            try:
                score, grade = score_grade.split(',')
                prod_sum += level_courses[course_code] * grade_weight.get(grade, 0)
            except ValueError:
                pass
        level_gpa = round(prod_sum / total_credits, 4)
    
    try:
        conn.execute('INSERT INTO GPA (MATNO, LEVEL{}) VALUES (?, ?);'.format(level * 100), (mat_no, level_gpa))
    except sqlite3.IntegrityError:
        conn.execute('UPDATE GPA SET LEVEL{} = ? WHERE MATNO = "{}"'.format(level * 100, mat_no), (level_gpa,))
    conn.commit()

    if carryovers[0]:
        for carryover_result in carryovers[0].split(','):
            course_code, score, grade = carryover_result.split(' ')
            course_level = int(course_code[3]) if course_code != 'CED300' else 4
            course_level_index = mod if course_level < mod else course_level
            gpa = conn.execute('SELECT LEVEL{} FROM GPA WHERE MATNO = "{}"'.format(course_level_index * 100, mat_no)).fetchone()[0]
            gpa = gpa if gpa else 0
            total_level_credits = conn.execute('SELECT * FROM Credits;').fetchall()[mod - 1][course_level_index]
            gpa += grade_weight.get(grade, 0) * courses_dict[course_level - 1][course_code] / total_level_credits
            try:
                conn.execute('INSERT INTO GPA (MATNO, LEVEL{}) VALUES (?, ?);'.format(course_level_index * 100), (mat_no, round(gpa, 4)))
            except sqlite3.IntegrityError:
                conn.execute('UPDATE GPA SET LEVEL{} = ? WHERE MATNO = "{}"'.format(course_level_index * 100, mat_no), (round(gpa, 4),))
            conn.commit()            


def store_unusual_students(mat_no, entry_session):
    fd = open(os.path.join(os.getcwd(), 'error.txt'), 'a')
    fd.write('{} ==> {}\n'.format(mat_no, entry_session))
    fd.close()

def populate_db(conn, mat_no, entry_session, mod):
    global result_dtype_glob, course_reg_dtype_glob, num_probation
    num_probation = 0
    # Loads all the student's results
    curr_frame = result_frame[result_frame.MATNO == mat_no]
    curr_frame_group = curr_frame.groupby(by='SESSION')
    groups = [curr_frame_group.get_group(x) for x in curr_frame_group.groups]
    groups = sorted(groups, key=lambda x: x.SESSION.iloc[0])
    levels = [groups[num].SESSION.iloc[0] for num in range(len(groups))]
    if not levels or levels[0] != entry_session or len(groups) > (9 - mod):
        store_unusual_students(mat_no, entry_session)
        return
#    progressive_sum = int(len(levels) / 2.0 * (2 * levels[0] + len(levels) - 1))
#    if sum(levels) != progressive_sum:
#        store_unusual_students(mat_no, entry_session)
#        return
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
        if count == 3:
            ced_error = level_result[level_result.COURSE_CODE == 'CED300']
            level_result.drop(ced_error.index, inplace=True)
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
        
        probation_stat = on_probation
        
        course_reg_df['PROBATION'] = on_probation
        num_probation += on_probation
        student_result['CATEGORY'] = get_category(conn, entry_session, count, mod, student_result, course_reg_df)
        bool_df = student_result['CATEGORY'] == 'C'
        if bool_df.all() : on_probation = 1
        else: on_probation = 0
        
        for col_name, series in student_result.items():
            if col_name in ['MATNO', 'CATEGORY']: continue
            if col_name == 'CARRYOVERS':
                if bool(series[0]):
                    items = series[0].split(',')
                    new_items_list = []
                    for item in items:
                        course, score = item.split()
                        try:
                            course, score = item.split(' ')
                            try: score = int(float(score))
                            except ValueError: score = -1
                            grade = get_grade(score, entry_session)
                        except ValueError:
                            course, score, grade = item, '-1', 'ABS'
                        new_items_list.append(' '.join([course, str(score), grade]))
                    series.replace(series[0], ','.join(new_items_list), inplace=True)
            else:
                try:
                    score = int(series[0])
                    grade = get_grade(score, entry_session)
                except ValueError:
                    series.replace(series[0], '-1,ABS', inplace=True)
                else:
                    series.replace(series[0], str(score) + ',' + grade, inplace=True)
        
        # compute gpa
        store_gpa(conn, mat_no, count, student_result, probation_stat, mod)
        
        student_result['SESSION'] = group.SESSION.iloc[0]
        course_reg_df['SESSION'] = group.SESSION.iloc[0]
        course_reg_dtype['SESSION'] = 'INTEGER'
        
        student_result['LEVEL'] = (count - num_probation) * 100
        course_reg_df['LEVEL'] = (count - num_probation) * 100
        course_reg_dtype['LEVEL'] = 'INTEGER'
        
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
    create_gpa_schema()
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
