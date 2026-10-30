def deploy_actions(changed_paths, services, app_service, service_config_dirs, is_retry=False):
    """
    設定ファイルの配布で変わったパスから、デプロイで行う操作を決める

    アプリは毎回ビルドするので、ホストに割り当てられていれば常に再起動する。
    他のサービスは、設定ディレクトリか unit ファイル (drop-in を含む) が変わったときだけ再起動する。
    restart_services は services の順序を保つ。
    中断後の再実行では、前回コピー済みの設定も反映するため全操作をやり直す
    """
    def is_config_changed(service):
        config_dirs = service_config_dirs.get(service, [])
        return any(
            path.endswith(f'/{service}.service') or f'/{service}.service.d/' in path
            or path.startswith(tuple(config_dirs))
            for path in changed_paths
        )

    return {
        'restart_services': [s for s in services if is_retry or s == app_service or is_config_changed(s)],
        'daemon_reload': is_retry or any(path.endswith('.service') or '.service.d/' in path for path in changed_paths),
        'reload_sysctl': is_retry or any(path.startswith('/etc/sysctl') for path in changed_paths),
    }


def deploy_http_checks(services, app_service, app_port, app_path='/', app_status_codes=None):
    """アプリを動かすホストだけで HTTP の疎通を確認する"""
    if app_service not in services:
        return []
    base_url = f'http://127.0.0.1:{app_port or 8080}'
    return [
        {'url': base_url + app_path,
         'status_codes': list(range(200, 500)) if app_status_codes is None else app_status_codes},
    ]


class FilterModule:
    def filters(self):
        return {'deploy_actions': deploy_actions, 'deploy_http_checks': deploy_http_checks}
