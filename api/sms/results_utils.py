# imports go here


def get_result_at_acad_session(acad_session, res_poll):
    # get last result
    for index, result in enumerate(res_poll):
        if result and result['session'] == acad_session:
            table = 'Result' + str((index + 1) * 100)
            return result, table
    return {}, ''


def get_table_to_populate(session_course_reg, full_res_poll):
    result_level = session_course_reg['course_reg_level']
    # selecting Result table for a fresh input (first result entered for the student for the session)
    if session_course_reg['courses'] and not full_res_poll[session_course_reg['table'][-3:] // 100 - 1]:
        # use table corresponding to course reg table if it is available 
        table_to_populate = 'Result' + session_course_reg['table'][-3:]
    elif not full_res_poll[result_level // 100 - 1]:
        table_to_populate = 'Result' + str(result_level)
    else:
        table_to_populate = 'Result' + str(100 * ([ind for ind, result in enumerate(res_poll) if not result][0] + 1))
    return table_to_populate

