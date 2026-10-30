# PYTHONPATH に ansible/filter_plugins を含めて実行する (make test)
import unittest

from deploy_actions import deploy_actions, deploy_http_checks

SERVICES = ['nginx', 'mysql', 'isucon-go']
CONFIG_DIRS = {'nginx': ['/etc/nginx/'], 'mysql': ['/etc/mysql/']}


def actions(changed_paths, services=SERVICES):
    return deploy_actions(changed_paths, services, 'isucon-go', CONFIG_DIRS)


class TestDeployHttpChecks(unittest.TestCase):
    def test_checks_application_http_at_detected_port(self):
        checks = deploy_http_checks(SERVICES, 'isucon-go', 3000)

        self.assertEqual([check['url'] for check in checks], [
            'http://127.0.0.1:3000/',
        ])
        self.assertIn(404, checks[0]['status_codes'])
        self.assertNotIn(500, checks[0]['status_codes'])

    def test_does_not_check_application_on_database_only_host(self):
        self.assertEqual(deploy_http_checks(['mysql'], 'isucon-go', None), [])

    def test_uses_configured_healthcheck_path_and_success_status(self):
        checks = deploy_http_checks(SERVICES, 'isucon-go', None, '/health', [204])

        self.assertEqual(checks[0], {'url': 'http://127.0.0.1:8080/health', 'status_codes': [204]})
        self.assertEqual(len(checks), 1)


class TestDeployActions(unittest.TestCase):
    def test_retry_reapplies_config_even_when_files_are_unchanged(self):
        self.assertEqual(deploy_actions([], SERVICES, 'isucon-go', CONFIG_DIRS, is_retry=True), {
            'restart_services': ['nginx', 'mysql', 'isucon-go'],
            'daemon_reload': True,
            'reload_sysctl': True,
        })

    def test_retry_does_not_restart_services_assigned_elsewhere(self):
        result = deploy_actions([], ['mysql'], 'isucon-go', CONFIG_DIRS, is_retry=True)

        self.assertEqual(result['restart_services'], ['mysql'])

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
