from sms import result_poll
from sms import personal_info
from sms import course_details
from json import loads,dumps


def get(mat_no):
    person = loads(personal_info.get(mat_no=mat_no))
    
    student_details = {"name":"{}, {}".format(person['surname'],person['othernames']), "depat":"MECHANICAL ENGINEERING",
                       "dob":person['date_of_birth'], "mode_of_entry":person['mode_of_entry'], "results":[], "credits":[],
                       "entry_session":person['session_admitted'], "grad_session":person['session_grad']}
    
    results = loads(result_poll.get(mat_no))
    finalResults = []
    
    for lvl in range(8):
        result = results[lvl]
        if result:
            result.pop('mat_no')
            category = result.pop('category')
            if lvl:
                carryovers = result.pop('carryovers')
                if (carryovers != "nan, F"):
                    carryovers = carryovers.split(',')
                    for co in carryovers:
                        (course, score, grade) = co.split()
                        result[course] = ",".join([score,grade])
            credits_passed = credits_failed = credits_total = 0
            lvlResult={"first_sem":[],"second_sem":[]}
            for course in result:
                if result[course]:
                    course_props = loads(course_details.get(course))
                    sem = course_props['course_semester']
                    credit = course_props['course_credit']
                    title = course_props['course_title']
                    (score, grade) = [x.strip() for x in result[course].split(',')]

                    if grade=='F':
                        credits_failed += credit
                    else:
                        credits_passed +=credit
                    credits_total += credit

                    lvlResult[["first_sem","second_sem"][sem-1]].append(((lvl+1)*100,course,title,credit,int(score),grade))

            finalResults.append(lvlResult)
            student_details["credits"].append((credits_total,credits_passed,credits_failed))
    student_details["results"] = finalResults
    return dumps(student_details)


def get_carryovers(mat_no):
    first_sem, second_sem, carryovers = {}, {}, {}
    for result in loads(get(mat_no))["results"]:
        for record in result["first_sem"]:
            (course, grade) = (record[1], record[5])
            first_sem[course] = grade
        for record in result["second_sem"]:
            (course, grade) = (record[1], record[5])
            second_sem[course] = grade
    carryovers["first_sem"] = [course for course in first_sem if first_sem[course]=="F"]
    carryovers["second_sem"] = [course for course in second_sem if second_sem[course]=="F"]
    return dumps(carryovers)


def get_gpa(mat_no):
    person = loads(personal_info.get(mat_no=mat_no))
    mode_of_entry = person['mode_of_entry']
    gpas = [[0,0,0,0,0],[0,0,0,0]][mode_of_entry-1]
    level_percent = [[10,15,20,25,30],[10,20,30,40]][mode_of_entry-1]
    level_credits = [[46,42,46,24,38],[52,46,24,38]][mode_of_entry-1]
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
