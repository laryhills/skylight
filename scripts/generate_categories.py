import os
import sqlite3
import pandas

db_base_dir = os.path.join(os.path.dirname(__file__), '..', 'api', 'sms', 'database')

categories = [
    {
        'category': 'A',
        'group': 'successful students',
        'description': 'Successful Students',
        'text': 'The following {{ no_sw }} ({{ no_s }}) students have satisfied the Examiners in all the courses '
                'which they registered for in the {{ session }} Session and have earned all the assigned credits.',
        'headers': 'S/N, Mat. No., Full Name (Surname Last in Block Letters), Total Credits earned in the '
                   '{{ session }} session',
        'sizes': '3, 22, 48, 24'
    },
    {
        'category': 'B',
        'group': 'carryover students',
        'description': 'Students with Carryover Courses',
        'text': 'The following {{ no_sw }} ({{ no_s }}) students have obtained the {{ mc }} minimum credits '
                'requirement to remain in the Faculty but failed some courses which they are allowed to carry over '
                'to the next session.',
        'headers': 'S/N, Mat. No., Full Name (Surname Last in Block Letters), Total Credits earned in the '
                   '{{ session }} session, Total Credits Failed in the {{ session }} Session, Outstanding Courses '
                   'Failed in the {{ session }} Session',
        'sizes': '3, 13, 30, 13, 13, 25'
    },
    {
        'category': 'C',
        'group': 'probating students',
        'description': 'Students for Probation/Transfer',
        'text': 'The results of the following {{ no_sw }} ({{ no_s }}) students did not earn the {{ mc }} minimum '
                'number of credits needed to qualify them to move to the next higher level but they earned not less '
                'than 50% of the minimum number of credits and are to remain in the Faculty on probation/transfer.',
        'headers': 'S/N, Mat. No., Full Name (Surname Last in Block Letters), Total Credits earned in the '
                   '{{ session }} session, Total Credits Failed in the {{ session }} Session, Outstanding Courses '
                   'Failed in the {{ session }} Session',
        'sizes': '3, 13, 30, 13, 13, 25'
    },
    {
        'category': 'D',
        'group': 'unsuccessful students 1',
        'description': 'Students who are to Withdraw from the Faculty and the University',
        'text': 'The following {{ no_sw }} ({{ no_s }}) students did not earn the {{ mc }} minimum number of '
                'credits needed to qualify them to move to the next higher level and also earned less than 50% of '
                'the minimum number of credits and are to withdraw from the Faculty and the University.',
        'headers': 'S/N, Mat. No., Full Name (Surname Last in Block Letters), Total Credits earned in the '
                   '{{ session }} session, Total Credits Failed in the {{ session }} Session, Outstanding Courses '
                   'Failed in the {{ session }} Session',
        'sizes': '3, 13, 30, 13, 13, 25'
    },
    {
        'category': 'E',
        'group': 'unsuccessful students 2',
        'description': 'Students who were Previously on Probation/Transfer',
        'text': 'The following {{ no_sw }} ({{ no_s }}) student who had previously had a probation or transferred '
                'from other Faculties failed to obtain the 36 minimum credit requirements to remain in the Faculty '
                'and he is therefore, required to withdraw from the Faculty and the University.',
        'headers': 'S/N, Mat. No., Full Name, Total Credits earned in the {{ session }} session, Total Credits '
                   'Failed in the {{ session }} Session, Outstanding Courses Failed in the {{ session }} Session',
        'sizes': '3, 13, 30, 13, 13, 25'
    },
    {
        'category': 'F',
        'group': 'medical cases',
        'description': 'Medical Case',
        'text': '',
        'headers': 'S/N, Mat. No., Full Name (Surname Last in Block Letters), Remarks if any',
        'sizes': '3, 22, 48, 24'
    },
    {
        'category': 'G',
        'group': 'absent from examination',
        'description': 'Absence from Examination',
        'text': '',
        'headers': 'S/N, Mat. No., Full Name (Surname Last in Block Letters), Remarks if any',
        'sizes': '3, 22, 48, 24'
    },
    {
        'category': 'H',
        'group': 'withheld results',
        'description': 'Withheld Results',
        'text': '',
        'headers': 'S/N, Mat. No., Full Name (Surname Last in Block Letters), Remarks if any',
        'sizes': '3, 22, 48, 24'
    },
    {
        'category': 'I',
        'group': 'expelled/suspended students',
        'description': 'Expelled/Rusticated/Suspended Students',
        'text': '',
        'headers': 'S/N, Mat. No., Full Name (Surname Last in Block Letters), Remarks if any',
        'sizes': '3, 22, 48, 24'
    },
    {
        'category': 'J',
        'group': 'temporary withdrawal',
        'description': 'Temporary Withdrawal from the University',
        'text': 'The following {{ no_sw }} ({{ no_s }}) students were recommended by the Faculty Board of Studies for '
                'temporary withdrawal from the University to resume studies at the beginning of next session.',
        'headers': 'S/N, Mat. No., Full Name (Surname Last in Block Letters), Reasons for Temporary Withdrawal',
        'sizes': '3, 22, 48, 24'
    },
    {
        'category': 'K',
        'group': 'unregistered students',
        'description': 'Unregistered Students',
        'text': 'The following {{ no_sw }} ({{ no_s }}) students failed to register for the session because they have'
                'not provided evidence of payment of school charges for the {{ session }} academic session',
        'headers': 'S/N, Mat. No., Full Name (Surname Last in Block Letters), Remarks if any',
        'sizes': '3, 22, 48, 24'
    },
]

