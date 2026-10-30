#!/usr/bin/env bash
# リポジトリの common/ と <host>/ にある設定ファイルを <dest_root> 以下の同じパスに置き、
# 内容が変わったファイルのパスを 1 行ずつ出力する。同じパスのファイルは <host>/ を優先する
# Usage: distribute_config.sh <host> [dest_root]
set -euo pipefail

host=$1
dest_root=${2:-/}

declare -A sources
for dir in common "$host"; do
	[ -d "$dir" ] || continue
	while IFS= read -r -d '' path; do
		sources[${path#"$dir"/}]=$path
	done < <(find "$dir" -type f -print0)
done

for rel_path in "${!sources[@]}"; do
	src_path=${sources[$rel_path]}
	dest_path=${dest_root%/}/$rel_path
	if ! cmp -s "$src_path" "$dest_path"; then
		install -D -m "$(stat -c %a "$src_path")" "$src_path" "$dest_path"
		echo "$dest_path"
	fi
done
