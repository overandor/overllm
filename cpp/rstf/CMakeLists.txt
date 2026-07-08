cmake_minimum_required(VERSION 3.16)

project(overllm_rstf_cpp
  VERSION 0.1.0
  DESCRIPTION "OverLLM RSTF canonicalization and byte-cost benchmark package"
  LANGUAGES CXX
)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

add_library(overllm_rstf
  src/rstf.cpp
)

target_include_directories(overllm_rstf
  PUBLIC
    $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/include>
    $<INSTALL_INTERFACE:include>
)

target_compile_features(overllm_rstf PUBLIC cxx_std_17)

add_executable(overllm-rstf
  tools/rstf_cli.cpp
)

target_link_libraries(overllm-rstf PRIVATE overllm_rstf)

option(OVERLLM_RSTF_BUILD_TESTS "Build RSTF C++ tests" ON)

if(OVERLLM_RSTF_BUILD_TESTS)
  enable_testing()
  add_executable(overllm-rstf-tests
    tests/rstf_tests.cpp
  )
  target_link_libraries(overllm-rstf-tests PRIVATE overllm_rstf)
  add_test(NAME overllm-rstf-tests COMMAND overllm-rstf-tests)
endif()

install(TARGETS overllm_rstf overllm-rstf
  EXPORT overllm_rstfTargets
  ARCHIVE DESTINATION lib
  LIBRARY DESTINATION lib
  RUNTIME DESTINATION bin
)

install(DIRECTORY include/ DESTINATION include)
