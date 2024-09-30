# create an executable
set (CMAKE_RUNTIME_OUTPUT_DIRECTORY ${TELEOP_BINARY_DIR}/panda_teleop)
ADD_EXECUTABLE (simviz_panda simviz.cpp ${TELEOP_COMMON_SOURCE})
ADD_EXECUTABLE (controller_panda controller.cpp ${TELEOP_COMMON_SOURCE})
ADD_EXECUTABLE (controller_panda_relative controller_relative.cpp ${TELEOP_COMMON_SOURCE})

# and link the library against the executable
TARGET_LINK_LIBRARIES (simviz_panda ${TELEOP_COMMON_LIBRARIES})
TARGET_LINK_LIBRARIES (controller_panda ${TELEOP_COMMON_LIBRARIES})
TARGET_LINK_LIBRARIES (controller_panda_relative ${TELEOP_COMMON_LIBRARIES})

# export resources such as model files.
# NOTE: this requires an install build
SET(APP_RESOURCE_DIR ${CMAKE_RUNTIME_OUTPUT_DIRECTORY}/resources)
FILE(MAKE_DIRECTORY ${APP_RESOURCE_DIR})
FILE(COPY world.urdf panda_arm.urdf DESTINATION ${APP_RESOURCE_DIR})

