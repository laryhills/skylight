from sms.src import utils, personal_info, course_details, result_statement

start = 2003
stop = 2019

crs_lvl=[0,0,0,0]
for i in range(1,4):
    crs_lvl[i] = course_details.get_all(inactive=True, mode_of_entry=i)
    crs_lvl[i] = {x["code"]: x["level"] for x in crs_lvl[i]}


def rule_2_3():   
    bad_mat_1 = set(); bad_mat_2 = set()
    for session in range(start, stop):
        sess = utils.load_session(session)
        mats = [x.mat_no for x in sess.PersonalInfo.query.all()]
        for mat_no in mats:
            # print(mat_no)
            catg = result_statement.get(mat_no)["categories"]
            if catg.count("C") > 1:
                bad_mat_1.add(mat_no)
            d_idx = (catg + ["D"]).index("D")
            if (catg + ["D"])[d_idx+1:]:
                bad_mat_2.add(mat_no)
    print ("Rule 2 defaulters\n",bad_mat_1)
    print ("Rule 3 defaulters\n",bad_mat_2)


def rule_1_4():
    bad_mat_1 = set(); bad_mat_2 = set()
    for session in range(start, stop):
        sess = utils.load_session(session)
        mats = [x.mat_no for x in sess.PersonalInfo.query.all()]
        for mat_no in mats:
            person = personal_info.get(mat_no)
            mode_of_entry = person["mode_of_entry"]
            results = result_statement.get(mat_no)["results"]
            for result in results:
                for record in result["first_sem"]+result["second_sem"]:
                    rec_crs_lvl = crs_lvl[mode_of_entry][record[0]]
                    if rec_crs_lvl // 100 < mode_of_entry:
                        bad_mat_1.add(mat_no)
                    if rec_crs_lvl > result["level"]:
                        bad_mat_2.add(mat_no)

    print ("Rule 1 defaulters\n", bad_mat_1)
    print ("Rule 4 defaulters\n", bad_mat_2)


rule_1_4()
rule_2_3()
