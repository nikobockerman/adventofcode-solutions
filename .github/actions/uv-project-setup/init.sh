#!/bin/bash

set -euo pipefail

# Verify GitHub Actions environment variables
if [[ -z "${GITHUB_ENV}" ]]; then
  echo "::error::GITHUB_ENV is not set"
  exit 1
fi
if [[ -z "${GITHUB_OUTPUT}" ]]; then
  echo "::error::GITHUB_OUTPUT is not set"
  exit 1
fi
if [[ -z "${RUNNER_OS}" ]]; then
  echo "::error::RUNNER_OS is not set"
  exit 1
fi
if [[ -z "${RUNNER_TEMP}" ]]; then
  echo "::error::RUNNER_TEMP is not set"
  exit 1
fi

# Validate inputs
if [[ -z "${CACHE_MODE}" ]]; then
  echo "::error::CACHE_MODE is not set"
  exit 1
fi
case "${CACHE_MODE}" in
  prepare|prepare-check-match|use)
    ;;
  *)
    echo "::error::Unknown cache mode: ${CACHE_MODE}"
    exit 1
    ;;
esac

if [[ -z "${DIRECTORY}" ]]; then
  echo "::error::Empty DIRECTORY is not supported"
  exit 1
fi

if [[ "${DIRECTORY}" = "." ]]; then
  echo "::error::Current directory is not supported"
  exit 1
fi

if [[ ! -d "${DIRECTORY}" ]]; then
  echo "::error::Directory does not exist: ${DIRECTORY}"
  exit 1
elif [[ ! -f "${DIRECTORY}/uv.lock" ]]; then
  echo "::error::Directory does not contain uv.lock: ${DIRECTORY}"
  exit 1
fi

pushd "${DIRECTORY}"
python_version=$(python -c 'import sys; print(f".".join(map(str, sys.version_info[:3])))')
mise_python_version=$(mise ls --current --json python | jq -r '.[0].version')
mise_uv_version=$(mise ls --current --json uv | jq -r '.[0].version')
popd

echo "::group::Tool versions"
echo "Python version: ${python_version}"
echo "Mise Python version: ${mise_python_version}"
echo "Mise uv version: ${mise_uv_version}"
echo "::endgroup::"

if [[ -z "${python_version}" ]]; then
  echo "::error::Failed to determine Python version"
  exit 1
fi
if [[ "${mise_python_version}" != "${python_version}" ]]; then
  echo "::error::Python version mismatch: ${mise_python_version} != ${python_version}"
  exit 1
fi

if [[ -z "${mise_uv_version}" ]]; then
  echo "::error::Failed to determine uv version"
  exit 1
fi

dir_key=${DIRECTORY/\//-}
cache_key_prefix="uv-${dir_key}-${RUNNER_OS}-${python_version}"
cache_key_uv_directory=$(sha256sum "${DIRECTORY}/uv.lock" | cut -d ' ' -f 1)
cache_key_uv_aoc_main=""
if [[ "${DIRECTORY}" != "aoc-main" ]]; then
  cache_key_uv_aoc_main=$(sha256sum "aoc-main/uv.lock" | cut -d ' ' -f 1)
fi

uv_cache_dir="${RUNNER_TEMP}/aoc-uv-cache"

echo "::group::Environment variable changes"
{
  echo -n "UV_CACHE_DIR="
  echo "${uv_cache_dir}" | tr -d '\n'
  echo
} | tee -a "${GITHUB_ENV}"
echo "::endgroup::"

echo "::group::Outputs from init"
{
  # Install directories
  echo "uv-install-directories<<ENDDIRS"
  echo "${DIRECTORY}"
  if [[ "${DIRECTORY}" != "aoc-main" ]]; then
    echo "aoc-main"
  fi
  echo "ENDDIRS"

  # Cache key
  cache_key="${cache_key_prefix}-${mise_uv_version}-${cache_key_uv_directory}"
  if [[ -n "${cache_key_uv_aoc_main}" ]]; then
    cache_key="${cache_key}-${cache_key_uv_aoc_main}"
  fi
  echo "cache-key=${cache_key}"

  # Cache restore keys
  echo "cache-restore-keys<<ENDKEYS"
  if [[ -n "${cache_key_uv_aoc_main}" ]]; then
    echo "${cache_key_prefix}-${mise_uv_version}-${cache_key_uv_directory}"-
  fi
  echo "${cache_key_prefix}-${mise_uv_version}-"
  echo "${cache_key_prefix}-"
  echo "ENDKEYS"

  # Cache paths
  echo "cache-paths<<ENDPATHS"
  echo "${uv_cache_dir}"
  echo "${DIRECTORY}/.venv"
  if [[ "${DIRECTORY}" != "aoc-main" ]]; then
    echo "aoc-main/.venv"
  fi
  echo "ENDPATHS"
} | tee -a "${GITHUB_OUTPUT}"
echo "::endgroup::"
