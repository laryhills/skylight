# skylight
###### Note:
1. Current data in the `accounts.db`
    - username = ucheigbeka
    - password = testing

2. Ensure that **WeasyPrint** is propery configured. Check out the
[docs](https://weasyprint.readthedocs.io/en/latest/install.html) for more info

## Instructions
- `server.py` is the main entry point into the app
- Before executing `server.py` first run `scripts/generate_models.py` 
  which generates all the database models
- Run `scripts/personal_info.py`, `scripts/course_details.py`, `scripts/generate_courses_&_credits` and 
  `scripts/generate_course_reg_&_result.py` and `scripts/generate_grading_rule` to generate the databases