import json
import asyncio
import pyhavoc

from os.path       import *
from pyhavoc.agent import *
from pyhavoc.ui    import *
from pyhavoc.core  import *

KAINE_FILESYSTEM_CONFIG = 'extension'

@KnRegisterCommand(
    command     = 'vm-ls',
    description = 'file listing using firebeam',
    group       = 'filesystem commands' )
class TaskVmFileListCommand( HcKaineCommand ):

    def __init__( self, *args, **kwargs ):
        super().__init__( *args, **kwargs )
        self.key_id                   : str = 'vm-filesys.ls'
        self.bytecode_path            : str = f'{dirname( __file__ )}/bin/vm-filesys-ls.x64.exe'
        self.FILE_ATTRIBUTE_DIRECTORY : int = 0x00000010
        return

    @staticmethod
    def arguments( parser ):

        parser.epilog = (
            "example usage:\n"
            "  vm-ls C:\\\\Windows\\\\Temp\n"
            "  vm-ls C:\\\\Windows\\\\Users\\\\John\\\\Documents\n"
            "  vm-ls \\\\\\\\.\\\\pipe\\\\*mojo.*\n"
            "\n"
            "the vm-ls command allows to use the * symbol to query\n"
            "for specific or certain files and extensions.\n"
        )

        parser.add_argument( 'path', nargs='?', default='.\\*', type=str, help="path to list" )

        return

    async def execute( self, args ):
        task    = self.list_directory( args.path )
        task_id = task.task_uuid()

        if args.path == '.\\*' or args.path == '.':
            self.log_task( task_id, f'list current working directory' )
        else:
            self.log_task( task_id, f'list directory files and folders: {args.path}' )

        try:
            directory, files = await task.result()

            self.log_raw( '<br>' + self.format_directory_listing( directory, files ) + '<br>', is_html = True, task_id = task.task_uuid() )
        except Exception as e:
            self.log_error( f"({task_id:x}) {e}", task_id = task_id )
            return

        self.log_success( f"({task_id:x}) successfully executed bytecode", task_id = task_id )

        return

    def list_directory(
        self,
        directory: str  = '.\\*',
    ) -> HcKaineTask:
        if not self._check_registered():
            raise RuntimeError( 'firebeam extension has not been registered' )

        description = f'list files from '
        if directory == '.' or directory == '.\\*':
            description += 'current working directory'
        else:
            description += directory

        task_id = self.agent().task_generate()
        self.agent().task_description( task_id, description )

        firebeam = self.agent().command( 'firebeam' )

        if self.key_id not in self.agent().key_store:
            vm_task  = firebeam.firebeam_execute(
                self.bytecode_path,
                self.path_validate( directory ),
                flag_cache = True,
                task_id    = task_id
            )
        else:
            vm_task  = firebeam.firebeam_invoke(
                self.agent().key_store[ self.key_id ],
                self.path_validate( directory ),
                task_id = task_id
            )

        return self.agent().create_task(
            description = description,
            task_uuid   = task_id,
            coroutine   = self._process_response( vm_task )
        )

    def register_command( self, args ) -> bool:
        return self._check_registered()

    def path_validate( self, path: str ) -> str:
        if '*' in path:
            return self.agent().to_unicode( path )

        if path.endswith( "\\*" ):
            return self.agent().to_unicode( path )
        else:
            return self.agent().to_unicode( path.rstrip( "\\" ) + "\\*" )

    @staticmethod
    def format_size( size ):
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024:
                return f"{size:.0f} {unit}"
            size /= 1024
        return f"{size:.0f} PB"  # Handles exceptionally large sizes

    def format_directory_listing( self, directory, files ):
        html_output = []
        html_space  = '&nbsp;'

        count_files, count_dirs, files_size, html_output = self._format_structure(
            directory,
            files
        )

        summary = f'  { self.format_size( files_size ) } Total File Size for { count_files } File(s) and { count_dirs } Dir(s)'.replace( ' ', html_space  )

        html_output.append( '' )
        html_output.append( HcTheme.console().foreground( summary, bold = True ) )

        return "<br>".join( html_output )

    def _format_structure( self, directory, files ) -> tuple[int, int, int, list[str]]:
        html_output = []
        html_space  = '&nbsp;'

        html_output.append( HcTheme.console().foreground( f'&nbsp;Listing Directory: {directory}' ) )
        html_output.append( HcTheme.console().foreground( f'&nbsp;{"=" * (20 + len(directory))}' ) )
        html_output.append( '' )

        header  = f'  {"Last Modified":<20}  {"Type":<6}  {"Size":<10}  {"Name"}'.replace( ' ', html_space  )
        divider = f'  {"-" * 20}  {"-" * 6}  {"-" * 10}  {"-" * 30}'.replace( ' ', html_space  )

        html_output.append( HcTheme.console().foreground( f'{header}' ) )
        html_output.append( HcTheme.console().foreground( f'{divider}' ) )

        count_files = 0
        count_dirs  = 0
        files_size  = 0

        for entry in files:
            file_type = "dir" if entry[ 'attribute' ] & self.FILE_ATTRIBUTE_DIRECTORY else "fil"
            file_name = entry[ 'file name' ]
            file_size = '' if ( file_type == 'dir' ) else self.format_size( entry[ 'file size' ] )

            if file_type == "dir":
                file_name   = HcTheme.console().cyan( file_name )
                count_dirs += 1
            else:
                count_files += 1
                files_size  += entry[ 'file size' ]

            html_output.append( (
                f'  {entry["last write"]:<20}  '
                f'{file_type:<6}  '
                f'{file_size:<10}  '
            ).replace( ' ', html_space ) + f'{file_name}' )

        return count_files, count_dirs, files_size, html_output

    async def _process_response(
        self,
        vm_task : HcKaineTask
    ) -> tuple[str, list[dict]]:
        if self.key_id in self.agent().key_store:
            try:
                handle, parser = await vm_task
            except Exception as e:
                if e != 'couldn\'t find specified bytecode id':
                    del self.agent().key_store[ self.key_id ]
                raise e
        else:
            handle, parser = await vm_task
            self.agent().key_store[ self.key_id ] = handle

        directory, file_list = self._parse_files( parser )

        self.log_event( 'filesystem.ls', json.dumps( { 'directory': directory, 'files': file_list } ), task_id = vm_task.task_id() )

        return directory, file_list

    def _check_registered( self ) -> bool:
        firebeam = self.agent().command( 'firebeam' )

        if firebeam is None:
            return False

        #
        # check when ever it has been registered
        return firebeam.register_command( None )

    def _parse_files( self, parser: KnParser ) -> tuple[str, list[dict]]:
        file_list: list[dict] = []
        directory: str        = parser.get_wstring()

        if directory.endswith( '\\*' ):
            directory = directory.rstrip( '\\*' )

        # handle the case of a single drive letter (e.g., "C:" or "Z:")
        if len( directory ) == 2 and directory[ 1 ] == ':' and directory[ 0 ].isalpha():
            directory += '\\' # ensure it has a trailing backslash

        while parser.length():
            file_name = parser.get_wstring()
            if len( file_name ) == 0:
                break

            entry = {
                'file name'  : file_name,
                'attribute'  : parser.get_u32(),
                'file size'  : parser.get_u64(),

                'time create': '{:0>2d}/{:0>2d}/{} {:0>2d}:{:0>2d}:{:0>2d}'.format(
                    parser.get_u16(), parser.get_u16(), parser.get_u16(),
                    parser.get_u16(), parser.get_u16(), parser.get_u16()
                ),

                'last write': '{:0>2d}/{:0>2d}/{} {:0>2d}:{:0>2d}:{:0>2d}'.format(
                    parser.get_u16(), parser.get_u16(), parser.get_u16(),
                    parser.get_u16(), parser.get_u16(), parser.get_u16()
                ),
            }

            file_list.append( entry )

        ##
        ## order the folders first then the files
        normalized_list = sorted(
            [
                {
                    'time create': entry[ 'time create' ],
                    'last write' : entry[ 'last write'  ],
                    'file size'  : entry[ 'file size'   ],
                    'format size': self.format_size( entry[ 'file size' ] ),
                    'file name'  : entry[ 'file name'   ],
                    'attribute'  : entry[ 'attribute'   ],
                    **( { 'files': entry[ 'files' ] } if 'files' in entry else {} )
                }
                for entry in file_list if entry[ 'file name' ] not in { '.', '..' }
            ],

            key=lambda x: (
                x[ 'attribute' ] != self.FILE_ATTRIBUTE_DIRECTORY, # prioritize directories
                x[ 'file name' ]                                   # sort by file name
            )
        )

        return directory, normalized_list


