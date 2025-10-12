#!/usr/bin/env bash

set -euo pipefail

echo "::group::Check changes to downloaded contents"
if [[ "${INPUT_DOWNLOADS_HASH_TO_USE}" == "${DOWNLOADS_HASH}" ]]; then
  downloadsChanged=false
  echo "Downloads were not changed by install/upgrade"
else
  downloadsChanged=true
  echo "Downloads were changed during install/upgrade"
fi
echo "::endgroup::"

if [[ "${INPUT_CACHE_MODE}" == "prepare" && "${downloadsChanged}" == "true" ]]; then
  saveCache=true
else
  saveCache=false
fi

echo "::group::Outputs from checks-after-install"
{
  echo "downloads-hash=${DOWNLOADS_HASH}"
  echo "save-cache=${saveCache}"
} | tee -a "${GITHUB_OUTPUT}"
echo "::endgroup::"
