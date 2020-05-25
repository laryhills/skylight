# Skylight
This project represents the server side of the **Student Management System** for the Department of Mechanical 
Engineering, University of Benin.

## Instructions
- `server.py` is the main entry point into the app
- Before executing `server.py` first run `scripts/generate_models.py` 
  which generates all the database models
- Also run the following scripts in the order specified to generate the database
    - `scripts/personal_info.py`
    - `scripts/course_details.py`
    - `scripts/generate_courses_&_credits`
    - `scripts/generate_course_reg_&_result.py`
    - `scripts/generate_grading_rule`

###### Note:
1. Current data in the `accounts.db`
    - username = ucheigbeka
    - password = testing

2. [**Wkhtmltopdf**](https://wkhtmltopdf.org/downloads.html) is needed for generating the pdfs