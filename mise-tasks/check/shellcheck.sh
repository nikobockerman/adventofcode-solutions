#!/usr/bin/env bash
#MISE description="Check shell scripts in repository with shellcheck"

set -euo pipefail

files_output=$(git ls-files | grep '.sh$')
mapfile -t files < <(echo "${files_output}")
if [[ "${#files[@]}" -eq 0 ]]; then
  echo "No .sh files found to check with shellcheck"
  exit 0
fi

shellcheck "${files[@]}"
