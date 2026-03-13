CCX64 = clang++ -target x86_64-w64-mingw32-gnu -fuse-ld=lld -flto

#
# compiler flags
SDK		?= firebeam
CFLAGS  := -nostartfiles -Wl,--plugin-opt=--lto-embed-bitcode=post-merge-pre-opt -Wl,/entry:entry -Wl,--subsystem,console
INCLUDE := -Iinclude -I$(SDK)/include
LIBS 	:= $(SDK)/lib/firebeam.x64.dll

#
# plugin source and object files
SRC := $(wildcard src/*.cc)
OBJ := $(SRC:%.cc=%.obj)

#
# build the entire payload
x64: $(OBJ)

#
# build source to object files
$(OBJ):
	@ echo "[*] building $@ as vm-filesys-$(basename $(notdir $@)).x64.exe"
	@ $(CCX64) $(INCLUDE) -c $(basename $@).cc -o bin/obj/$(basename $(notdir $@)).x64.obj
	@ $(CCX64) $(CFLAGS) -o bin/vm-filesys-$(basename $(notdir $@)).x64.exe bin/obj/$(basename $(notdir $@)).x64.obj $(LIBS)

compile-commands:
	@ mkdir build-commands; cmake -S . -B build-commands -DCMAKE_EXPORT_COMPILE_COMMANDS=ON; cp build-commands/compile_commands.json .; rm -rf build-commands

#
# cleanup binaries
clean:
	@ rm -rf bin/obj/*.obj
	@ rm -rf bin/*.exe
