#!/usr/bin/env bash

set -euo pipefail

# Validate inputs
if [[ -z "${DIRECTORIES}" ]]; then
  echo "::error::DIRECTORIES is not set"
  exit 1
fi

echo "::group::Test whether any mise packages are installed or not"
numberOfInstalledMisePackages=$(mise ls --json | jq '. | length')
echo "Number of installed mise packages: ${numberOfInstalledMisePackages}"
if [[ ${numberOfInstalledMisePackages} -gt 0 ]]; then
  echo "Mise packages are installed"
  useUpgrade=true
  actionName=Upgrade
else
  echo "Mise packages are not installed"
  useUpgrade=false
  actionName=Install
fi
echo "::endgroup::"

# Unset in case it is set by an earlier run of this action
unset UV_PYTHON_DOWNLOADS

for dir in ${DIRECTORIES}; do
  echo "::group::${actionName} mise tools: ${dir}"
  pushd "${dir}"
  if [[ "${useUpgrade}" = true ]]; then
    mise upgrade
  else
    mise install
  fi
  popd
  echo "::endgroup::"
done

echo "::group::Mise prune"
mise prune
echo "::endgroup::"
