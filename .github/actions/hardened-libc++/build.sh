#!/usr/bin/env bash

set -euo pipefail

# Determine compiler based on platform
clang=$(command -v clang)
clangpp=$(command -v clang++)

clangDir=$(dirname "${clang}")
clangppDir=$(dirname "${clangpp}")

if [[ "${clangDir}" != "${clangppDir}" ]]; then
  echo "::error::clang and clang++ are not in the same directory"
  exit 1
fi

echo "::group::Hardened libc++ build info"
echo "LLVM version of source files: ${LLVM_VERSION}"
echo "LLVM project directory: ${LLVM_PROJECT_DIR}"
echo "Compiler: ${clang}"
echo "Install directory: ${INSTALL_DIR}"
echo "::endgroup::"

# Create build directory
buildDir="${GITHUB_WORKSPACE}/build-libcxx-hardened"

# Clean install directory if it exists
rm -rf "${INSTALL_DIR}"

# Configure and build using the LLVM monorepo runtimes

echo "::group::Hardened libc++ cmake config"
cmake -G Ninja \
  -S "${LLVM_PROJECT_DIR}/runtimes" \
  -B "${buildDir}" \
  -DCMAKE_INSTALL_PREFIX="${INSTALL_DIR}" \
  -DCMAKE_C_COMPILER="${clang}" \
  -DCMAKE_CXX_COMPILER="${clangpp}" \
  -DLLVM_ENABLE_RUNTIMES="libcxx;libcxxabi;libunwind" \
  -DLIBCXX_ABI_DEFINES="_LIBCPP_ABI_BOUNDED_ITERATORS;_LIBCPP_ABI_BOUNDED_ITERATORS_IN_STRING;_LIBCPP_ABI_BOUNDED_ITERATORS_IN_VECTOR;_LIBCPP_ABI_BOUNDED_UNIQUE_PTR;_LIBCPP_ABI_BOUNDED_ITERATORS_IN_STD_ARRAY"
echo "::endgroup::"

# Build the runtimes
echo "::group::Hardened libc++ build"
ninja -C "${buildDir}" cxx cxxabi unwind
echo "::endgroup::"

# Install the runtimes
echo "::group::Hardened libc++ install"
ninja -C "${buildDir}" install-cxx install-cxxabi install-unwind
echo "::endgroup::"

echo "::group::Hardened libc++ install info"
echo "Hardened libc++ installed to: ${INSTALL_DIR}"
echo "Include directory: ${INSTALL_DIR}/include/c++/v1"
echo "Library directory: ${INSTALL_DIR}/lib"
echo "::endgroup::"