categories_500 = [
    {
        'category': 'A',
        'group': 'successful students',
        'description': 'Successful Students',
        'text': 'The following {{ no_sw }} ({{ no_s }}) students who sat for the 500 level (Final) Degree '
                       'examination of the Bachelor of Engineering have satisfied the degree requirements of the '
                       'Faculty of Engineering including the General Studies Examination (and Industrial Training) and '
                       'are therefore, qualified for the award of Bachelor degree in the class of honours and in '
                       'the subject area indicated below:',
        'headers': 'S/N, Mat. No., Full Name (Surname Last in Block Letters), Subject Area',
        'sizes': '3, 22, 48, 24'
     },
    {
        'category': 'B',
        'group': 'carryover students',
        'description': 'Referred Students',
        'text': 'The following {{ no_sw }} ({{ no_s }}) students did not satisfy the Examiners in the course shown '
                'against their names and are to carry over failed courses to the next session.',
        'headers': 'S/N, Mat. No., Full Name (Surname Last in Block Letters), Registered courses owed in the '
                   '{{ session }} Session, Cumulative credits to date, Outstanding credits required to graduate, '
                   'Other courses owed over the years but not registered for',
        'sizes': '3, 12, 22, 20, 10, 10, 20'
    },
    {
        'category': 'C',
        'group': 'withheld results',
        'description': 'Withheld Results',
        'text': '',
        'headers': 'S/N, Mat. No., Full Name (Surname Last in Block Letters), Remarks if any',
        'sizes': '3, 22, 48, 24'
    },
    {
        'category': 'D',
        'group': 'expelled/suspended students',
        'description': 'Expelled/Rusticated/Suspended Students',
        'text': '',
        'headers': 'S/N, Mat. No., Full Name (Surname Last in Block Letters), Reasons for Rustication/Suspension',
        'sizes': '3, 22, 48, 24'
    },
    {
        'category': 'E',
        'group': 'temporary withdrawal',
        'description': 'Temporary Withdrawal from The University',
        'text': 'The following {{ no_sw }} ({{ no_s }}) students were recommended by the Faculty Board of Studies for '
                'temporary withdrawal from the University to resume studies at the beginning of next session.',
        'headers': 'S/N, Mat. No., Full Name (Surname Last in Block Letters), Reasons for Temporary Withdrawal',
        'sizes': '3, 22, 48, 24'
    },
    {
        'category': 'F',
        'group': 'medical cases',
        'description': 'Medical Cases',
        'text': '',
        'headers': 'S/N, Mat. No., Full Name (Surname Last in Block Letters), Remarks if any',
        'sizes': '3, 22, 48, 24'
    },
    {
        'category': 'G',
        'group': 'exhausted maximum allowable period',
        'description': 'Students Who Have Exhausted the Maximum Period Allowed',
        'text': '',
        'headers': 'S/N, Mat. No., Full Name (Surname Last in Block Letters), Remarks if any',
        'sizes': '3, 22, 48, 24'
    },
{
        'category': 'H',
        'group': 'unregistered students',
        'description': 'Unregistered Students',
        'text': 'The following {{ no_sw }} ({{ no_s }}) students failed to register for the session because they have'
                'not provided evidence of payment of school charges for the {{ session }} academic session',
        'headers': 'S/N, Mat. No., Full Name (Surname Last in Block Letters), Remarks if any',
        'sizes': '3, 22, 48, 24'
    },
    {
        'category': 'I',
        'group': 'prize winners',
        'description': 'Prize Winners',
        'text': 'List the prize winners with their CGPA approximated to one decimal point only.',
        'headers': 'S/N, Mat. No., Full Name (Surname Last in Block Letters), CGPA',
        'sizes': '3, 22, 48, 24'
    },
]


def create_categories_table():
    stmt = 'CREATE TABLE Category(category PRIMARY_KEY TEXT, group TEXT, ' \
           'description TEXT, text TEXT, headers TEXT, sizes TEXT);'
    stmt_1 = 'CREATE TABLE Category500(category PRIMARY_KEY TEXT, group TEXT, ' \
             'description TEXT, text TEXT, headers TEXT, sizes TEXT);'
    conn = sqlite3.connect(os.path.join(db_base_dir, 'master.db'))
    try:
        conn.execute(stmt)
    except sqlite3.OperationalError:
        pass
    try:
        conn.execute(stmt_1)
    except sqlite3.OperationalError:
        pass
    df = pandas.DataFrame(categories)
    df.to_sql('Category', conn, index=False, if_exists='replace')
    df = pandas.DataFrame(categories_500)
    df.to_sql('Category500', conn, index=False, if_exists='replace')
    conn.commit()
    conn.close()


if __name__ == '__main__':
    create_categories_table()

    print('Done')
