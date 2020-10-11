from sms.src import utils, personal_info, course_details, result_statement

start = 2016
stop = 2019

crs_lvl=[0,0,0,0]
for i in range(1,4):
    crs_lvl[i] = course_details.get_all(inactive=True, mode_of_entry=i)
    crs_lvl[i] = {x["code"]: x["level"] for x in crs_lvl[i]}

def rule_1():
    bad_mat = set()
    for session in range(start, stop):
        sess = utils.load_session(session)
        mats = [x.mat_no for x in sess.PersonalInfo.query.all()]
        for mat_no in mats:
            # print(mat_no)
            person = personal_info.get(mat_no)
            mode_of_entry = person["mode_of_entry"]
            results = result_statement.get(mat_no)["results"]
            for result in results:
                lp_2 = False
                for record in result["first_sem"]+result["second_sem"]:
                    lp_1 = False
                    if crs_lvl[mode_of_entry][record[0]] // 100 < mode_of_entry:
                        print (mat_no, mode_of_entry, record[0])
                        bad_mat.add(mat_no)
                        lp_1=True
                        break
                else:
                    if lp_1:
                        lp_2 = True
                        break
            else:
                if lp_2:
                    break
    print ("Rule 1 defaulters")
    print (bad_mat)

rule_1()
