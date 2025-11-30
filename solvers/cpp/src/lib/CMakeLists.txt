add_library(lib INTERFACE)
target_include_directories(lib INTERFACE ${CMAKE_CURRENT_LIST_DIR})

add_executable(lib-tests my_stride_view.test.cpp)
target_link_libraries(lib-tests PRIVATE test_utils GTest::gtest_main)
gtest_discover_tests(lib-tests)
