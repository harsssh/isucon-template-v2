# PYTHONPATH に ansible/filter_plugins を含めて実行する (make test)
import unittest

from deploy_actions import deploy_actions

SERVICES = ['nginx', 'mysql', 'isucon-go']
CONFIG_DIRS = {'nginx': ['/etc/nginx/'], 'mysql': ['/etc/mysql/']}


def actions(changed_paths, services=SERVICES):
    return deploy_actions(changed_paths, services, 'isucon-go', CONFIG_DIRS)


class TestDeployActions(unittest.TestCase):
    def test_restarts_only_app_when_nothing_changed(self):
        self.assertEqual(actions([]), {
            'restart_services': ['isucon-go'],
            'daemon_reload': False,
            'reload_sysctl': False,
        })

    def test_restarts_service_whose_config_changed(self):
        result = actions(['/etc/mysql/mysql.conf.d/mysqld.cnf'])

        self.assertEqual(result['restart_services'], ['mysql', 'isucon-go'])

    def test_restarts_service_whose_unit_file_changed(self):
        result = actions(['/lib/systemd/system/nginx.service'])

        self.assertEqual(result['restart_services'], ['nginx', 'isucon-go'])
        self.assertTrue(result['daemon_reload'])

    def test_ignores_services_not_assigned_to_host(self):
        result = actions(['/etc/nginx/nginx.conf'], services=['mysql'])

        self.assertEqual(result['restart_services'], [])

    def test_reloads_sysctl_when_sysctl_config_changed(self):
        self.assertTrue(actions(['/etc/sysctl.d/99-isucon.conf'])['reload_sysctl'])

    def test_restarts_service_whose_drop_in_changed(self):
        result = actions(['/etc/systemd/system/mysql.service.d/override.conf'])

        self.assertEqual(result['restart_services'], ['mysql', 'isucon-go'])
        self.assertTrue(result['daemon_reload'])

    def test_does_not_confuse_services_with_common_prefix(self):
        result = actions(['/etc/systemd/system/nginx-exporter.service'])

        self.assertEqual(result['restart_services'], ['isucon-go'])


if __name__ == '__main__':
    unittest.main()
