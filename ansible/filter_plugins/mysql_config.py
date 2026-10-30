import re


def last_included_dir(my_cnf):
    """
    my.cnf の中身から、最後に読み込まれる !includedir のディレクトリを返す。無ければ None

    後に読み込まれた設定が優先されるので、既存の設定を上書きするファイルはここに置く
    """
    dirs = re.findall(r'^\s*!includedir\s+(\S+)', my_cnf, re.MULTILINE)
    return dirs[-1].rstrip('/') if dirs else None


class FilterModule:
    def filters(self):
        return {'last_included_dir': last_included_dir}
