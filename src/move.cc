#include <common.h>
#include <cstdint>
#include <minicrt.h>
#include <firebeam.h>

extern "C" auto entry(
    const char*  argv,
    const size_t argc
) -> uint32_t {
    auto status = uint32_t { 0 };
    auto src    = _buffer<wchar_t>();
    auto dst    = _buffer<wchar_t>();
    auto parser = firebeam::parser( argv, argc );

    src.buffer = parser.get_wstring( &src.length );
    dst.buffer = parser.get_wstring( &dst.length );

    if ( !MoveFileW( src.buffer, dst.buffer ) ) {
        status = GetLastError() | KN_FACILITY_WIN32_BIT;
    }

    return status;
}
