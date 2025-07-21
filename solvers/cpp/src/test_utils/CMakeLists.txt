add_library(test_utils STATIC test_utils.cpp)
target_include_directories(test_utils PUBLIC ${CMAKE_CURRENT_LIST_DIR})
target_link_libraries(test_utils PUBLIC lib spdlog::spdlog GTest::gtest)
