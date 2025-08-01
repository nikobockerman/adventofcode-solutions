add_library(lib INTERFACE)
target_include_directories(lib INTERFACE ${CMAKE_CURRENT_LIST_DIR})
target_link_libraries(lib INTERFACE fmt::fmt)
