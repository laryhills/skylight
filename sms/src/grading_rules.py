from sms.src.users import access_decorator, load_session
from sms.src.utils import spc_fn, csv_fn


def get(acad_session):
    rule_str = load_session(acad_session).GradingRule.query.all()[0].rule
    rule = [spc_fn(x) for x in csv_fn(rule_str)]
    grad_rule = list(map(lambda x: [x[0], int(x[1]), int(x[2])], rule))
    return grad_rule, 200


@access_decorator
def post(acad_session, rule):
    pass
