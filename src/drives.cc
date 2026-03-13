#include <common.h>
#include <firebeam.h>

extern "C" auto entry(
    const char*  argv,
    const size_t argc
) -> void {
    firebeam::packet::add_u32( GetLogicalDrives() );
}
