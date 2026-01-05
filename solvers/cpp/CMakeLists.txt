cmake_minimum_required(VERSION 3.24)

project(adventofcode VERSION 0.1.0 LANGUAGES C CXX)

set(CMAKE_CXX_STANDARD 23)

find_package(GTest CONFIG REQUIRED)
find_package(spdlog CONFIG REQUIRED)

enable_testing()
include(GoogleTest)

add_subdirectory(src)
