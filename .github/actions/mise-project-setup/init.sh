#!/bin/bash

set -euo pipefail

# TODO: Verify whether SEP is needed or not
if [ "$RUNNER_OS" = "Windows" ]; then
  SEP="\\"
else
  SEP="/"
fi


case "$CACHE_MODE" in
  prepare|use)
    ;;
  *)
    echo "::error::Unknown cache mode: $CACHE_MODE"
    exit 1
    ;;
esac

if [ "$CACHE_MODE" = "prepare" ]; then
  if [ -n "${DIRECTORY}" ]; then
    echo "::error::Directory must be empty for prepare mode"
    exit 1
  fi

  DIRECTORY="."
fi

if [ -z "${DIRECTORY}" ]; then
  echo "::error::Empty DIRECTORY is not supported"
  exit 1
elif [ ! -d "$DIRECTORY" ]; then
  echo "::error::Directory does not exist: $DIRECTORY"
  exit 1
elif [ ! -f "$DIRECTORY/mise.toml" ]; then
  echo "::error::Directory does not contain mise.toml: $DIRECTORY"
  exit 1
fi

mise_data_dir="${RUNNER_TEMP}${SEP}aoc-mise-data"

# Isolate rustup used with mise.
rustup_home="${RUNNER_TEMP}${SEP}aoc-rustup-home"
# Isolate cargo used with mise.
cargo_home="${RUNNER_TEMP}${SEP}aoc-cargo-home"


echo "::group::Environment variable changes"
{
  echo "CARGO_HOME=$(echo "${cargo_home}" | tr -d '\n')"
  echo "MISE_DATA_DIR=$(echo "${mise_data_dir}" | tr -d '\n')"
  echo "RUSTUP_HOME=$(echo "${rustup_home}" | tr -d '\n')"
} | tee -a "$GITHUB_ENV"
echo "::endgroup::"

echo "::group::Outputs from init"
{
  echo "mise-version=${MISE_VERSION}"

  # Install directories
  echo "mise-install-directories<<ENDDIRS"
  echo "."
  if [ "$CACHE_MODE" = "prepare" ]; then
    echo "aoc-main"
    # Use of mise tools in CI on different OSes for solvers:
    #   - C++: Ubuntu
    #   - Python: Ubuntu
    #   - Rust: Ubuntu, Windows and macOS
    if [ "$RUNNER_OS" = "Linux" ]; then
      echo solvers/cpp
      echo solvers/python
    fi
    echo solvers/rust
  elif [ "$DIRECTORY" != "."  ]; then
    if [ "$DIRECTORY" != "aoc-main" ]; then
      echo "aoc-main"
    fi
    echo "${DIRECTORY}"
  fi
  echo "ENDDIRS"

  # Mise cache paths
  echo "cache-paths<<ENDPATHS"
  echo "${cargo_home}"
  echo "${mise_data_dir}"
  echo "${rustup_home}"
  echo "ENDPATHS"
} | tee -a "$GITHUB_OUTPUT"
echo "::endgroup::"
