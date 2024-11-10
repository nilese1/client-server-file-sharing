# for dir and subfolder functions
from pathlib import Path
from pprint import pprint

# put in config file later
ROOT_PATH = "server_root"

def list_dir(rootPath: Path):
    '''
    Recursively gets all files and directories in given path. 
    Returns dictionary that mirrors the hierarchical structure of the files.
    '''

    files_dict = {}
    
    for subPath in rootPath.rglob("*"):
        parts = subPath.relative_to(rootPath).parts
        curr = files_dict
        for part in parts[:-1]:
            curr = curr.setdefault(part, {})
        
        if subPath.is_file():
            curr[parts[-1]] = None
        else:
            curr[parts[-1]] = {}

    
    return files_dict


def create_dir(path: Path):
    '''
    Creates a directory at the specified path. Nested directories can be created.
    '''

    if path.exists():
        raise FileExistsError(f'Directory {path} already exists')

    path.mkdir(parents=True) # parents=True allows for making subdirectories


def delete_dir(path: Path):
    '''
    Recursively delete specified directory. Will delete everything in that directory!
    '''

    if not path.exists():
        raise FileNotFoundError(f'Directory {path} does not exist')
    elif not path.is_dir():
        path.unlink()
        return

    for subPath in path.iterdir():
        if subPath.is_file(): 
            subPath.unlink() # normal files must be deleted because rmdir() only works on empty directories
        else: 
            delete_dir(subPath) # recursion ftw :D

    path.rmdir()

# pprint(list_dir(Path(ROOT_PATH)))

# delete_dir(Path(f'{ROOT_PATH}/newFolder'))

# create_dir(Path(f'{ROOT_PATH}/newFolder/subfolder'))