@KnRegisterCommand(
    command     = 'vm-drives',
    description = 'list all available drives',
    group       = 'filesystem commands' )
class TaskVmListDrivesCommand( HcKaineCommand ):

    def __init__( self, *args, **kwargs ):
        super().__init__( *args, **kwargs )
        self.key_id        : str = 'vm-filesys.drives'
        self.bytecode_path : str = f'{dirname( __file__ )}/bin/vm-filesys-drives.x64.exe'
        return

    @staticmethod
    def arguments( parser ):
        return

    def register_command( self, args ) -> bool:
        return self._check_registered()

    async def execute( self, args ):
        task    = self.drives()
        task_id = task.task_uuid()

        self.log_task( task_id, 'list all available drives' )

        try:
            drives = await task.result()
            self.log_raw( '<br>' + self.format_drive_list( drives ) + '<br>', is_html = True, task_id = task_id )
        except Exception as e:
            self.log_error( f"({task_id:x}) failed to list drives: {e}" )
            return

        self.log_success( f"({task_id:x}) successfully listed {len(drives)} drives", task_id = task_id )

        return

    def drives(
        self,
    ) -> HcKaineTask:
        if not self._check_registered():
            raise RuntimeError( 'firebeam extension has not been registered' )

        description = 'list available drives'
        task_id     = self.agent().task_generate()
        self.agent().task_description( task_id, description )

        firebeam = self.agent().command( 'firebeam' )

        if self.key_id not in self.agent().key_store:
            vm_task  = firebeam.firebeam_execute(
                self.bytecode_path,
                flag_cache = True,
                task_id    = task_id
            )
        else:
            vm_task  = firebeam.firebeam_invoke(
                self.agent().key_store[ self.key_id ],
                task_id = task_id
            )

        return self.agent().create_task(
            description = description,
            task_uuid   = task_id,
            coroutine   = self._process_response( vm_task )
        )

    async def _process_response(
        self,
        vm_task: HcKaineTask,
    ):
        if self.key_id in self.agent().key_store:
            try:
                handle, parser = await vm_task
            except Exception as e:
                if e != 'couldn\'t find specified bytecode id':
                    del self.agent().key_store[ self.key_id ]
                raise e
        else:
            handle, parser = await vm_task
            self.agent().key_store[ self.key_id ] = handle

        drives = []
        value  = parser.get_u32()

        for i in range( 26 ):
            if value & ( 1 << i ):
                drives.append( f"{ chr( ord( 'A' ) + i ) }" )

        return drives

    def format_drive_list( self, drive_list: list ):
        html_output = []
        html_space  = '&nbsp;'

        headers = [ "Drive Letter" ]
        header_row = (f'  { headers[ 0 ]:<12}  ').replace( " ", html_space )
        divider_row = (f'  {"-"*12}  ').replace( " ", html_space )

        html_output.append( HcTheme.console().foreground( "&nbsp;Available Drives:" ) )
        html_output.append( HcTheme.console().foreground( "&nbsp;==================" ) )
        html_output.append( '' )

        if len( drive_list ) > 0:
            for drive in drive_list:
                row = f'  { drive }:\\  '.replace( " ", html_space )
                html_output.append( HcTheme.console().foreground( row ) )
        else:
            html_output.append( '    (No drives found)'.replace( ' ', html_space ) )

        return "<br>".join(html_output)


    def _check_registered( self ) -> bool:
        firebeam = self.agent().command( 'firebeam' )

        if firebeam is None:
            return False

        #
        # check when ever it has been registered
        return firebeam.register_command( None )

