#!/usr/bin/env bash
#MISE description="Check Python codes using Pyright. Checks all Python files outside the python project directories."

set -euo pipefail

files_output=$(git ls-files | grep '.py$' | grep -v '^solvers/python/' | grep -v '^aoc-main/')
mapfile -t files < <(echo "${files_output}")
if [[ "${#files[@]}" -eq 0 ]]; then
  echo "No .py files found to check with pyright"
  exit 0
fi

pyright "${files[@]}"
