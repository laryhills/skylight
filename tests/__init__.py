import os.path
import pytest

base_dir = os.path.dirname(__file__)
db_path = os.path.join(os.path.split(base_dir)[0], "sms", "database")


if __name__ == '__main__':
    pytest.main()