@KnRegisterCommand(
    command     = 'vm-mkdir',
    description = 'make a new directory',
    group       = 'filesystem commands' )
class TaskMkdirCommand( HcKaineCommand ):

    def __init__( self, *args, **kwargs ):
        super().__init__( *args, **kwargs )
        self.key_id        : str = 'vm-filesys.mkdir'
        self.bytecode_path : str = f'{dirname( __file__ )}/bin/vm-filesys-mkdir.x64.exe'
        return

    @staticmethod
    def arguments( parser ):
        parser.add_argument( 'PATH', type=str, help="directory name or path to create" )
        return

    def register_command( self, args ) -> bool:
        return self._check_registered()

    async def execute( self, args ):
        task    = self.mkdir( args.PATH )
        task_id = task.task_id()

        self.log_task( task_id, f'make a new directory: {args.PATH}' )

        try:
            await task.result()
        except Exception as e:
            self.log_error( f"({task_id:x}) failed to make directory: {e}", task_id = task_id )
            return

        self.log_success( f"({task_id:x}) successfully created directory", task_id = task_id )

        return

    def mkdir(
        self,
        path: str
    ) -> HcKaineTask:
        if not self._check_registered():
            raise RuntimeError( 'firebeam extension has not been registered' )

        description = f'make new directory: {path}'
        task_id     = self.agent().task_generate()
        self.agent().task_description( task_id, description )

        firebeam = self.agent().command( 'firebeam' )

        if self.key_id not in self.agent().key_store:
            vm_task  = firebeam.firebeam_execute(
                self.bytecode_path,
                self.agent().to_unicode( path ),
                flag_cache = True,
                task_id    = task_id
            )
        else:
            vm_task  = firebeam.firebeam_invoke(
                self.agent().key_store[ self.key_id ],
                self.agent().to_unicode( path ),
                task_id = task_id
            )

        return self.agent().create_task(
            description = description,
            task_uuid   = task_id,
            coroutine   = self._process_response( vm_task )
        )

    async def _process_response(
        self,
        vm_task: HcKaineTask,
    ):
        if self.key_id in self.agent().key_store:
            try:
                handle, parser = await vm_task
            except Exception as e:
                if e != 'couldn\'t find specified bytecode id':
                    del self.agent().key_store[ self.key_id ]
                raise e
        else:
            handle, parser = await vm_task
            self.agent().key_store[ self.key_id ] = handle

        return

    def _check_registered( self ) -> bool:
        firebeam = self.agent().command( 'firebeam' )

        if firebeam is None:
            return False

        #
        # check when ever it has been registered
        return firebeam.register_command( None )


