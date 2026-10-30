# PYTHONPATH に ansible/filter_plugins を含めて実行する (make test)
import unittest

from nginx_config import nginx_files_with_directive, nginx_includes, nginx_local_upstream_ports

# nginx -T の出力の形。ISUCON14 の s1 の出力を縮めたもの
DUMP = """\
nginx: the configuration file /etc/nginx/nginx.conf syntax is ok
nginx: configuration file /etc/nginx/nginx.conf test is successful
# configuration file /etc/nginx/nginx.conf:
user www-data;
http {
	include /etc/nginx/mime.types;
	access_log /var/log/nginx/access.log;
	# access_log /var/log/nginx/old.log;
	include /etc/nginx/conf.d/*.conf;
	include /etc/nginx/sites-enabled/*;
}

# configuration file /etc/nginx/sites-enabled/isuride.conf:
server {
  location /api/ {
    proxy_pass http://localhost:8080;
  }
}
"""


class TestNginxIncludes(unittest.TestCase):
    def test_returns_true_for_file_matching_include(self):
        self.assertTrue(nginx_includes(DUMP, '/etc/nginx/conf.d/ltsv-log.conf'))

    def test_returns_false_for_file_not_included(self):
        self.assertFalse(nginx_includes(DUMP, '/etc/nginx/extra/ltsv-log.conf'))

    def test_resolves_relative_include_from_prefix(self):
        dump = '# configuration file /etc/nginx/nginx.conf:\nhttp {\n  include conf.d/*.conf;\n}\n'

        self.assertTrue(nginx_includes(dump, '/etc/nginx/conf.d/ltsv-log.conf'))

    def test_ignores_commented_include(self):
        dump = '# configuration file /etc/nginx/nginx.conf:\n# include /etc/nginx/conf.d/*.conf;\n'

        self.assertFalse(nginx_includes(dump, '/etc/nginx/conf.d/ltsv-log.conf'))

    def test_returns_false_when_nginx_is_missing(self):
        self.assertFalse(nginx_includes('', '/etc/nginx/conf.d/ltsv-log.conf'))


class TestNginxFilesWithDirective(unittest.TestCase):
    def test_returns_files_with_uncommented_directive(self):
        self.assertEqual(nginx_files_with_directive(DUMP, 'access_log'), ['/etc/nginx/nginx.conf'])

    def test_returns_empty_when_directive_is_absent(self):
        self.assertEqual(nginx_files_with_directive(DUMP, 'error_log'), [])


class TestNginxLocalUpstreamPorts(unittest.TestCase):
    def test_returns_port_of_proxy_pass(self):
        self.assertEqual(nginx_local_upstream_ports(DUMP), [8080])

    def test_returns_ports_of_upstream_servers(self):
        dump = (
            '# configuration file /etc/nginx/nginx.conf:\n'
            'upstream app {\n  server 127.0.0.1:3000;\n  server s2:3000;\n}\n'
            'server {\n  listen 80;\n  location / { proxy_pass http://app; }\n}\n'
        )

        self.assertEqual(nginx_local_upstream_ports(dump), [3000])

    def test_returns_empty_without_local_upstream(self):
        dump = '# configuration file /etc/nginx/nginx.conf:\nserver {\n  root /var/www;\n}\n'

        self.assertEqual(nginx_local_upstream_ports(dump), [])


if __name__ == '__main__':
    unittest.main()
