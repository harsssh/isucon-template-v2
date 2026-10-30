import os
import subprocess
import tempfile
import unittest

SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'distribute_config.sh')


def write(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w') as f:
        f.write(content)


def read(path):
    with open(path) as f:
        return f.read()


class TestDistributeConfig(unittest.TestCase):
    def setUp(self):
        self.repo = tempfile.mkdtemp()
        self.root = tempfile.mkdtemp()

    def distribute(self, host='s1'):
        result = subprocess.run(
            [SCRIPT, host, self.root], cwd=self.repo, capture_output=True, text=True, check=True
        )
        return sorted(result.stdout.splitlines())

    def test_copies_common_files(self):
        write(f'{self.repo}/common/etc/nginx/nginx.conf', 'common')

        changed = self.distribute()

        self.assertEqual(changed, [f'{self.root}/etc/nginx/nginx.conf'])
        self.assertEqual(read(f'{self.root}/etc/nginx/nginx.conf'), 'common')

    def test_host_files_take_precedence_over_common(self):
        write(f'{self.repo}/common/etc/nginx/nginx.conf', 'common')
        write(f'{self.repo}/s1/etc/nginx/nginx.conf', 's1')

        self.distribute()

        self.assertEqual(read(f'{self.root}/etc/nginx/nginx.conf'), 's1')

    def test_ignores_other_hosts(self):
        write(f'{self.repo}/s2/etc/nginx/nginx.conf', 's2')

        self.assertEqual(self.distribute(), [])
        self.assertFalse(os.path.exists(f'{self.root}/etc/nginx/nginx.conf'))

    def test_reports_nothing_when_unchanged(self):
        write(f'{self.repo}/common/etc/nginx/nginx.conf', 'common')
        write(f'{self.repo}/s1/etc/nginx/nginx.conf', 's1')
        self.distribute()

        self.assertEqual(self.distribute(), [])

    def test_reports_only_changed_files(self):
        write(f'{self.repo}/common/etc/nginx/nginx.conf', 'v1')
        write(f'{self.repo}/common/etc/mysql/my.cnf', 'v1')
        self.distribute()
        write(f'{self.repo}/common/etc/mysql/my.cnf', 'v2')

        self.assertEqual(self.distribute(), [f'{self.root}/etc/mysql/my.cnf'])


if __name__ == '__main__':
    unittest.main()
