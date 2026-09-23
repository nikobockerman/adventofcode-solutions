#!/bin/bash

set -euo pipefail

case "${RUNNER_OS}" in
"macOS")
  version=$(sw_vers -productVersion)
  case "${version}" in
  "${RUNNER_MACOS_VERSION}".*) ;;
  *)
    echo "Unexpected macOS version: ${version}"
    exit 1
    ;;
  esac
  ;;

"Linux")
  version=$(</etc/os-release grep "VERSION_ID=" | cut -d = -f 2 | tr -d '"')
  case "${version}" in
  "${RUNNER_UBUNTU_VERSION}") ;;
  *)
    echo "Unexpected Linux version: ${version}"
    exit 1
    ;;
  esac
  ;;
*)
  echo "Unexpected runner OS: ${RUNNER_OS}"
  exit 1
  ;;
esac
