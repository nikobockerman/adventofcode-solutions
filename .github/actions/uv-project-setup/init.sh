#!/bin/bash

set -xe

case "$CACHE_MODE" in
  prepare|use)
    ;;
  *)
    echo "::error Unknown cache mode: $CACHE_MODE"
    exit 1
    ;;
esac

if [ -z "$DIRECTORY" ]; then
  echo "::error Empty DIRECTORY is not supported"
  exit 1
fi

if [ "$DIRECTORY" = "." ]; then
  echo "::error Current directory is not supported"
  exit 1
fi

if [ ! -d "$DIRECTORY" ]; then
  echo "::error Directory does not exist: $DIRECTORY"
  exit 1
elif [ ! -f "$DIRECTORY/uv.lock" ]; then
  echo "::error Directory does not contain uv.lock: $DIRECTORY"
  exit 1
fi

pushd "$DIRECTORY"
python_version=$(python -c 'import sys; print(f".".join(map(str, sys.version_info[:3])))')
mise_python_version=$(mise ls --current --json python | jq -r '.[0].version')
popd
echo "::debug Python version: $python_version"
echo "::debug Mise Python version: $mise_python_version"
if [ -z "$python_version" ]; then
  echo "::error Failed to determine Python version"
  exit 1
fi
if [ "$mise_python_version" != "$python_version" ]; then
  echo "::error Python version mismatch: $mise_python_version != $python_version"
  exit 1
fi

dir_key=${DIRECTORY/\//-}
cache_key_prefix="uv-${dir_key}-${RUNNER_OS}-${python_version}"
cache_key_uv_directory=$(sha256sum "${DIRECTORY}/uv.lock" | cut -d ' ' -f 1)
cache_key_uv_aoc_main=""
if [ "$DIRECTORY" != "aoc-main" ]; then
  cache_key_uv_aoc_main=$(sha256sum "aoc-main/uv.lock" | cut -d ' ' -f 1)
fi

cache_key="${cache_key_prefix}-${cache_key_uv_directory}"
if [ -n "${cache_key_uv_aoc_main}" ]; then
  cache_key="${cache_key}-${cache_key_uv_aoc_main}"
fi


uv_cache_dir="${RUNNER_TEMP}/aoc-uv-cache"

# Set environment variables for remaining workflow
{
  echo "UV_CACHE_DIR=${uv_cache_dir}"
} >> "$GITHUB_ENV"

# Set outputs
{
  echo "cache-key=${cache_key}"

  # Install directories
  echo "uv-install-directories<<ENDDIRS"
  echo "${DIRECTORY}"
  if [ "${DIRECTORY}" != "aoc-main" ]; then
    echo "aoc-main"
  fi
  echo "ENDDIRS"

  # Cache restore keys
  echo "cache-restore-keys<<ENDKEYS"
  if [ "$CACHE_MODE" = "prepare" ]; then
    if [ -n "${cache_key_uv_aoc_main}" ]; then
      echo "${cache_key_prefix}-${cache_key_uv_directory}"-
    fi
    echo "${cache_key_prefix}-"
  fi
  echo "ENDKEYS"

  # Cache paths
  echo "cache-paths<<ENDPATHS"
  echo "${uv_cache_dir}"
  echo "${DIRECTORY}/.venv"
  if [ "$DIRECTORY" != "aoc-main" ]; then
    echo "aoc-main/.venv"
  fi
  echo "ENDPATHS"
} >> "$GITHUB_OUTPUT"
