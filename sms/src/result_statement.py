from re import match
from sms.src import personal_info, course_details, utils

itol = lambda x: (x+1) * 100
csv_fn = lambda csv, fn=lambda x:x: list(map(fn, csv.split(","))) if csv else []
spc_fn = lambda spc, fn=lambda x:x: list(map(fn, spc.split(" "))) if spc else []


def format_results(results, tcp=(0,0), tcf = (0,0)):
    # TODO when making undumb, use TCP, TCF 1&2 from DB
    formatted_results, tcp, tcf = [[], []], [*tcp], [*tcf]
    for code, score, grade in results:
        course = course_details.get(code)
        sem, credit, title = course["semester"], course["credit"], course["title"]
        formatted_results[sem-1].append((code, title, credit, int(score), grade))
        if grade not in ("ABS", "F"):
            tcp[sem-1] += credit
        else:
            tcf[sem-1] += credit
    tcw = [tcp[0]+tcf[0], tcp[1]+tcf[1]]
    return [formatted_results] + [tcw] + [tcp] + [tcf]


def get(mat_no, sep_carryovers=False):
    person = personal_info.get(mat_no)
    results = utils.result_poll(mat_no)
    student_details = {"dept": utils.get_dept(), "results": [], "credits": [], "categories": [], "unregd": [], "carryovers": []}
    keys = ["date_of_birth", "mode_of_entry", "session_admitted", "surname",
            "grad_status",  "session_grad", "is_symlink", "othernames", "sex"]
    student_details.update({key: person[key] for key in keys})
    for idx, result in enumerate(results):
        if result:
            result_arr = []
            co_result = {"first_sem": [], "second_sem": [], 'level': result["level"], 'session': result["session"], "table": itol(idx)}
            lvl_result = {"first_sem": [], "second_sem": [], 'level': result["level"], 'session': result["session"], "table": itol(idx)}
            for code in [key for key in result if match("[A-Z][A-Z][A-Z][0-9][0-9][0-9]", key) and result[key]]:
                result_arr.append((code, *csv_fn(result[code])))
            co_arr = [spc_fn(x) for x in csv_fn(result["carryovers"])]
            if sep_carryovers:
                co_formatted = format_results(co_arr)
                co_result["first_sem"] += co_formatted[0][0]
                co_result["second_sem"] += co_formatted[0][1]
                student_details["carryovers"].append(co_result)
                formatted = format_results(result_arr, *co_formatted[2:])
            else:
                formatted = format_results(result_arr + co_arr)
            lvl_result["first_sem"] += formatted[0][0]
            lvl_result["second_sem"] += formatted[0][1]
            student_details["results"].append(lvl_result)
            student_details["credits"].append((formatted[1], formatted[2], formatted[3]))
            student_details["categories"].append(result["category"])
    return student_details
