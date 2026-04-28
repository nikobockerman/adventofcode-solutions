#!/bin/bash

set -euo pipefail

conanHome=${RUNNER_TEMP}/aoc-conan-home

export CONAN_HOME="${conanHome}"

echo "::group::Install settings_user.yml"
mkdir -p "${CONAN_HOME}"
cp "${GITHUB_WORKSPACE}/.github/files/settings_user.yml" "${CONAN_HOME}/"
echo "::endgroup::"

echo "::group::Detect Conan profile"
pushd solvers/cpp
conan profile detect
popd
echo "::endgroup::"

echo "::group::Environment variable changes"
{
  echo -n "CONAN_HOME="
  echo "${conanHome}" | tr -d '\n'
  echo
} | tee -a "${GITHUB_ENV}"
echo "::endgroup::"

echo "::group::Outputs from init"
{
  echo "conan-cache-path=${conanHome}/p"
} | tee -a "${GITHUB_OUTPUT}"
echo "::endgroup::"
