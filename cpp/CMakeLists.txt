cmake_minimum_required(VERSION 3.10)
project(EdgeAIProcessor)

# Set C++ standard
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Find required packages
find_package(OpenCV REQUIRED)
find_package(PkgConfig REQUIRED)

# Find additional libraries
pkg_check_modules(ALSA REQUIRED alsa)

# Include directories
include_directories(${OpenCV_INCLUDE_DIRS})
include_directories(${ALSA_INCLUDE_DIRS})

# Compiler flags
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -Wall -Wextra -O3")

# Create executable
add_executable(edge_processor
    edge_processor.cpp
)

# Link libraries
target_link_libraries(edge_processor
    ${OpenCV_LIBS}
    ${ALSA_LIBRARIES}
    pthread
)

# Install target
install(TARGETS edge_processor DESTINATION bin)

# Optional: Create shared library for Python integration
add_library(edge_processor_lib SHARED
    edge_processor.cpp
)

target_link_libraries(edge_processor_lib
    ${OpenCV_LIBS}
    ${ALSA_LIBRARIES}
    pthread
)

# Set library properties
set_target_properties(edge_processor_lib PROPERTIES
    PREFIX ""
    SUFFIX ".so"
)

# Install library
install(TARGETS edge_processor_lib DESTINATION lib)

# Create Python wrapper (optional)
if(PYTHON_EXECUTABLE)
    find_package(pybind11 QUIET)
    if(pybind11_FOUND)
        pybind11_add_module(edge_processor_py
            python_wrapper.cpp
            edge_processor.cpp
        )
        
        target_link_libraries(edge_processor_py PRIVATE
            ${OpenCV_LIBS}
            ${ALSA_LIBRARIES}
            pthread
        )
        
        install(TARGETS edge_processor_py DESTINATION lib/python)
    endif()
endif()

# Print configuration
message(STATUS "OpenCV version: ${OpenCV_VERSION}")
message(STATUS "OpenCV libraries: ${OpenCV_LIBS}")
message(STATUS "Build type: ${CMAKE_BUILD_TYPE}")
