#!/usr/bin/env bash

set -euo pipefail

if [[ -z "${TOOLS_TO_INSTALL}" ]]; then
  echo "::error::TOOLS_TO_INSTALL is empty"
  exit 1
fi

calculateDownloadsHash() {
  brewCache=$(brew --cache)
  brewDownloads=${brewCache}/downloads
  downloads=$(ls "${brewDownloads}/" 2>/dev/null || true)
  downloadsHash=$(echo "${downloads}" | sha256sum | cut -d ' ' -f 1)
  echo "${downloadsHash}"
}

initialDownloadsHash=$(calculateDownloadsHash)
if [[ "${CACHE_HIT}" == "true" && "${INPUT_DOWNLOADS_HASH_FROM_PREPARE}" != "${initialDownloadsHash}" ]]; then
  echo -n "::error::Cache restored with exact key match but calculated downloads hash doesn't match"
  echo -n " 'downloads-hash-from-prepare' input value. This should never happen."
  echo -n " Calculated downloads hash: ${downloadsHash}"
  echo
  exit 1
fi

for tool in ${TOOLS_TO_INSTALL}; do
  echo "::group::Install ${tool}"
  brew install "${tool}"
  echo "::endgroup::"
done

echo "::group::brew cleanup"
brew cleanup --scrub
echo "::endgroup::"

echo "::group::Check changes to downloaded contents"
downloadsHash=$(calculateDownloadsHash)
echo "downloadsHash=${downloadsHash}"
if [[ "${initialDownloadsHash}" = "${downloadsHash}" ]]; then
  downloadsChanged=false
  echo "Downloads were not changed by install/upgrade"
else
  downloadsChanged=true
  echo "Downloads were changed during install/upgrade"
fi
echo "::endgroup::"

if [[ "${INPUT_CACHE_MODE}" = "prepare" && "${downloadsChanged}" = "true" ]]; then
  saveCache=true
else
  saveCache=false
fi

echo "::group::Outputs from install"
{
  echo "downloads-hash=${downloadsHash}"
  echo "save-cache=${saveCache}"
} | tee -a "${GITHUB_OUTPUT}"
echo "::endgroup::"
