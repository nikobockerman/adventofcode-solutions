#!/usr/bin/env bash

set -euo pipefail

echo "::group::Environment changes for rest of workflow"
{
  echo "HOMEBREW_NO_AUTO_UPDATE=1"
} | tee -a "${GITHUB_ENV}"
echo "::endgroup::"
