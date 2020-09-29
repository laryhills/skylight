from sms.src import personal_info, course_details, utils
from json import dumps


def get(mat_no, retJSON=False):
    person = personal_info.get(mat_no=mat_no)
    
    student_details = {"name": "{}, {}".format(person['surname'], person['othernames']), "dept": utils.get_dept(),
                       "dob": person['date_of_birth'], "mode_of_entry": person['mode_of_entry'], "results": [], "credits": [],
                       "category": [], "entry_session": person['session_admitted'], "grad_session": person['session_grad']}
    
    results = utils.result_poll(mat_no)
    finalResults = []
    tcps = []   # This may be useful
    
    for lvl in range(8):
        result = results[lvl]
        if result:
            result.pop('mat_no')
            session = result.pop('session')
            level = result.pop('level')
            category = result.pop('category')
            result.pop('unusual_results')
            tcps.append(result.pop('tcp'))
            # if lvl:
            carryovers = result.pop('carryovers')
            if carryovers:
                carryovers = carryovers.split(',')
                for co in carryovers:
                    # coSplit = co.split()
                    # # Special cases, del on fix DB
                    # if len(coSplit)==4:
                    #     coSplit.remove('nan')
                    #     co = " ".join(coSplit)
                    # if len(coSplit) == 2:
                    #     co = " ".join(coSplit+["F"])
                    (course, score, grade) = co.split()
                    result[course] = ",".join([score, grade])
            credits_passed = credits_failed = credits_total = 0
            lvlResult = {"first_sem": [], "second_sem": [], 'level': level, 'session': session, "table": (lvl+1)*100}
            for course in result:
                if result[course]:
                    if course == "CHM112":
                        # Manually deal with this typo Special cases, del on fix DB
                        course, sem, credit, title, course_level = "CHM122", 2, 3, "General Chemistry II", 100
                        (score, grade) = [x.strip() for x in result["CHM112"].split(',')]
                    else:
                        course_props = course_details.get(course)
                        sem = course_props['semester']
                        credit = course_props['credit']
                        title = course_props['title']
                        if person['mode_of_entry'] != 1 and course[:3] == "GST":
                            course_level = person["mode_of_entry"] * 100
                        else:
                            course_level = course_props["level"]
                        (score, grade) = [x.strip() for x in result[course].split(',')]

                    if grade == 'F' or grade == 'ABS':
                        credits_failed += credit
                    else:
                        credits_passed += credit
                    credits_total += credit
                    lvlResult[["first_sem", "second_sem"][sem-1]].append(((lvl+1)*100,course,title,credit,int(score),grade,course_level))

            finalResults.append(lvlResult)
            student_details["credits"].append((credits_total,credits_passed,credits_failed))
            student_details["category"].append(category)
    student_details["results"] = finalResults
    if retJSON:
        return dumps(student_details)
    return student_details
