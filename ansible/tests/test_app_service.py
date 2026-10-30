# PYTHONPATH に ansible/filter_plugins を含めて実行する (make test)
import unittest

from app_service import exec_start_path, listening_port, services_in_directory

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


class TestExecStartPath(unittest.TestCase):
    def test_returns_path_of_executable(self):
        value = '{ path=/home/isucon/webapp/go/isuride ; argv[]=/home/isucon/webapp/go/isuride ; ignore_errors=no }'

        self.assertEqual(exec_start_path(value), '/home/isucon/webapp/go/isuride')

    def test_returns_none_without_exec_start(self):
        self.assertIsNone(exec_start_path(''))


# 実際の ss -Htlnp の出力。プロセス名の列は空白で揃えられる
SS_OUTPUT = """\
LISTEN 0      151        127.0.0.1:3306       0.0.0.0:*    users:(("mysqld",pid=913,fd=31))
LISTEN 0      4096               *:8080             *:*    users:(("isuride",pid=1055,fd=6))
LISTEN 0      4096            [::]:8080          [::]:*    users:(("isuride",pid=1055,fd=7))
LISTEN 0      4096               *:6060             *:*    users:(("isuride",pid=1055,fd=8))
LISTEN 0      4096               *:12345            *:*    users:(("payment_mock",pid=10550,fd=3))
"""


class TestListeningPort(unittest.TestCase):
    def test_returns_smallest_port_of_process(self):
        self.assertEqual(listening_port(SS_OUTPUT, 1055), 6060)

    def test_does_not_match_pid_with_same_prefix(self):
        self.assertEqual(listening_port(SS_OUTPUT, 10550), 12345)

    def test_returns_none_when_process_does_not_listen(self):
        self.assertIsNone(listening_port(SS_OUTPUT, 0))


if __name__ == '__main__':
    unittest.main()
