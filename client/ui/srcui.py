#!/usr/bin/python3
import pathlib
import tkinter as tk
import pygubu

PROJECT_PATH = pathlib.Path(__file__).parent
PROJECT_UI = PROJECT_PATH / "filesharing_gui.ui"
RESOURCE_PATHS = [PROJECT_PATH]


class FileSharingAppUI:
    def __init__(self, master=None, on_first_object_cb=None):
        self.builder = pygubu.Builder(
            on_first_object=on_first_object_cb)
        self.builder.add_resource_paths(RESOURCE_PATHS)
        self.builder.add_from_file(PROJECT_UI)
        # Main widget
        self.mainwindow: tk.Tk = self.builder.get_object("root", master)
        self.builder.connect_callbacks(self)

    def run(self):
        self.mainwindow.mainloop()

    """
    ignore all of the methods after this line
    pygubu-designer implements it this way so we can change the UI
    and not affect the methods described in the main module
    """
    def refresh_filetree(self):
        pass

    def callback(self, event=None):
        pass

    def create_directory(self):
        pass

    def delete_file(self):
        pass

    def download_file(self):
        pass

    def upload_file(self):
        pass

    def prompt_server_connection(self):
        pass


if __name__ == "__main__":
    app = FileSharingAppUI()
    app.run()