@KnRegisterCommand(
    command     = 'vm-remove',
    description = 'remove a file or directory',
    group       = 'filesystem commands' )
class TaskRemoveCommand( HcKaineCommand ):

    def __init__( self, *args, **kwargs ):
        super().__init__( *args, **kwargs )
        self.key_id        : str = 'vm-filesys.remove'
        self.bytecode_path : str = f'{dirname( __file__ )}/bin/vm-filesys-remove.x64.exe'
        return

    @staticmethod
    def arguments( parser ):
        parser.add_argument( 'PATH', type=str, help="path of file or directory to remove" )
        return

    def register_command( self, args ) -> bool:
        return self._check_registered()

    async def execute( self, args ):
        task    = self.remove( args.PATH )
        task_id = task.task_id()

        self.log_task( task_id, f'remove path: {args.PATH}' )

        try:
            is_dir = await task.result()
        except Exception as e:
            self.log_error( f"({task_id:x}) failed to remove path: {e}", task_id = task_id )
            return

        self.log_success( f"({task_id:x}) successfully removed {'directory' if is_dir else 'file'}", task_id = task_id )

        return

    def remove(
        self,
        path: str
    ) -> HcKaineTask:
        if not self._check_registered():
            raise RuntimeError( 'firebeam extension has not been registered' )

        description = f'remove path {path}'
        task_id     = self.agent().task_generate()
        self.agent().task_description( task_id, description )

        firebeam = self.agent().command( 'firebeam' )

        if self.key_id not in self.agent().key_store:
            vm_task  = firebeam.firebeam_execute(
                self.bytecode_path,
                self.agent().to_unicode( path ),
                flag_cache = True,
                task_id    = task_id
            )
        else:
            vm_task  = firebeam.firebeam_invoke(
                self.agent().key_store[ self.key_id ],
                self.agent().to_unicode( path ),
                task_id = task_id
            )

        return self.agent().create_task(
            description = description,
            task_uuid   = task_id,
            coroutine   = self._process_response( vm_task )
        )

    async def _process_response(
        self,
        vm_task: HcKaineTask,
    ):
        if self.key_id in self.agent().key_store:
            try:
                handle, parser = await vm_task
            except Exception as e:
                if e != 'couldn\'t find specified bytecode id':
                    del self.agent().key_store[ self.key_id ]
                raise e
        else:
            handle, parser = await vm_task
            self.agent().key_store[ self.key_id ] = handle

        return parser.get_u08() != 0

    def _check_registered( self ) -> bool:
        firebeam = self.agent().command( 'firebeam' )

        if firebeam is None:
            return False

        #
        # check when ever it has been registered
        return firebeam.register_command( None )

