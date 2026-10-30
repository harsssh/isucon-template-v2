#!/usr/bin/env bash
# カレントディレクトリ (リポジトリの config/) の common/ と <host>/ にある設定ファイルを <dest_root> 以下の同じパスに置き、
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
	done < <(find "$dir" \( -type f -o -type l \) -print0)
done

for rel_path in "${!sources[@]}"; do
	src_path=${sources[$rel_path]}
	dest_path=${dest_root%/}/$rel_path
	if [ -L "$src_path" ]; then
		link_target=$(readlink "$src_path")
		if [ ! -L "$dest_path" ] || [ "$(readlink "$dest_path")" != "$link_target" ]; then
			mkdir -p "$(dirname "$dest_path")"
			ln -sfnT "$link_target" "$dest_path"
			echo "$dest_path"
		fi
	elif [ -L "$dest_path" ] || ! cmp -s "$src_path" "$dest_path"; then
		# リンク先を上書きせず、リポジトリで指定した通常ファイルに置き換える
		if [ -L "$dest_path" ]; then
			rm -f "$dest_path"
		fi
		install -D -m "$(stat -c %a "$src_path")" "$src_path" "$dest_path"
		echo "$dest_path"
	fi
done
