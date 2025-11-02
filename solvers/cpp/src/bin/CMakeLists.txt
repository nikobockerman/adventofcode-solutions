function(getBinaries outVar)
  file(GLOB sourceFiles *.cpp)
  set(binaries "")
  foreach(sourceFile ${sourceFiles})
    cmake_path(GET sourceFile EXTENSION sourceFileExtension)
    if(sourceFileExtension STREQUAL ".test.cpp")
      continue()
    endif()
    cmake_path(GET sourceFile FILENAME sourceFileName)
    if(sourceFileName STREQUAL "shared_main.cpp")
      continue()
    endif()

    cmake_path(GET sourceFile STEM binary)
    list(APPEND binaries ${binary})
  endforeach()
  set(${outVar} ${binaries} PARENT_SCOPE)
endfunction()

getBinaries(binaries)
message(STATUS "Binaries: ${binaries}")

add_library(shared_main OBJECT shared_main.cpp)
target_link_libraries(shared_main PRIVATE lib fmt::fmt spdlog::spdlog)

foreach(binary ${binaries})
  add_library(${binary}.lib STATIC ${binary}.cpp)
  target_link_libraries(
      ${binary}.lib
      PRIVATE lib fmt::fmt spdlog::spdlog
  )

  add_executable(${binary})
  set_target_properties(${binary} PROPERTIES
      RUNTIME_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}
  )
  target_link_libraries(${binary} PRIVATE shared_main ${binary}.lib)

  if(EXISTS ${CMAKE_CURRENT_LIST_DIR}/${binary}.test.cpp)
    add_executable(${binary}.test ${binary}.test.cpp)
    gtest_discover_tests(${binary}.test)
    target_link_libraries(${binary}.test PRIVATE ${binary}.lib test_utils GTest::gtest_main)
  endif()
endforeach()
