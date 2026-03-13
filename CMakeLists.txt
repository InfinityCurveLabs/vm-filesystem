cmake_minimum_required( VERSION 3.27 )

set( CMAKE_CXX_STANDARD 20 )
set( CMAKE_CXX_COMPILER x86_64-w64-mingw32-g++ )
set( CMAKE_C_STANDARD   11 )
set( CMAKE_C_COMPILER   x86_64-w64-mingw32-gcc )

include_directories( include )

file( GLOB SRC_FILES
    src/*.cc
)

add_library( VmFileSystem ${SRC_FILES} )
