# Note: Comment out the line for starting the redis worker in sms/src/users.py before profiling
# def login(token):
#     ....
#     start_redis_worker(stored_user)
#     ....

import os
from pstats import Stats

base_dir = os.path.dirname(__file__)
reports_dir = os.path.join(base_dir, 'reports')
summary_dir = os.path.join(reports_dir, 'summary')
print_regex_pattern = f'fme_skylight[{os.path.sep}]+sms[{os.path.sep}]+src'

report_start, cum_time_col = 8, 3
summary = {}


def parse_stats(stats: Stats, sort_criteria='cumulative'):
    stats.sort_stats(sort_criteria).print_stats(print_regex_pattern)


def generate_report(filepath: str, report_name: str, section_name: str, func_dict: dict):
    with open(filepath) as fd:
        _lines = fd.readlines()[report_start:]

    lines = []
    for _line in _lines:
        line = _line.strip().split(' ')
        line = list(filter(lambda x: bool(x), line))
        lines.append(line)

    total_time = float(lines[0][cum_time_col])

    def get_line(func_name):
        for line in lines:
            if func_name in line[-1]:
                return line

    report = []
    prev_time_dict = {}
    for name in func_dict:
        func, func_level = func_dict[name]
        if func:
            cum_time = float(get_line(func)[cum_time_col])
        else:
            cum_time = total_time
        prev_time = prev_time_dict.get(func_level, 0)
        percent = (cum_time - prev_time) / total_time * 100
        report.append('\t=\t'.join([name, '{:.2f}%'.format(percent) + os.linesep]))
        if summary.get(report_name):
            if summary[report_name].get(name):
                summary[report_name][name].append(percent)
            else:
                summary[report_name][name] = [percent]
        else:
            summary[report_name] = {name: [percent]}
        prev_time_dict[func_level] = cum_time

    report_path = os.path.join(summary_dir, report_name + '.txt')
    canonical_name = section_name.replace('_', ' ')
    canonical_name = canonical_name.title()
    with open(report_path, 'a') as fd:
        fd.write(canonical_name.center(60, ' ') + os.linesep)
        fd.write(f'\tTotal time: {total_time}' + os.linesep * 2)
        fd.writelines(report)
        fd.write('=' * 60 + os.linesep * 2)


def summarize_report():
    for report_name in summary:
        report_summary = []
        for name in summary[report_name]:
            percent_list = summary[report_name][name]
            mean_percent = sum(percent_list) / len(percent_list)
            report_summary.append('\t=\t'.join([name, '{:.2f}%'.format(mean_percent) + os.linesep]))

        report_path = os.path.join(summary_dir, report_name + '.txt')
        with open(report_path, 'a') as fd:
            fd.write('SUMMARY'.center(60, ' ') + os.linesep)
            fd.writelines(report_summary)
