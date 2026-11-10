cmake_minimum_required(VERSION 3.22)
project(native_v4_store LANGUAGES C CXX)
set(VILLA_SOURCE_ROOT "" CACHE PATH "Existing checkout of the documented Villa pin")
if(NOT EXISTS "${VILLA_SOURCE_ROOT}/vc_object_store/CMakeLists.txt")
  message(FATAL_ERROR "Set VILLA_SOURCE_ROOT to the pinned Villa source checkout")
endif()
find_package(nlohmann_json CONFIG REQUIRED)
foreach(option VC_OBJECT_STORE_BUILD_ADAPTERS VC_OBJECT_STORE_BUILD_LINKING
               VC_OBJECT_STORE_BUILD_PYTHON VC_OBJECT_STORE_BUILD_SERVER
               VC_OBJECT_STORE_BUILD_TOOLS VC_OBJECT_STORE_BUILD_TESTS
               VC_READER_BUILD_PYTHON VC_READER_BUILD_READER VC_READER_ENABLE_CUDA
               VC_READER_BUILD_NATIVE_TESTS VC_READER_BUILD_EXAMPLES
               VC_READER_BUILD_THINNING_BENCHMARK)
  set(${option} OFF CACHE BOOL "Minimal native typed geometry target" FORCE)
endforeach()
add_subdirectory("${VILLA_SOURCE_ROOT}/vc_object_store" native)
add_executable(native_v4_store native_v4_store.cpp)
target_compile_features(native_v4_store PRIVATE cxx_std_20)
target_link_libraries(native_v4_store PRIVATE vc_object_store::vc_objects vc_geometry nlohmann_json::nlohmann_json)
