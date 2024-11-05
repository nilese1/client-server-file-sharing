# will handle creation and deletion of files
from pathlib import Path

ROOT_PATH = "server_root"

# not sure what else to add here
def delete_file(path: Path):
    if path.exists() and path.is_file():
        path.unlink()

# must be able to create different types of files? 
def create_file(path: Path, data):
    pass