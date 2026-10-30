import re


def services_in_directory(systemctl_show_output, working_directory):
    """
    `systemctl show -p Id -p WorkingDirectory <unit>...` の出力から、
    WorkingDirectory が working_directory のサービス名 (.service を除く) を返す

    参照実装は言語ごとにサービスがあり、WorkingDirectory で言語を区別できる
    """
    units = [
        dict(line.split('=', 1) for line in block.splitlines() if '=' in line)
        for block in systemctl_show_output.split('\n\n')
    ]
    return [
        unit['Id'].removesuffix('.service')
        for unit in units
        if 'Id' in unit and unit.get('WorkingDirectory', '').rstrip('/') == working_directory.rstrip('/')
    ]


def exec_start_path(exec_start):
    """
    systemd の ExecStart プロパティの値 (`{ path=... ; argv[]=... }`) から、起動する実行ファイルのパスを返す。無ければ None
    """
    match = re.search(r"\bpath=(\S+)", exec_start)
    return match.group(1) if match else None


def listening_port(ss_output, pid):
    """
    `ss -Htlnp` の出力から、pid のプロセスが listen している最小のポート番号を返す。無ければ None

    IPv4 と IPv6 で同じポートを listen していることがあるので、最小のものを選ぶ
    """
    ports = [
        int(line.split()[3].rsplit(':', 1)[1])
        for line in ss_output.splitlines()
        if f'pid={pid},' in line
    ]
    return min(ports, default=None)


class FilterModule:
    def filters(self):
        return {
            'services_in_directory': services_in_directory,
            'exec_start_path': exec_start_path,
            'listening_port': listening_port,
        }
