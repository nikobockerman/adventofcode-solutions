#!/bin/bash

set -euo pipefail

installDir="${RUNNER_TEMP}/aoc-libcxx-hardened"

echo "::group::Outputs from init"
{
  echo "installDir=${installDir}"
  echo "llvmVersion=${LLVM_VERSION}"
} | tee -a "${GITHUB_OUTPUT}"
echo "::endgroup::"
