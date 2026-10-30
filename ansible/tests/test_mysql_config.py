# PYTHONPATH に ansible/filter_plugins を含めて実行する (make test)
import unittest

from mysql_config import last_included_dir

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


if __name__ == '__main__':
    unittest.main()
