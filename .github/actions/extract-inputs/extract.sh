#!/usr/bin/env bash

set -euo pipefail

if [[ -z "${ENCRYPTION_KEY}" ]]; then
  echo "::error::ENCRYPTION_KEY is empty"
  exit 1
fi

echo "::group::Extract inputs"
mise run inputs:extract
echo "::endgroup::"