@KnRegisterCommand(
    command     = 'vm-move',
    description = 'move a file',
    group       = 'filesystem commands' )
class TaskMoveCommand( HcKaineCommand ):

    def __init__( self, *args, **kwargs ):
        super().__init__( *args, **kwargs )
        self.key_id        : str = 'vm-filesys.move'
        self.bytecode_path : str = f'{dirname( __file__ )}/bin/vm-filesys-move.x64.exe'
        return

    @staticmethod
    def arguments( parser ):
        parser.add_argument( 'SOURCE', type=str, help="source of file to move" )
        parser.add_argument( 'DESTINATION', type=str, help="destination path to move to" )
        return

    def register_command( self, args ) -> bool:
        return self._check_registered()

    async def execute( self, args ):
        task    = self.moved( args.SOURCE, args.DESTINATION )
        task_id = task.task_id()

        self.log_task( task_id, f'moved {args.SOURCE} to {args.DESTINATION}' )

        try:
            await task.result()
        except Exception as e:
            self.log_error( f"({task_id:x}) failed to moved file: {e}", task_id = task_id )
            return

        self.log_success( f"({task_id:x}) successfully moved file", task_id = task_id )

        return

    def move(
        self,
        source      : str,
        destination : str
    ) -> HcKaineTask:
        if not self._check_registered():
            raise RuntimeError( 'firebeam extension has not been registered' )

        description = f'copy {source} to {destination}'
        task_id     = self.agent().task_generate()
        self.agent().task_description( task_id, description )

        firebeam = self.agent().command( 'firebeam' )

        if self.key_id not in self.agent().key_store:
            vm_task  = firebeam.firebeam_execute(
                self.bytecode_path,
                self.agent().to_unicode( source ),
                self.agent().to_unicode( destination ),
                flag_cache = True,
                task_id    = task_id
            )
        else:
            vm_task  = firebeam.firebeam_invoke(
                self.agent().key_store[ self.key_id ],
                self.agent().to_unicode( source ),
                self.agent().to_unicode( destination ),
                task_id = task_id
            )

        return self.agent().create_task(
            description = description,
            task_uuid   = task_id,
            coroutine   = self._process_response( vm_task )
        )

    async def _process_response(
        self,
        vm_task: HcKaineTask,
    ):
        if self.key_id in self.agent().key_store:
            try:
                handle, parser = await vm_task
            except Exception as e:
                if e != 'couldn\'t find specified bytecode id':
                    del self.agent().key_store[ self.key_id ]
                raise e
        else:
            handle, parser = await vm_task
            self.agent().key_store[ self.key_id ] = handle

        return

    def _check_registered( self ) -> bool:
        firebeam = self.agent().command( 'firebeam' )

        if firebeam is None:
            return False

        #
        # check when ever it has been registered
        return firebeam.register_command( None )

