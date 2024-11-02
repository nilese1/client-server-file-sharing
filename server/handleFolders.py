# for dir and subfolder functions
from pathlib import Path


def list_dir(rootPath: str, recursive: bool = False):
    '''
    List all files and directories in given path. To list every single thing, set recursive to True. 
    TODO: Probably will return a dict object. Idea is to serialize it into JSON when sending over network.
    '''

    path = Path(rootPath)

    generator = path.rglob("*") if recursive else path.glob("*")
    for subPath in generator:
        print(f'path: {subPath.relative_to(path).as_posix()}{"/" if subPath.is_dir() else ""}')
    

list_dir("server_root", False)