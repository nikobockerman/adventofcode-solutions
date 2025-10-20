#!/usr/bin/env bash

set -euo pipefail

case ${INPUT_CACHE_MODE} in
  prepare)
    if [[ -n ${INPUT_DOWNLOADS_HASH_FROM_PREPARE} ]]; then
      echo "::error::'downloads-hash-from-prepare' input must be empty in 'prepare' mode"
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
