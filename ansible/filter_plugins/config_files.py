def differing_config_files(checksums, primary_checksums):
    """
    2 つのホストの `sha256sum <file>...` の出力を比べ、内容が違うか片方にしか無いファイルのパスを返す

    deploy は primary から集めた設定ファイルを全ホストに配るので、
    primary と違うファイルは deploy で上書きされるか、primary にしか無いファイルが追加される
    """
    def parse(sha256sum_output):
        return dict(reversed(line.split(maxsplit=1)) for line in sha256sum_output.splitlines() if line)

    files = parse(checksums)
    primary_files = parse(primary_checksums)
    return sorted(path for path in files.keys() | primary_files.keys() if files.get(path) != primary_files.get(path))


class FilterModule:
    def filters(self):
        return {'differing_config_files': differing_config_files}