##
## functions to be used to monkey-patch the
## methods that the file-explorer uses
##

_original_file_browser_drives = pyhavoc.agent._file_browser_list_drives
def _vm_file_browser_list_drives(
    agent,
) -> tuple[int, list[str]] | str:
    ##
    ## execute the file listing
    try:
        list_drives = agent.command( 'vm-drives' )

        if list_drives is None:
            return 'ERROR: command \"vm-drives\" has not been registered. ensure that the filesystem script is properly loaded'

        ##
        ## async function wrapper
        async def _async_fn():
            task   = list_drives.drives()
            drives = await task.result()

            return task.task_uuid(), drives

        return asyncio.run( _async_fn() )
    except Exception as e:
        traceback.print_exc()
        return str( e ).strip()


_original_file_browser_remove = pyhavoc.agent._file_browser_remove
def _vm_file_browser_remove(
    agent,
    path: str
) -> tuple[int, bool] | str:
    ##
    ## execute the file listing
    try:
        command = agent.command( 'vm-remove' )
        if command is None:
            return 'ERROR: command \"vm-remove\" has not been registered. ensure that the script is properly loaded'

        ##
        ## async function wrapper
        async def _async_fn():
            task   = command.remove( path )
            is_dir = await task.result()

            return task.task_uuid(), is_dir

        return asyncio.run( _async_fn() )
    except Exception as e:
        traceback.print_exc()
        return str( e ).strip()

_original_file_browser_mkdir = pyhavoc.agent._file_browser_mkdir
def _vm_file_browser_mkdir(
    agent,
    path: str
) -> tuple[int, bool] | str:
    ##
    ## execute the path moving
    try:
        command = agent.command( 'vm-mkdir' )

        if command is None:
            return 'ERROR: command \"vm-mkdir\" has not been registered. ensure that the script is properly loaded'

        ##
        ## async function wrapper
        async def _async_fn():
            task = command.mkdir( path )

            ##
            ## wait for the task to finish
            await task.result()

            return task.task_uuid()

        return asyncio.run( _async_fn() )
    except Exception as e:
        return str( e ).strip()


_original_file_browser_move = pyhavoc.agent._file_browser_move
def _vm_file_browser_move(
    agent,
    source     : str,
    destination: str,
) -> tuple[int, bool] | str:
    #
    # execute the path moving
    try:
        command = agent.command( 'vm-move' )

        if command is None:
            return 'ERROR: command \"vm-move\" has not been registered. ensure that the script is properly loaded'

        #
        # async function wrapper
        async def _async_fn():
            task = command.move( source, destination )

            #
            # wait for the task to finish
            await task.result()

            return task.task_uuid()

        return asyncio.run( _async_fn() )
    except Exception as e:
        return str( e ).strip()

_original_file_browser_list_directory = pyhavoc.agent._file_browser_list_directory
def _vm_file_browser_list_directory(
    agent,
    directory  = '.',
    dirs_only  = False,
    files_only = False
) -> tuple[int, str, list] | str:
    ##
    ## execute the file listing
    try:
        list_dir = agent.command( 'vm-ls' )

        if list_dir is None:
            return 'ERROR: command \"vm-ls\" has not been registered. ensure that the firebeam script is properly loaded'

        ##
        ## async function wrapper
        async def _async_fn():
            _dir = directory

            if _dir != '.':
                agent.key_store[ '_file_browser.last-path' ] = _dir
            else:
                if '_file_browser.last-path' in agent.key_store:
                    _dir = agent.key_store[ '_file_browser.last-path' ]

            task        = list_dir.list_directory( directory = _dir )
            path, files = await task.result()

            return task.task_uuid(), path, files

        return asyncio.run( _async_fn() )
    except Exception as e:
        return str( e ).strip()

