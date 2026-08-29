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
  if [[ -n "${DIRECTORY}" ]]; then
    echo "::error::Directory must be empty for prepare mode"
    exit 1
  fi

  DIRECTORY="."
fi

if [[ -z "${DIRECTORY}" ]]; then
  echo "::error::Empty DIRECTORY is not supported"
  exit 1
elif [[ ! -d "${DIRECTORY}" ]]; then
  echo "::error::Directory does not exist: ${DIRECTORY}"
  exit 1
elif [[ ! -f "${DIRECTORY}/mise.toml" ]]; then
  echo "::error::Directory does not contain mise.toml: ${DIRECTORY}"
  exit 1
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

install_directories="."
if [[ "${CACHE_MODE}" = "prepare" ]]; then
  install_directories="${install_directories} aoc-main"
  # Use of mise tools in CI on different OSes for solvers:
  #   - C++: macOS and Ubuntu
  #   - Python: Ubuntu
  #   - Rust: macOS and Ubuntu
  install_directories="${install_directories} solvers/cpp"
  if [[ "${RUNNER_OS}" = "Linux" ]]; then
    install_directories="${install_directories} solvers/python"
  fi
  install_directories="${install_directories} solvers/rust"
elif [[ "${DIRECTORY}" != "." ]]; then
  install_directories="${install_directories} aoc-main ${DIRECTORY}"
fi

deduplicated=""
for directory in ${install_directories}; do
  case " ${deduplicated} " in
  *" ${directory} "*) continue ;;
  *) ;;
  esac
  deduplicated="${deduplicated} ${directory}"
done
install_directories=${deduplicated# }

echo "::group::Outputs from init"
{
  echo "mise-version=${MISE_VERSION}"

  # Install directories
  echo "mise-install-directories<<ENDDIRS"
  for directory in ${install_directories}; do
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
