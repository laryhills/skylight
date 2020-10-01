"""
    The senate version generation process can be grouped into 5 different categories
        - Initialization - between get and the calling to the respective level's get_ function
        - Data retrieval - between functions calls by the models up to the get_students_by_category function
        - Data parsing - between get_students_by_category and get_students_details_by_category (100 to 400) or (500)
        - Template pre-processing: between get_100_to_400 (100L sv) or get_500 (500L sv) and the call to merge the data
                                    and template
        - Sheet Generation: the time taken within generate_header and generate_pdf
"""

import os
import cProfile
from pstats import Stats
from colorama import init, Fore

from sms.src.senate_version import get
from profiles import reports_dir, parse_stats, generate_report, summarize_report

init(autoreset=True)


_100_to_400_test_funcs = {
    '100_senate_version_profile': 'get(2015, 100)',
    '200_senate_version_profile': 'get(2016, 200)',
    '300_senate_version_profile': 'get(2017, 300)',
    '400_senate_version_profile': 'get(2018, 400)',
}

_500_test_funcs = {
    '2018_500_senate_version_profile': 'get(2018, 500)',
    '2017_500_senate_version_profile': 'get(2017, 500)',
}

_100_to_400_func_dict = {
    'Data Retrieval': ['get_students_by_category', 0],
    'Data Parsing': ['get_students_details_by_category', 0],
    'Section loading': ['load_cat_section', 1],
    'Header generation': ['generate_header', 2],
    'Template Pre-processing': ['get_100_to_400', 0],
    'Sheet generation': ['generate_pdf', 3],
    'Initializing': ['', 0]
}

_500_func_dict = {
    'Data Retrieval': ['get_students_by_category', 0],
    'Data Parsing': ['get_final_year_students_by_category', 0],
    'Section loading': ['load_cat_section_500', 1],
    'Header generation': ['generate_header', 2],
    'Template Pre-processing': ['get_500', 0],
    'Sheet generation': ['generate_pdf', 3],
    'Initializing': ['', 0]
}


def profile(test_funcs, report_name, func_dict):
    count, num_of_tests = 0, len(test_funcs.keys())
    for filename, stmt in test_funcs.items():
        count += 1
        print(Fore.YELLOW + f'Profiling test case {count} of {num_of_tests}: {stmt}')

        cProfile.run(stmt, 'stats')
        filepath = os.path.join(reports_dir, filename + '.txt')
        with open(filepath, 'w') as fd:
            stats = Stats('stats', stream=fd)
            parse_stats(stats)

        generate_report(filepath, report_name, filename, func_dict)
    summarize_report()

    os.remove('stats')


print(Fore.GREEN + 'Profiling senate_version.py...')
profile(_100_to_400_test_funcs, '100_to_400_senate_version_profile_report', _100_to_400_func_dict)
profile(_500_test_funcs, '500_senate_version_profile_report', _500_func_dict)
print(Fore.GREEN + 'Done')
