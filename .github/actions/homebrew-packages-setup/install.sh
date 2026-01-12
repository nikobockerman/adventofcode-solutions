#!/usr/bin/env bash

set -euo pipefail

if [[ -z "${TOOLS_TO_INSTALL}" ]]; then
  echo "::error::TOOLS_TO_INSTALL is empty"
  exit 1
fi

skipInstalls=false
if [[ "${INPUT_CACHE_MODE}" == "prepare" && "${GITHUB_EVENT_NAME}" == "pull_request" && "${MATCHED_RESTORE_KEY}" =~ ^"${RESTORE_KEY_PREFIX}" ]]; then
  echo "Prepare mode for PR. Cache restored with a prefix match. Skipping all installs."
  skipInstalls=true
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
  echo -n " Calculated downloads hash: ${initialDownloadsHash}"
  echo
  exit 1
fi

if [[ "${skipInstalls}" == "false" ]]; then
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

  saveCache=false
  if [[ "${INPUT_CACHE_MODE}" == "prepare" ]]; then
    if [[ "${downloadsChanged}" = "true" ]] || ! [[ "${MATCHED_RESTORE_KEY}" =~ ^"${RESTORE_KEY_PREFIX}" ]]; then
      saveCache=true
    fi
  fi
else
  # Installs skipped for PR.
  downloadsHash=${initialDownloadsHash}
  saveCache=false
fi

echo "::group::Outputs from install"
{
  echo "downloads-hash=${downloadsHash}"
  echo "save-cache=${saveCache}"
} | tee -a "${GITHUB_OUTPUT}"
echo "::endgroup::"
