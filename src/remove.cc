#include <windows.h>
#include <common.h>
#include <cstdint>
#include <minicrt.h>
#include <firebeam.h>

extern "C" auto entry(
    const char*  argv,
    const size_t argc
) -> uint32_t {
    auto status     = uint32_t { 0 };
    auto path       = _buffer<wchar_t>();
    auto attributes = ULONG { 0 };

    //
    // parse the path to list
    path.buffer = firebeam::parser( argv, argc )
        .get_wstring( &path.length );

    // 
    // delete the path based on when ever it is a file or directory 
    if ( ( attributes = GetFileAttributesW( path.buffer ) ) != INVALID_FILE_ATTRIBUTES ) {
        if ( attributes & FILE_ATTRIBUTE_DIRECTORY ) {
            if ( !RemoveDirectoryW( path.buffer ) ) {
                status = GetLastError() | KN_FACILITY_WIN32_BIT;
            }
        } else {
            if ( !DeleteFileW( path.buffer ) ) {
                status = GetLastError() | KN_FACILITY_WIN32_BIT;
            }
        }
    } else {
        status = GetLastError() | KN_FACILITY_WIN32_BIT;
    }

    //
    // send back when ever it was a file or directory we just deleted
    firebeam::packet::add_u08( attributes & FILE_ATTRIBUTE_DIRECTORY );

    return status;
}
