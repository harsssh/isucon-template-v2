# PYTHONPATH に ansible/filter_plugins を含めて実行する (make test)
import unittest

from app_service import services_in_directory

# systemctl show は -p の順序によらず、プロパティを決まった順序で出力する
SHOW_OUTPUT = """\
WorkingDirectory=/home/isucon/webapp/go
Id=isupipe-go.service

WorkingDirectory=/home/isucon/webapp/python
Id=isupipe-python.service

WorkingDirectory=/
Id=isupipe-dns.service
"""


class TestServicesInDirectory(unittest.TestCase):
    def test_returns_service_running_in_directory(self):
        self.assertEqual(services_in_directory(SHOW_OUTPUT, '/home/isucon/webapp/go'), ['isupipe-go'])

    def test_ignores_trailing_slash(self):
        output = 'Id=isucondition.go.service\nWorkingDirectory=/home/isucon/webapp/go/\n'

        self.assertEqual(services_in_directory(output, '/home/isucon/webapp/go'), ['isucondition.go'])

    def test_returns_empty_when_no_service_matches(self):
        self.assertEqual(services_in_directory(SHOW_OUTPUT, '/home/isucon/webapp/rust'), [])

    def test_returns_empty_for_empty_output(self):
        self.assertEqual(services_in_directory('', '/home/isucon/webapp/go'), [])


if __name__ == '__main__':
    unittest.main()
