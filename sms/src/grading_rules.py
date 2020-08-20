from sms.src.users import access_decorator, load_session


def get(acad_session):
    session = load_session(acad_session)
    rule_str = eval('session.GradingRule.query.all()[0].rule')
    rule = rule_str.split(',')
    grad_rule = []
    for r in rule:
        grade, weight, limit = r.split(' ')
        grad_rule.append([grade, int(weight), int(limit)])

    return grad_rule, 200


@access_decorator
def post(acad_session, rule):
    pass
