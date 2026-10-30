import re

# MySQL と Debian のパッケージが作るユーザー。アプリは使わない
SYSTEM_USERS = {'root', 'mysql.sys', 'mysql.session', 'mysql.infoschema', 'debian-sys-maint'}
LOCAL_HOSTS = {'localhost', '127.0.0.1', '::1'}


def last_included_dir(my_cnf):
    """
    my.cnf の中身から、最後に読み込まれる !includedir のディレクトリを返す。無ければ None

    後に読み込まれた設定が優先されるので、既存の設定を上書きするファイルはここに置く
    """
    dirs = re.findall(r'^\s*!includedir\s+(\S+)', my_cnf, re.MULTILINE)
    return dirs[-1].rstrip('/') if dirs else None


def remote_mysql_users(user_hosts):
    """
    `mysql -N -B -e 'SELECT user, host FROM mysql.user'` の出力から、
    他のホストから接続できるユーザーを `user@host` の形で返す。システムのユーザーは除く

    DB を別ホストに移すと、アプリはこのどれかで接続することになる
    """
    rows = [line.split('\t') for line in user_hosts.splitlines() if line]
    return [f'{user}@{host}' for user, host in rows
            if user not in SYSTEM_USERS and host not in LOCAL_HOSTS]


class FilterModule:
    def filters(self):
        return {'last_included_dir': last_included_dir, 'remote_mysql_users': remote_mysql_users}
