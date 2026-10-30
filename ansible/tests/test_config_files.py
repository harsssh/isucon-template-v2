# PYTHONPATH に ansible/filter_plugins を含めて実行する (make test)
import unittest

from config_files import differing_config_files

PRIMARY = """\
aaa  /etc/nginx/nginx.conf
bbb  /home/isucon/env.sh
"""


class TestDifferingConfigFiles(unittest.TestCase):
    def test_returns_nothing_when_files_are_same(self):
        self.assertEqual(differing_config_files(PRIMARY, PRIMARY), [])

    def test_returns_file_with_different_content(self):
        checksums = 'aaa  /etc/nginx/nginx.conf\nccc  /home/isucon/env.sh\n'

        self.assertEqual(differing_config_files(checksums, PRIMARY), ['/home/isucon/env.sh'])

    def test_returns_files_only_on_one_host(self):
        checksums = 'aaa  /etc/nginx/nginx.conf\nddd  /etc/nginx/sites-enabled/isucon.conf\n'

        self.assertEqual(
            differing_config_files(checksums, PRIMARY),
            ['/etc/nginx/sites-enabled/isucon.conf', '/home/isucon/env.sh'],
        )

    def test_keeps_spaces_in_path(self):
        checksums = PRIMARY + 'eee  /etc/nginx/a b.conf\n'

        self.assertEqual(differing_config_files(checksums, PRIMARY), ['/etc/nginx/a b.conf'])


if __name__ == '__main__':
    unittest.main()
