#pragma once

#include <windows.h>
#include <stdint.h>

//
// a bit set to NTSTATUS to tell the server that it
// is a normal Win32 Error and not a NTSTATUS error
#define KN_FACILITY_WIN32_BIT (FACILITY_WIN32 << 16)