#ifndef MINICRT_H
#define MINICRT_H

#include <sal.h>
#include <cstdint>
#include <utility>

template <typename T = uint8_t, size_t size = 0>
struct _buffer {
    using TT = std::conditional_t<size == 0, T*, T[size]>;

    TT     buffer;
    size_t length;

    _buffer() : length( size ) {}

    inline auto is_empty() const -> bool {
        return length == 0 && buffer == nullptr;
    }
};

namespace memory {
    inline auto copy(
        _Out_ void*    destination,
        _In_  void*    source,
        _In_  uint32_t length
    ) -> void* {
        for ( size_t i = 0; i < length; i++ ) {
            static_cast<uint8_t*>( destination )[ i ] = static_cast<uint8_t *>( source )[ i ];
        };

        return destination;
    }

    template <typename T = void*>
    inline auto rva(
        _In_ void*     memory,
        _In_ uintptr_t length
    ) -> T {
        return reinterpret_cast<T>( reinterpret_cast<uintptr_t>( memory ) + length );
    }
}

namespace string {
    template <typename T = char>
    inline auto compare(
        _In_ T* string1,
        _In_ T* string2
    ) -> size_t {
        auto s1 = string1;
        auto s2 = string2;

        if ( !s1 || !s2 ) {
            return -1;
        }

        for (; *s1 == *s2; s1++, s2++ ) {
            if ( *s1 == static_cast<T>( 0 ) ) {
                return 0;
            }
        }

        return ( ( *static_cast<T*>( s1 ) < *static_cast<T*>( string2 ) ) ? -1 : +1 );
    }
}

#endif
