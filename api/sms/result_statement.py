from sms import utils
from sms import personal_info
from sms import course_details
from json import loads, dumps
from sms.users import access_decorator


@access_decorator
def get(mat_no, retJSON=True, req_perms=["read"]):
    person = loads(personal_info.get(mat_no=mat_no))
    
    student_details = {"name": "{}, {}".format(person['surname'], person['othernames']), "depat": utils.get_depat(),
                       "dob": person['date_of_birth'], "mode_of_entry": person['mode_of_entry'], "results": [], "credits": [],
                       "category": [], "entry_session": person['session_admitted'], "grad_session": person['session_grad']}
    
    results = utils.result_poll(mat_no)
    finalResults = []
    
    for lvl in range(8):
        result = results[lvl]
        if result:
            result.pop('mat_no')
            session = result.pop('session')
            level = result.pop('level')
            category = result.pop('category')
            if lvl:
                carryovers = result.pop('carryovers')
                if carryovers != '':
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
            lvlResult = {"first_sem": [], "second_sem": [], 'level': level, 'session': session}
            for course in result:
                if result[course]:
                    if course == "CHM112":
                        # Manually deal with this typo Special cases, del on fix DB
                        course, sem, credit, title = "CHM122", 2, 3, "General Chemistry II"
                        (score, grade) = [x.strip() for x in result["CHM112"].split(',')]
                    else:
                        course_props = loads(course_details.get(course))
                        sem = course_props['course_semester']
                        credit = course_props['course_credit']
                        title = course_props['course_title']
                        (score, grade) = [x.strip() for x in result[course].split(',')]

                    if grade == 'F' or grade == 'ABS':
                        credits_failed += credit
                    else:
                        credits_passed += credit
                    credits_total += credit
                    lvlResult[["first_sem", "second_sem"][sem-1]].append(((lvl+1)*100,course,title,credit,int(score),grade))

            finalResults.append(lvlResult)
            student_details["credits"].append((credits_total,credits_passed,credits_failed))
            student_details["category"].append(category)
    student_details["results"] = finalResults
    if retJSON:
        return dumps(student_details)
    return student_details


def get_gpa(mat_no):
    person = loads(personal_info.get(mat_no=mat_no))
    mode_of_entry = person['mode_of_entry']
    gpas = [[0,0,0,0,0],[0,0,0,0],[0,0,0]][mode_of_entry-1]
    level_percent = [[10,15,20,25,30],[10,20,30,40],[25,35,40]][mode_of_entry-1]
    level_credits = utils.get_credits(mat_no, mode_of_entry)
    grade_weight = {"A":5, "B":4, "C":3, "D":2, "E":1, "F":0}
    
    for result in loads(get(mat_no))["results"]:
        for record in (result["first_sem"]+result["second_sem"]):
            (course, grade) = (record[1], record[5])
            course_props = loads(course_details.get(course))
            lvl = int(course_props["course_level"]/100)-1
            credit = course_props["course_credit"]
            product = grade_weight[grade]*credit
            gpas[lvl]+=(product/level_credits[lvl])

    return dumps(gpas)
