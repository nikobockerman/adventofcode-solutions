#!/bin/bash

set -xe

# TODO: Verify whether SEP is needed or not
if [ "$RUNNER_OS" = "Windows" ]; then
  SEP="\\"
else
  SEP="/"
fi


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

if [ -z "${DIRECTORY}" ]; then
  echo "::error Empty DIRECTORY is not supported"
  exit 1
elif [ ! -d "$DIRECTORY" ]; then
  echo "::error Directory does not exist: $DIRECTORY"
  exit 1
elif [ ! -f "$DIRECTORY/mise.toml" ]; then
  echo "::error Directory does not contain mise.toml: $DIRECTORY"
  exit 1
fi

if [ "${DIRECTORY}" = "." ]; then
  dir_key=""
else
  dir_key="-${DIRECTORY/\//-}"
fi

cache_key_prefix="mise${dir_key}-${MISE_VERSION}-${RUNNER_OS}"
cache_key_mise_root=$(sha256sum "mise.toml" | cut -d ' ' -f 1)
cache_key_mise_directory=""
cache_key_mise_aoc_main=""
if [ "${DIRECTORY}" != "." ]; then
  cache_key_mise_directory=$(sha256sum "${DIRECTORY}"/mise.toml | cut -d ' ' -f 1)
  if [ "${DIRECTORY}" != "aoc-main" ]; then
    cache_key_mise_aoc_main=$(sha256sum aoc-main/mise.toml | cut -d ' ' -f 1)
  fi
fi

cache_key="${cache_key_prefix}-${cache_key_mise_root}"
if [ -n "${cache_key_mise_directory}" ]; then
  cache_key="${cache_key}-${cache_key_mise_directory}"
  if [ -n "${cache_key_mise_aoc_main}" ]; then
    cache_key="${cache_key}-${cache_key_mise_aoc_main}"
  fi
fi

cache_key_root=""
if [ "${DIRECTORY}" != "." ]; then
  cache_key_root_prefix="mise-${MISE_VERSION}-${RUNNER_OS}"
  cache_key_root="${cache_key_root_prefix}-${cache_key_mise_root}"
fi

mise_data_dir="${RUNNER_TEMP}${SEP}aoc-mise-data"

# Isolate rustup used with mise.
rustup_home="${RUNNER_TEMP}${SEP}aoc-rustup-home"
# Isolate cargo used with mise.
cargo_home="${RUNNER_TEMP}${SEP}aoc-cargo-home"


# Set environment variables for remaining workflow
{
  echo "CARGO_HOME=$(echo "${cargo_home}" | tr -d '\n')"
  echo "MISE_DATA_DIR=$(echo "${mise_data_dir}" | tr -d '\n')"
  echo "RUSTUP_HOME=$(echo "${rustup_home}" | tr -d '\n')"
} >> "$GITHUB_ENV"

# Set outputs
{
  echo "cache-key=${cache_key}"
  echo "fail-on-cache-miss=${fail_on_cache_miss}"
  echo "mise-version=${MISE_VERSION}"
  echo "save-cache=${save_cache}"

  # Install directories
  echo "mise-install-directories<<ENDDIRS"
  echo "${DIRECTORY}"
  if [ "${DIRECTORY}" != "." ] && [ "${DIRECTORY}" != "aoc-main" ]; then
    echo "aoc-main"
  fi
  echo "ENDDIRS"

  # Cache restore keys
  echo "cache-restore-keys<<ENDKEYS"
  if [ "$CACHE_MODE" = "prepare" ]; then
    if [ -n "${cache_key_mise_directory}" ]; then
      if [ -n "${cache_key_mise_aoc_main}" ]; then
        echo "${cache_key_prefix}-${cache_key_mise_root}-${cache_key_mise_directory}-"
      fi
      echo "${cache_key_prefix}-${cache_key_mise_root}-"
    fi
    echo "${cache_key_prefix}-"
    if [ -n "${cache_key_root}" ]; then
      echo "${cache_key_root}"
    fi
  fi
  echo "ENDKEYS"

  # Mise cache paths
  echo "cache-paths<<ENDPATHS"
  echo "${cargo_home}"
  echo "${mise_data_dir}"
  echo "${rustup_home}"
  echo "ENDPATHS"
} >> "$GITHUB_OUTPUT"
