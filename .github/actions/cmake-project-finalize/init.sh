#!/bin/bash

set -euo pipefail

# Validate required environment variables
if [[ -z "${CONAN_HOME}" ]]; then
  echo "::error::CONAN_HOME is not set"
  exit 1
fi

pushd solvers/cpp

echo "::group::List existing recipes and binaries"
conan list --cache '*/*#*:*' -f=compact
echo "::endgroup::"

# Remove all recipes that have not been used in the last 1 hour
# (with their binaries). In practice, this will remove all recipes that have
# not been used in the last build.
echo "::group::Remove unused recipes and binaries"
conan remove "*" --lru=1h --confirm
echo "::endgroup::"

# Remove all binaries (but not recipes) not used in the last 1 hour
echo "::group::Remove unused binaries"
conan remove "*:*" --lru=1h --confirm
echo "::endgroup::"

# Remove non-critical folders from the cache for the remaining recipes
echo "::group::Remove non-critical folders from the cache"
conan cache clean
echo "::endgroup::"

# Generate file about existing recipes and binaries

echo "::group::List remaining recipes and binaries"
conan list --cache '*/*#*:*' -f=compact | tee "${RUNNER_TEMP}/existing_packages.txt"
echo "::endgroup::"

packagesHash=$(sha256sum "${RUNNER_TEMP}/existing_packages.txt" | cut -d ' ' -f 1)

popd

matchedKeyPackagesHash=${CONAN_CACHE_MATCHED_KEY##*-}

if [[ "${packagesHash}" != "${matchedKeyPackagesHash}" ]]; then
  saveCache=true
else
  saveCache=false
fi


echo "::group::Outputs from init"
{
  echo "conan-cache-path=${CONAN_HOME}/p"
  echo "packages-hash=${packagesHash}"
  echo "save-cache=${saveCache}"
} | tee -a "${GITHUB_OUTPUT}"
echo "::endgroup::"
