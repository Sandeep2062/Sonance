cmake_minimum_required(VERSION 3.14)
project(sonance LANGUAGES CXX)

set(BINARY_NAME "Sonance")

cmake_policy(SET CMP0063 NEW)

set(CMAKE_INSTALL_RPATH "$ORIGIN/lib")

# Configure build options
get_property(IS_MULTICONFIG GLOBAL PROPERTY GENERATOR_IS_MULTI_CONFIG)
if(IS_MULTICONFIG)
  set(CMAKE_CONFIGURATION_TYPES "Debug;Profile;Release"
    CACHE STRING "" FORCE)
else()
  if(NOT CMAKE_BUILD_TYPE AND NOT CMAKE_CONFIGURATION_TYPES)
    set(CMAKE_BUILD_TYPE "Debug" CACHE STRING
      "Choose the type of build, options are: Debug, Profile, Release."
      FORCE)
  endif()
endif()

# Application build configuration
add_definitions(-DUNICODE -D_UNICODE)
add_definitions(-DFLUTTER_VERSION="4.0.0")

# Standard Flutter runner includes
include(flutter/generated_plugins.cmake OPTIONAL)
