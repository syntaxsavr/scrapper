from django.test import TestCase
from .testExample import add_numbers
from .testExample import sub_numbers

# Create your tests here.
# You might have to give your db-User permissions to create tables (ALTER USER <yourUser> CREATEDB;)

# run tests via: coverage run manage.py test --keepdb

# --- running with mutation first init: cosmic-ray init cosmic-ray.toml cosmic-ray.sqlite
# Apply filters - so it does not take so long: cr-filter-pragma cosmic-ray.sqlite
# first run: cosmic-ray --verbosity=INFO baseline cosmic-ray.toml
# The following enumerates all the possible mutations: cr-report cosmic-ray.sqlite --show-pending
# The following runs mutatnts: cosmic-ray exec cosmic-ray.toml cosmic-ray.sqlite
# Generate report: cr-html cosmic-ray.sqlite > report.html

class ExampleTest(TestCase):

    def test_add_numbers(self):
        self.assertEqual(add_numbers(1, 1), 2)
        self.assertEqual(add_numbers(0, 0), 0)
        self.assertEqual(add_numbers(-1, -1), -2)

    def test_sub_numbers(self):
        self.assertEqual(sub_numbers(1, 1), 0)
        self.assertEqual(sub_numbers(-1, -1), 0)