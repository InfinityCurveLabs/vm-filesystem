#include <windows.h>
#include <common.h>
#include <ntstatus.h>
#include <minicrt.h>
#include <firebeam.h>

extern "C" auto entry(
    const char*  argv,
    const size_t argc
) -> uint32_t {
    auto status      = uint32_t { STATUS_SUCCESS };
    auto list_path   = _buffer<wchar_t>();
    auto file_size   = LARGE_INTEGER { 0, 0 };
    auto system_time = SYSTEMTIME();
    auto last_write  = SYSTEMTIME();
    auto time_create = SYSTEMTIME();
    auto is_dir      = false;
    auto file_handle = HANDLE { nullptr };
    auto str_ptr1    = L".";
    auto str_ptr2    = L"..";
    auto str_cur     = L".\\*";
    auto buffer      = _buffer<wchar_t, MAX_PATH>();
    auto directory   = _buffer<wchar_t>();
    auto length      = uint32_t { 0 };
    auto base_length = uint32_t { 0 };

    WIN32_FIND_DATAW file_data;

    //
    // parse the path to list
    list_path.buffer = firebeam::parser( argv, argc )
        .get_wstring( &list_path.length );

    directory.buffer = list_path.buffer;
    directory.length = list_path.length;

    if ( string::compare( list_path.buffer, const_cast<wchar_t*>( str_cur ) ) == 0 ) {
        directory.length = static_cast<size_t>( GetCurrentDirectoryW( MAX_PATH, buffer.buffer ) );
        if ( directory.length ) {
            directory.buffer = buffer.buffer;
            directory.length = directory.length * sizeof( wchar_t );
        } else {
            directory.length = list_path.length;
        }
    }

    //
    // now properly append the data to it
    //

    if ( ( file_handle = FindFirstFileW( list_path.buffer, &file_data ) ) == INVALID_HANDLE_VALUE ) {
        status = GetLastError() | KN_FACILITY_WIN32_BIT;
        goto LEAVE;
    }

    //
    // allocate the memory for the packet
    //

    firebeam::packet::add_bytes( directory.buffer, directory.length );

    do {
        is_dir = ( file_data.dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY ) == FILE_ATTRIBUTE_DIRECTORY;

        if ( is_dir ) {
            //
            // we are ignoring those symlinks!
            if ( string::compare( file_data.cFileName, const_cast<wchar_t*>( str_ptr1 ) ) == 0 ||
                 string::compare( file_data.cFileName, const_cast<wchar_t*>( str_ptr2 ) ) == 0 )
            {
                continue;
            }
        }

        file_size = {
            .LowPart  = file_data.nFileSizeLow,
            .HighPart = static_cast<LONG>( file_data.nFileSizeHigh ),
        };

        FileTimeToSystemTime( &file_data.ftLastAccessTime, &system_time );
        SystemTimeToTzSpecificLocalTime( nullptr, &system_time, &last_write );

        FileTimeToSystemTime( &file_data.ftCreationTime, &system_time );
        SystemTimeToTzSpecificLocalTime( nullptr, &system_time, &time_create );

        length = wcslen( file_data.cFileName ) * sizeof( wchar_t );

        firebeam::packet::add_bytes( file_data.cFileName, length );
        firebeam::packet::add_u32( file_data.dwFileAttributes );
        firebeam::packet::add_u64( file_size.QuadPart  );
        firebeam::packet::add_u16( time_create.wDay    );
        firebeam::packet::add_u16( time_create.wMonth  );
        firebeam::packet::add_u16( time_create.wYear   );
        firebeam::packet::add_u16( time_create.wHour   );
        firebeam::packet::add_u16( time_create.wMinute );
        firebeam::packet::add_u16( time_create.wSecond );
        firebeam::packet::add_u16( last_write.wDay     );
        firebeam::packet::add_u16( last_write.wMonth   );
        firebeam::packet::add_u16( last_write.wYear    );
        firebeam::packet::add_u16( last_write.wHour    );
        firebeam::packet::add_u16( last_write.wMinute  );
        firebeam::packet::add_u16( last_write.wSecond  );
    } while ( FindNextFileW( file_handle, &file_data ) );

    firebeam::packet::add_u32( 0 );

LEAVE:
    if ( file_handle != INVALID_HANDLE_VALUE ) {
        FindClose( file_handle );
    }

    return status;
}