# Save original

@pyhavoc.core.HcRegisterMenuAction( 'Switch FileSystem Feature' )
def switch_filesystem_dialog():
    global KAINE_FILESYSTEM_CONFIG

    dialog = QDialog()
    dialog.setModal( True )
    dialog.setObjectName( u"KnSwitchFilesystemDialog" )
    dialog.setWindowTitle( 'Switch FileSystem Feature' )
    dialog.resize( 500, 220 )

    grid_layout = QGridLayout( dialog )
    grid_layout.setObjectName( u"grid_layout" )

    group_fs = QGroupBox( dialog )
    group_fs.setObjectName( u"group_fs" )
    group_fs.setTitle( 'FileSystem Backend' )

    fs_layout = QGridLayout( group_fs )
    fs_layout.setObjectName( u"fs_layout" )

    fs_combo = QComboBox( group_fs )
    fs_combo.setObjectName( u"fs_combo" )
    fs_combo.addItem( 'extension' )
    fs_combo.addItem( 'virtual-machine' )

    fs_info = QLabel( group_fs )
    fs_info.setObjectName( u"fs_info" )
    fs_info.setWordWrap( True )

    button_box = QDialogButtonBox( dialog )
    button_box.setObjectName( u"button_box" )
    button_box.setOrientation( Qt.Orientation.Horizontal )
    button_box.setStandardButtons( QDialogButtonBox.StandardButton.Cancel | QDialogButtonBox.StandardButton.Save )

    fs_layout.addWidget( fs_combo,  0, 0, 1, 1 )
    fs_layout.addWidget( fs_info,   1, 0, 1, 1 )

    grid_layout.addWidget( group_fs, 0, 0, 1, 1 )
    grid_layout.addItem( QSpacerItem( 20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding ), 1, 0, 1, 1 )
    grid_layout.addWidget( button_box, 2, 0, 1, 1 )

    button_box.accepted.connect( dialog.accept )
    button_box.rejected.connect( dialog.reject )

    info_texts = {
        'extension':       u'[ℹ] Use the FileSystem Extension to interact with the filesystem',
        'virtual-machine': u'[ℹ] Use the Firebeam Virtual Machine to interact with the filesystem',
    }

    def fs_change( mode: str ):
        fs_info.setText( QCoreApplication.translate( "KnSwitchFilesystemDialog", info_texts.get( mode, '' ), None ) )

    fs_combo.currentTextChanged.connect( fs_change )
    fs_combo.setCurrentText( KAINE_FILESYSTEM_CONFIG )
    fs_change( fs_combo.currentText() )

    if dialog.exec() != QDialog.DialogCode.Accepted:
        return

    selected = fs_combo.currentText()
    KAINE_FILESYSTEM_CONFIG = selected

    if selected == 'extension':
        pyhavoc.agent._file_browser_list_directory = _original_file_browser_list_directory
        pyhavoc.agent._file_browser_list_drives    = _original_file_browser_drives
        pyhavoc.agent._file_browser_remove         = _original_file_browser_remove
        pyhavoc.agent._file_browser_mkdir          = _original_file_browser_mkdir
        pyhavoc.agent._file_browser_move           = _original_file_browser_move
    elif selected == 'virtual-machine':
        pyhavoc.agent._file_browser_list_directory = _vm_file_browser_list_directory
        pyhavoc.agent._file_browser_list_drives    = _vm_file_browser_list_drives
        pyhavoc.agent._file_browser_remove         = _vm_file_browser_remove
        pyhavoc.agent._file_browser_mkdir          = _vm_file_browser_mkdir
        pyhavoc.agent._file_browser_move           = _vm_file_browser_move
