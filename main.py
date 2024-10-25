#!/usr/bin/python3
import pathlib
import tkinter as tk
import pygubu
from ui.srcui import FileSharingAppUI


class FileSharingApp(FileSharingAppUI):
    def __init__(self, master=None, on_first_object_cb=None):
        super().__init__(master, on_first_object_cb=None)

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
    app = FileSharingApp()
    app.run()
