#!/usr/bin/env bash
#MISE description="Check shell scripts in repository with shfmt"

set -euo pipefail

files_output=$(git ls-files | grep '.sh$')
mapfile -t files < <(echo "${files_output}")
if [[ "${#files[@]}" -eq 0 ]]; then
  echo "No .sh files found to check with shfmt"
  exit 0
fi

shfmt -d "${files[@]}"
