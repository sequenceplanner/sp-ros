cmake_minimum_required(VERSION 3.5)
project(sp_messages)


# Default to C++14
if(NOT CMAKE_CXX_STANDARD)
  set(CMAKE_CXX_STANDARD 14)
endif()

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

# find dependencies
find_package(ament_cmake REQUIRED)
find_package(rosidl_default_generators REQUIRED)

rosidl_generate_interfaces(${PROJECT_NAME}
  "action/Json.action"
  "srv/Json.srv"
  "msg/RegisterResource.msg"
  "msg/Resources.msg"
)

ament_export_dependencies(rosidl_default_runtime)
ament_package()
