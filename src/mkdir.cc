#include <common.h>
#include <cstdint>
#include <minicrt.h>
#include <firebeam.h>

extern "C" auto entry(
    const char*  argv,
    const size_t argc
) -> uint32_t {
    auto path   = _buffer<wchar_t>();
    auto status = uint32_t { 0 };
    
    //
    // parse the path to list
    path.buffer = firebeam::parser( argv, argc )
        .get_wstring( &path.length );

    if ( !CreateDirectoryW( path.buffer, nullptr ) ) {
        status = GetLastError() | KN_FACILITY_WIN32_BIT;
    }

    return status;
}
