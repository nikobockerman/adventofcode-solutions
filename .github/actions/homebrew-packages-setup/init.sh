#!/usr/bin/env bash

set -euo pipefail

# Ensure brew is in path. Needed on Ubuntu runner
if ! command -v brew &>/dev/null; then
  linuxHomebrewBin="/home/linuxbrew/.linuxbrew/bin"
  PATH="${linuxHomebrewBin}:${PATH}"

  if ! command -v brew &>/dev/null; then
    echo "Could not find 'brew' command in PATH or standard locations."
    exit 1
  fi

  echo "::group::Prepend homebrew to PATH"
  {
    echo "${linuxHomebrewBin}"
  } | tee -a "${GITHUB_PATH}"
  echo "::endgroup::"
fi


# Values for cache key and restore-keys
cacheKeyBase="homebrew-${RUNNER_OS}"
cacheKeyPrefix="${cacheKeyBase}-gcc${GCC_MAJOR_VERSION}-llvm${LLVM_MAJOR_VERSION}"
cacheKeyForRestore="${cacheKeyPrefix}"
if [[ -n "${INPUT_DOWNLOADS_HASH_FROM_PREPARE}" ]]; then
  cacheKeyForRestore="${cacheKeyForRestore}-${INPUT_DOWNLOADS_HASH_FROM_PREPARE}"
fi

# Other values
brewCache=$(brew --cache)
cachePath="${brewCache}/downloads"

echo "::group::Environment variable changes"
{
  echo "HOMEBREW_NO_AUTO_UPDATE=1"
} | tee -a "${GITHUB_ENV}"
echo "::endgroup::"

echo "::group::Outputs from init"
{
  echo "cache-key-prefix=${cacheKeyPrefix}"
  echo "cache-path=${cachePath}"

  # Cache keys
  echo "cache-key-for-restore=${cacheKeyForRestore}"
  echo "cache-restore-keys<<ENDKEYS"
  echo "${cacheKeyPrefix}-"
  echo "${cacheKeyBase}-"
  echo "ENDKEYS"

  # Tools to install
  echo "tools-to-install<<ENDTOOLS"
  if [[ "${RUNNER_OS}" = "Linux" ]]; then
    echo "binutils"
  fi
  echo "gcc@${GCC_MAJOR_VERSION}"
  echo "llvm@${LLVM_MAJOR_VERSION}"
  echo "ENDTOOLS"
} | tee -a "${GITHUB_OUTPUT}"
echo "::endgroup::"
