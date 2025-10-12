#!/usr/bin/env bash

set -euo pipefail

echo "::group::Upgrade packages"
brew upgrade
echo "::endgroup::"

echo "::group::Install needed tools"
brew install "gcc@${GCC_MAJOR_VERSION}"
brew install "llvm@${LLVM_MAJOR_VERSION}"
echo "::endgroup::"

echo "::group::Run brew cleanup"
brew cleanup --scrub --prune=all
echo "::endgroup::"
