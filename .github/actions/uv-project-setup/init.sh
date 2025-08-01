#!/bin/bash

set -xe

case "$CACHE_MODE" in
  prepare)
    save_cache=true
    fail_on_cache_miss=false
    ;;
  use)
    save_cache=false
    fail_on_cache_miss=true
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

dir_key=${DIRECTORY/\//-}
cache_key_prefix="uv-${dir_key}-${RUNNER_OS}"
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
  echo "fail-on-cache-miss=${fail_on_cache_miss}"
  echo "save-cache=${save_cache}"

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
