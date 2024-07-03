#!/bin/bash -e

config_dir_names=("common" "$(hostname)")

for config_dir_name in "${config_dir_names[@]}"; do
	(
		cd "$config_dir_name" &&
			find . -type f | while read -r rel_path; do
				src_path=$(pwd)/$rel_path
				dest_path=${rel_path#.}
				cp -auv "$src_path" "$dest_path"
			done
	)
done
