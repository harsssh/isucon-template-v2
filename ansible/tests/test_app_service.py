# PYTHONPATH に ansible/filter_plugins を含めて実行する (make test)
import unittest

from app_service import (
    cgroup_search_paths,
    environment_file_paths,
    exec_start_path,
    listening_port,
    loaded_services,
    services_in_directory,
)

# systemctl show は -p の順序によらず、プロパティを決まった順序で出力する
SHOW_OUTPUT = """\
WorkingDirectory=/home/isucon/webapp/go
Id=isupipe-go.service

WorkingDirectory=/home/isucon/webapp/python
Id=isupipe-python.service

WorkingDirectory=/
Id=isupipe-dns.service
"""


class TestCgroupSearchPaths(unittest.TestCase):
    def test_searches_only_the_application_cgroup(self):
        self.assertEqual(cgroup_search_paths('/system.slice/app.service'), [
            '/sys/fs/cgroup/system.slice/app.service',
            '/sys/fs/cgroup/unified/system.slice/app.service',
            '/sys/fs/cgroup/systemd/system.slice/app.service',
        ])

    def test_does_not_search_the_host_when_cgroup_is_empty_or_root(self):
        for value in ['', '/', None]:
            with self.subTest(control_group=value):
                self.assertEqual(cgroup_search_paths(value), [])


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


class TestLoadedServices(unittest.TestCase):
    def test_returns_existing_service(self):
        output = 'Id=mysql.service\nLoadState=loaded\n\nId=mariadb.service\nLoadState=not-found\n'

        self.assertEqual(loaded_services(output), ['mysql'])

    def test_resolves_alias_to_real_name(self):
        output = 'Id=mariadb.service\nLoadState=loaded\n\nId=mariadb.service\nLoadState=loaded\n'

        self.assertEqual(loaded_services(output), ['mariadb'])

    def test_returns_empty_when_no_service_exists(self):
        output = 'Id=mysql.service\nLoadState=not-found\n'

        self.assertEqual(loaded_services(output), [])


class TestEnvironmentFilePaths(unittest.TestCase):
    def test_returns_paths_of_files(self):
        value = '/home/isucon/env.sh (ignore_errors=no) /home/isucon/env.local (ignore_errors=yes)'

        self.assertEqual(environment_file_paths(value), ['/home/isucon/env.sh', '/home/isucon/env.local'])

    def test_returns_empty_without_environment_files(self):
        self.assertEqual(environment_file_paths(''), [])


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
        self.assertEqual(listening_port(SS_OUTPUT, [1055]), 6060)

    def test_returns_port_of_any_process(self):
        # unit の cgroup にはラッパーのシェルと、listen する子プロセスが入る
        self.assertEqual(listening_port(SS_OUTPUT, ['1000', '10550']), 12345)

    def test_does_not_match_pid_with_same_prefix(self):
        self.assertEqual(listening_port(SS_OUTPUT, [10550]), 12345)

    def test_returns_none_when_process_does_not_listen(self):
        self.assertIsNone(listening_port(SS_OUTPUT, [0]))


if __name__ == '__main__':
    unittest.main()
