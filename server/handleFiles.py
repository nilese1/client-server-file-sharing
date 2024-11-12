# will handle creation and deletion of files
from pathlib import Path
import os

# put in config file later
ROOT_PATH = "server_root"
BUFFER_SIZE = 4096

# not sure what else to add here
def delete_file(path: Path):
    if path.exists() and path.is_file():
        path.unlink()

# must be able to create different types of files? 
def create_file(path: Path, data):
    pass

# Sends a file to the client when the client requests a download
def get_file_info(path: Path):
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(f'File {path} does not exist or is not a file')

    file_size = path.stat().st_size
    file_name = path.name

    return file_size, file_name

       
