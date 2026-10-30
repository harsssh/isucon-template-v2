import re


def _parse_systemctl_show(systemctl_show_output):
    """`systemctl show <unit>...` の出力を、unit ごとのプロパティの dict のリストにする"""
    return [
        dict(line.split('=', 1) for line in block.splitlines() if '=' in line)
        for block in systemctl_show_output.split('\n\n')
    ]


def services_in_directory(systemctl_show_output, working_directory):
    """
    `systemctl show -p Id -p WorkingDirectory <unit>...` の出力から、
    WorkingDirectory が working_directory のサービス名 (.service を除く) を返す

    参照実装は言語ごとにサービスがあり、WorkingDirectory で言語を区別できる
    """
    return [
        unit['Id'].removesuffix('.service')
        for unit in _parse_systemctl_show(systemctl_show_output)
        if 'Id' in unit and unit.get('WorkingDirectory', '').rstrip('/') == working_directory.rstrip('/')
    ]


def loaded_services(systemctl_show_output):
    """
    `systemctl show -p Id -p LoadState <unit>...` の出力から、存在するサービス名 (.service を除く) を順に返す

    別名で指定した unit は Id が本来の名前になるので、MariaDB の別名の mysql.service は mariadb になる
    """
    names = [
        unit['Id'].removesuffix('.service')
        for unit in _parse_systemctl_show(systemctl_show_output)
        if unit.get('LoadState') == 'loaded'
    ]
    return list(dict.fromkeys(names))


def exec_start_path(exec_start):
    """
    systemd の ExecStart プロパティの値 (`{ path=... ; argv[]=... }`) から、起動する実行ファイルのパスを返す。無ければ None
    """
    match = re.search(r"\bpath=(\S+)", exec_start)
    return match.group(1) if match else None


def environment_file_paths(environment_files):
    """
    systemd の EnvironmentFiles プロパティの値 (`/home/isucon/env.sh (ignore_errors=no) ...`) から、ファイルのパスを返す
    """
    return re.findall(r'(\S+) \(ignore_errors=\w+\)', environment_files)


def listening_port(ss_output, pids):
    """
    `ss -Htlnp` の出力から、pids のどれかのプロセスが listen している最小のポート番号を返す。無ければ None

    IPv4 と IPv6 で同じポートを listen していることがあるので、最小のものを選ぶ
    """
    pid_pattern = re.compile(r'\bpid=(\d+),')
    pid_set = {int(pid) for pid in pids}
    ports = [
        int(line.split()[3].rsplit(':', 1)[1])
        for line in ss_output.splitlines()
        if any(int(pid) in pid_set for pid in pid_pattern.findall(line))
    ]
    return min(ports, default=None)


class FilterModule:
    def filters(self):
        return {
            'services_in_directory': services_in_directory,
            'loaded_services': loaded_services,
            'exec_start_path': exec_start_path,
            'environment_file_paths': environment_file_paths,
            'listening_port': listening_port,
        }
