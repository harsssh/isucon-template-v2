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


class FilterModule:
    def filters(self):
        return {'services_in_directory': services_in_directory}
