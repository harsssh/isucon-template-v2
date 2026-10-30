def deploy_actions(changed_paths, services, app_service, service_config_dirs):
    """
    設定ファイルの配布で変わったパスから、デプロイで行う操作を決める

    アプリは毎回ビルドするので、ホストに割り当てられていれば常に再起動する。
    他のサービスは、設定ディレクトリか unit ファイル (drop-in を含む) が変わったときだけ再起動する。
    restart_services は services の順序を保つ
    """
    def is_config_changed(service):
        config_dirs = service_config_dirs.get(service, [])
        return any(
            path.endswith(f'/{service}.service') or f'/{service}.service.d/' in path
            or path.startswith(tuple(config_dirs))
            for path in changed_paths
        )

    return {
        'restart_services': [s for s in services if s == app_service or is_config_changed(s)],
        'daemon_reload': any(path.endswith('.service') or '.service.d/' in path for path in changed_paths),
        'reload_sysctl': any(path.startswith('/etc/sysctl') for path in changed_paths),
    }


class FilterModule:
    def filters(self):
        return {'deploy_actions': deploy_actions}
