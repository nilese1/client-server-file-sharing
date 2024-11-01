#!/usr/bin/python3
import pathlib
import tkinter as tk
import pygubu
from ui.srcui import FileSharingAppUI
from enum import Enum
from net import Client
from net import PacketType


# get from prompting the user later
SERVER_IP = '127.0.0.1'
SERVER_PORT = 30000


class FileSharingApp(FileSharingAppUI):
    def __init__(self, master=None, on_first_object_cb=None):
        super().__init__(master, on_first_object_cb=None)

        # Kill client thread on closing
        self.mainwindow.protocol('WM_DELETE_WINDOW', self.close)
        self.client = None

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
        # ask client if they'd like to disconnect later
        if self.client:
            return
        
        # TEST
        self.client = Client(SERVER_IP, SERVER_PORT)
        # Show connection status to ui
        self.connection_status.set(f'Connected to {self.client.server_ip}')

        self.client.connect()
        self.client.start()
 
    def close(self):
        if self.client:
            self.client.disconnect()

        self.mainwindow.destroy()


if __name__ == "__main__":
    try:
        app = FileSharingApp()
        app.run()
    except KeyboardInterrupt:
        app.client.stop()
