#!/bin/bash

set -euo pipefail

# Validate inputs
if [[ -z "${GCC_MAJOR_VERSION}" ]]; then
  echo "::error::GCC_MAJOR_VERSION is not set"
  exit 1
fi
if [[ -z "${LLVM_MAJOR_VERSION}" ]]; then
  echo "::error::LLVM_MAJOR_VERSION is not set"
  exit 1
fi

case "${INPUT_CACHE_MODE}" in
  prepare)
    if [[ -n "${INPUT_PACKAGES_HASH_TO_USE}" ]]; then
      echo "::error::packages-hash-to-use input must be empty in 'prepare' mode"
      exit 1
    fi
    ;;
  use)
    ;;
  *)
    echo "::error::Unknown cache mode: ${INPUT_CACHE_MODE}"
    exit 1
    ;;
esac

# Prepare output values
brewCache=$(brew --cache)
brewPrefix=$(brew --prefix)
cachePath="${brewCache}/downloads"

cacheKeyBase="homebrew-${RUNNER_OS}"
cacheKeyPrefix="${cacheKeyBase}-gcc${GCC_MAJOR_VERSION}-llvm${LLVM_MAJOR_VERSION}"
cacheRestoreKey="${cacheKeyPrefix}"
if [[ -n "${INPUT_PACKAGES_HASH_TO_USE}" ]]; then
  cacheRestoreKey="${cacheRestoreKey}-${INPUT_PACKAGES_HASH_TO_USE}"
fi

echo "::group::Environment variable changes"
{
  echo -n "HOMEBREW_PREFIX="
  echo "${brewPrefix}" | tr -d '\n'
  echo
} | tee -a "${GITHUB_ENV}"
echo "::endgroup::"

echo "::group::Outputs from init"
{
  echo "cache-key-prefix=${cacheKeyPrefix}"
  echo "cache-path=${cachePath}"
  echo "gcc-major-version=${GCC_MAJOR_VERSION}"
  echo "llvm-major-version=${LLVM_MAJOR_VERSION}"

  # Cache keys
  echo "cache-restore-key=${cacheRestoreKey}"
  echo "cache-restore-other-keys<<ENDKEYS"
  echo "${cacheKeyPrefix}-"
  echo "${cacheKeyBase}-"
  echo "ENDKEYS"
} | tee -a "${GITHUB_OUTPUT}"
echo "::endgroup::"
