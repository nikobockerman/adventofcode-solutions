#!/bin/bash

set -euo pipefail

# Validate inputs
if [[ -z "${GITHUB_TOKEN:-}" ]]; then
  echo "::error::github.token context variable must be available"
  exit 1
fi

case "${CACHE_MODE}" in
prepare | use) ;;
*)
  echo "::error::Unknown cache mode: ${CACHE_MODE}"
  exit 1
  ;;
esac

if [[ "${CACHE_MODE}" = "prepare" ]]; then
  if [[ -n "${DIRECTORIES}" ]]; then
    echo "::error::Directories must be empty for prepare mode"
    exit 1
  fi

  if [[ -n "${PATH_DIRECTORY}" ]]; then
    echo "::error::Path directory must be empty for prepare mode"
    exit 1
  fi

  # Use of mise tools in CI on different OSes for solvers:
  #   - C++: macOS and Ubuntu
  #   - Python: Ubuntu
  #   - Rust: macOS and Ubuntu
  DIRECTORIES=". aoc-main solvers/cpp solvers/rust"
  if [[ "${RUNNER_OS}" = "Linux" ]]; then
    DIRECTORIES="${DIRECTORIES} solvers/python"
  fi
fi

if [[ -z "${DIRECTORIES}" ]]; then
  echo "::error::Empty DIRECTORIES is not supported"
  exit 1
fi

deduplicated=""
for directory in ${DIRECTORIES}; do
  case " ${deduplicated} " in
  *" ${directory} "*) continue ;;
  *) ;;
  esac
  deduplicated="${deduplicated} ${directory}"
done
DIRECTORIES=${deduplicated# }

for directory in ${DIRECTORIES}; do
  if [[ ! -d "${directory}" ]]; then
    echo "::error::Directory does not exist: ${directory}"
    exit 1
  elif [[ ! -f "${directory}/mise.toml" ]]; then
    echo "::error::Directory does not contain mise.toml: ${directory}"
    exit 1
  fi
done

if [[ "${CACHE_MODE}" = "use" ]]; then
  if [[ -z "${PATH_DIRECTORY}" ]]; then
    echo "::error::Empty PATH_DIRECTORY is not supported"
    exit 1
  fi

  path_directory_listed=false
  for directory in ${DIRECTORIES}; do
    if [[ "${directory}" = "${PATH_DIRECTORY}" ]]; then
      path_directory_listed=true
    fi
  done
  if [[ "${path_directory_listed}" != true ]]; then
    echo "::error::Path directory is not one of the directories: ${PATH_DIRECTORY}"
    exit 1
  fi
fi

mise_ceiling_path=$(dirname "${GITHUB_WORKSPACE}")
mise_data_dir="${RUNNER_TEMP}/aoc-mise-data"

# Isolate rustup used with mise.
rustup_home="${RUNNER_TEMP}/aoc-rustup-home"
# Isolate cargo used with mise.
cargo_home="${RUNNER_TEMP}/aoc-cargo-home"

echo "::group::Environment variable changes"
{
  echo -n "CARGO_HOME="
  echo "${cargo_home}" | tr -d '\n'
  echo

  echo -n "MISE_DATA_DIR="
  echo "${mise_data_dir}" | tr -d '\n'
  echo

  echo -n "RUSTUP_HOME="
  echo "${rustup_home}" | tr -d '\n'
  echo

  echo -n "MISE_CEILING_PATHS="
  echo "${mise_ceiling_path}" | tr -d '\n'
  echo

  echo "MISE_DEBUG=1"
  echo "MISE_TASK_SHOW_FULL_CMD=true"
  echo "RUST_LOG=uv=debug"
} | tee -a "${GITHUB_ENV}"
echo "::endgroup::"

echo "::group::Outputs from init"
{
  echo "mise-version=${MISE_VERSION}"

  # Install directories
  echo "mise-install-directories<<ENDDIRS"
  for directory in ${DIRECTORIES}; do
    echo "${directory}"
  done
  echo "ENDDIRS"

  # Mise cache paths
  echo "cache-paths<<ENDPATHS"
  echo "${cargo_home}"
  echo "${mise_data_dir}"
  echo "${rustup_home}"
  echo "ENDPATHS"
} | tee -a "${GITHUB_OUTPUT}"
echo "::endgroup::"
