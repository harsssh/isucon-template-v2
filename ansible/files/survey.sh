#!/bin/bash
# サーバーの状態を Markdown で出力する。何も変更しない
#   survey.sh <webapp_dir>
# root で実行する (MySQL に unix socket の root で接続するため)

webapp_dir="$1"

section() {
	local title="$1"
	shift
	printf '## %s\n\n```\n' "$title"
	"$@" 2>&1
	printf '```\n\n'
}

os() {
	grep PRETTY_NAME /etc/os-release
	uname -m
	echo "CPU: $(nproc)"
	free -h
}

isu_unit_files() {
	systemctl list-unit-files --type=service --no-legend 'isu*' | awk '$1 !~ /@/ {print $1}' |
		while read -r unit; do
			systemctl cat "$unit"
			echo
		done
}

webapp() {
	ls -la "$(dirname "$webapp_dir")"
	echo
	ls -la "$webapp_dir/"
}

env_files() {
	for file in "$(dirname "$webapp_dir")"/env*; do
		[ -f "$file" ] || continue
		echo "# $file"
		cat "$file"
	done
}

table_sizes() {
	mysql -e "
		SELECT table_schema, table_name, table_rows,
			ROUND((data_length + index_length) / 1024 / 1024) AS size_mb
		FROM information_schema.tables
		WHERE table_schema NOT IN ('mysql', 'information_schema', 'performance_schema', 'sys')
		ORDER BY size_mb DESC, table_rows DESC"
}

section "OS" os
section "動いているサービス" systemctl list-units --type=service --state=running --no-legend --no-pager
section "isu で始まるサービスの unit ファイル" isu_unit_files
section "listen しているポート" ss -tlnp
section "CPU 使用率の高いプロセス" bash -c 'ps -eo user,pid,%cpu,%mem,rss,args --sort=-%cpu | head -20'
section "webapp" webapp
section "環境変数のファイル" env_files
section "nginx の設定ファイル" find /etc/nginx -type f -o -type l
section "MySQL の設定ファイル" find /etc/mysql -type f -o -type l
section "MySQL のバージョン" mysql --version
section "テーブルのサイズ" table_sizes
section "Docker のコンテナ" docker ps
