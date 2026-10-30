import fnmatch
import os
import re

# nginx -T は読み込んだファイルごとに、この行の後に中身を出力する
_FILE_HEADER = re.compile(r'^# configuration file (.+):$', re.MULTILINE)
_LOCAL_HOSTS = r'(?:localhost|127\.0\.0\.1|\[::1\])'


def _config_files(nginx_dump):
    """`nginx -T` の出力を {ファイルのパス: コメントを除いた中身} にする"""
    parts = _FILE_HEADER.split(nginx_dump)
    return {
        path: re.sub(r'#.*', '', content)
        for path, content in zip(parts[1::2], parts[2::2])
    }


def nginx_includes(nginx_dump, path, prefix='/etc/nginx'):
    """
    `nginx -T` の出力から、path のファイルを置けば読み込まれるかを返す

    include の相対パスは nginx の prefix (Debian では /etc/nginx) からのパスとして扱う
    """
    patterns = [
        os.path.join(prefix, pattern)
        for content in _config_files(nginx_dump).values()
        for pattern in re.findall(r'^\s*include\s+([^;\s]+)\s*;', content, re.MULTILINE)
    ]
    return any(fnmatch.fnmatch(path, pattern) for pattern in patterns)


def nginx_files_with_directive(nginx_dump, directive):
    """`nginx -T` の出力から、directive を書いているファイルのパスを返す。コメントアウトしたものは除く"""
    return [
        path
        for path, content in _config_files(nginx_dump).items()
        if re.search(rf'^\s*{re.escape(directive)}\s', content, re.MULTILINE)
    ]


def nginx_local_upstream_ports(nginx_dump):
    """
    `nginx -T` の出力から、proxy_pass と upstream の server で転送する、自ホストのポート番号を返す

    アプリが Docker で動くなど、unit のプロセスからポートが分からないときに使う
    """
    ports = {
        int(port)
        for content in _config_files(nginx_dump).values()
        for port in re.findall(
            rf'^\s*(?:proxy_pass\s+https?://|server\s+){_LOCAL_HOSTS}:(\d+)', content, re.MULTILINE)
    }
    return sorted(ports)


class FilterModule:
    def filters(self):
        return {
            'nginx_includes': nginx_includes,
            'nginx_files_with_directive': nginx_files_with_directive,
            'nginx_local_upstream_ports': nginx_local_upstream_ports,
        }
