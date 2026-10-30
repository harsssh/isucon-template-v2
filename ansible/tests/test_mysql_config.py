# PYTHONPATH に ansible/filter_plugins を含めて実行する (make test)
import unittest

from mysql_config import last_included_dir, remote_mysql_users

# Ubuntu の MySQL の /etc/mysql/my.cnf の末尾
MY_CNF = """\
# * IMPORTANT: Additional settings that can override those from this file!
#   The files must end with '.cnf', otherwise they'll be ignored.
#
!includedir /etc/mysql/conf.d/
!includedir /etc/mysql/mysql.conf.d/
"""


class TestLastIncludedDir(unittest.TestCase):
    def test_returns_last_included_dir(self):
        self.assertEqual(last_included_dir(MY_CNF), '/etc/mysql/mysql.conf.d')

    def test_returns_none_without_includedir(self):
        self.assertIsNone(last_included_dir('[mysqld]\nport = 3306\n'))


# ISUCON14 のサーバーの mysql.user
USER_HOSTS = """\
isucon\t%
debian-sys-maint\tlocalhost
mysql.infoschema\tlocalhost
mysql.session\tlocalhost
mysql.sys\tlocalhost
root\tlocalhost
"""


class TestRemoteMysqlUsers(unittest.TestCase):
    def test_returns_users_with_non_local_host(self):
        self.assertEqual(remote_mysql_users(USER_HOSTS), ['isucon@%'])

    def test_excludes_users_only_on_local_hosts(self):
        user_hosts = 'isucon\tlocalhost\nisucon\t127.0.0.1\nisucon\t::1\n'
        self.assertEqual(remote_mysql_users(user_hosts), [])

    def test_excludes_system_users_on_any_host(self):
        self.assertEqual(remote_mysql_users('root\t%\n'), [])

    def test_returns_empty_without_output(self):
        self.assertEqual(remote_mysql_users(''), [])


if __name__ == '__main__':
    unittest.main()
