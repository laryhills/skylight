import os
import sqlite3
import pandas

db_base_dir = os.path.join(os.path.dirname(__file__), '..', 'api', 'sms', 'database')

categories = [
    {
        'category': 'A',
        'description': 'Successful Students',
        'text': 'The following {{ no_sw }} ({{ no_s }}) students have satisfied the Examiners in all the courses '
                'which they registered for in the {{ session }} Session and have earned all the assigned credits.',
        'headers': 'S/N, Mat. No., Full Name (Surname Last in Block Letters), Total Credits earned in the '
                   '{{ session }} session',
        'sizes': '3, 22, 48, 24'
    },
    {
        'category': 'B',
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
        'description': 'Medical Case',
        'text': '',
        'headers': 'S/N, Mat. No., Full Name, Remarks if any',
        'sizes': '3, 22, 48, 24'
    },
    {
        'category': 'G',
        'description': 'Absence from Examination',
        'text': '',
        'headers': 'S/N, Mat. No., Full Name, Remarks if any',
        'sizes': '3, 22, 48, 24'
    },
    {
        'category': 'H',
        'description': 'Withheld Results',
        'text': '',
        'headers': 'S/N, Mat. No., Full Name, Remarks if any',
        'sizes': '3, 22, 48, 24'
    },
    {
        'category': 'I',
        'description': 'Expelled/Rusticated/Suspended Students',
        'text': '',
        'headers': 'S/N, Mat. No., Full Name, Remarks if any',
        'sizes': '3, 22, 48, 24'
    },
    {
        'category': 'J',
        'description': 'Temporary Withdrawal from the University',
        'text': '',
        'headers': 'S/N, Mat. No., Full Name, Remarks if any',
        'sizes': '3, 22, 48, 24'
    },
    {
        'category': 'K',
        'description': 'Unregistered Student',
        'text': '',
        'headers': 'S/N, Mat. No., Full Name, Remarks if any',
        'sizes': '3, 22, 48, 24'
    },
]


def create_categories_table():
    stmt = 'CREATE TABLE Category(category PRIMARY_KEY TEXT, description TEXT, text TEXT, headers TEXT, sizes TEXT);'
    conn = sqlite3.connect(os.path.join(db_base_dir, 'master.db'))
    try:
        conn.execute(stmt)
    except sqlite3.OperationalError:
        pass
    df = pandas.DataFrame(categories)
    df.to_sql('Category', conn, index=False, if_exists='append')
    conn.commit()
    conn.close()


if __name__ == '__main__':
    create_categories_table()

    print('Done')
