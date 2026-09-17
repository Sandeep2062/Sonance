cmake_minimum_required(VERSION 3.10)
project(sonance LANGUAGES CXX)

set(BINARY_NAME "sonance")

cmake_policy(SET CMP0063 NEW)

set(CMAKE_INSTALL_RPATH "$ORIGIN/lib")

# Apply Flutter build settings
add_definitions(-DFLUTTER_VERSION="2.1.0")

# Standard Linux GTK runner settings
include(flutter/generated_plugins.cmake OPTIONAL)
