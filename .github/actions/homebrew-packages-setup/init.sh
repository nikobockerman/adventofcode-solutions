#!/usr/bin/env bash

set -euo pipefail

# Isolate all 'brew' calls in this script from auto-update so the captured
# Homebrew commit reflects the runner image exactly. The same value is also
# written to GITHUB_ENV below for subsequent action steps.
export HOMEBREW_NO_AUTO_UPDATE=1

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

toolsToInstall=(
  "gcc@${GCC_MAJOR_VERSION}"
  "llvm@${LLVM_MAJOR_VERSION}"
)
if [[ "${RUNNER_OS}" == "Linux" ]]; then
  toolsToInstall+=("binutils")
fi
toolsToInstallLines=$(printf '%s\n' "${toolsToInstall[@]}")
toolsToInstallHash=$(echo "${toolsToInstallLines}" | sha256sum | cut -d ' ' -f 1)
toolsToInstallCacheKeyPart=$(
  IFS=-
  echo "${toolsToInstall[*]}"
)

# Scope the cache key to the Homebrew commit currently on the runner.
# Bottles downloaded under one Homebrew version may fail to install under
# another, so a runner-image Homebrew bump must invalidate the cache.
brewRepository=$(brew --repository)
brewCommit=$(git -C "${brewRepository}" rev-parse --short=12 HEAD)
brewCommitCacheKeyPart="brew${brewCommit}"

# Values for cache key and restore-keys
cacheKeyBase="homebrew-${RUNNER_OS}"
cacheKeyPrefix="${cacheKeyBase}-${brewCommitCacheKeyPart}-${toolsToInstallCacheKeyPart}-${toolsToInstallHash}"
cacheKeyForRestore="${cacheKeyPrefix}"
if [[ -n "${INPUT_DOWNLOADS_HASH_FROM_PREPARE}" ]]; then
  cacheKeyForRestore="${cacheKeyForRestore}-${INPUT_DOWNLOADS_HASH_FROM_PREPARE}"
fi

# Other values
brewCache=$(brew --cache)
cachePath="${brewCache}/downloads"

echo "::group::Environment variable changes"
{
  echo "HOMEBREW_DISPLAY_INSTALL_TIMES=1"
  echo "HOMEBREW_NO_AUTO_UPDATE=1"

  # Set GCC and LLVM major versions
  echo "GCC_MAJOR_VERSION=${GCC_MAJOR_VERSION}"
  echo "LLVM_MAJOR_VERSION=${LLVM_MAJOR_VERSION}"
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
  echo "ENDKEYS"

  # Tools to install
  echo "tools-to-install<<ENDTOOLS"
  for tool in "${toolsToInstall[@]}"; do
    echo "${tool}"
  done
  echo "ENDTOOLS"
} | tee -a "${GITHUB_OUTPUT}"
echo "::endgroup::"
