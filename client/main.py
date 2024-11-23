#!/usr/bin/python3
import pathlib
import tkinter as tk
from tkinter import simpledialog
from tkinter import filedialog
from tkinter import messagebox
import pygubu


from ui.srcui import FileSharingAppUI
from enum import Enum
from net import Client
from net import PacketType
from request import *
from send import *
import socket
import ssl
import hashlib
import json
import struct
import base64


# get from prompting the user later
SERVER_IP = '127.0.0.1'
SERVER_PORT = 30000


class FileSharingApp(FileSharingAppUI):
    def __init__(self, master=None, on_first_object_cb=None):
        super().__init__(master, on_first_object_cb=None)

        # Kill client thread on closing
        self.mainwindow.protocol('WM_DELETE_WINDOW', self.close)
        self.treeview = self.builder.get_object('tv_filetree')
        self.client = None
        self.treeview.bind('<Button-3>', self.deselect_item_on_right_click)

    def deselect_item_on_right_click(self, event):
        for item in self.treeview.selection():
            self.treeview.selection_remove(item)

    def authenticate_client(self):
        """Prompt for user credentials and authenticate with the server."""
        username = input("Enter username: ")
        password = input("Enter password: ")

        # Use the authenticate method from the Client class
        try:
            self.client.authenticate(username, password)
            logger.info("Authentication successful. You may now access the server.")

            # client.authenticate not implemented

        except Exception as e:
            self.handle_error(e)
            self.client.disconnect()

    '''
    get an item's path from a selected item in the treeview that the user is currently clicked on
    '''
    def get_item_path(self, item):
        if not item:
            return ''
        # No possible error situations that aren't already handled
        selected_item = self.treeview.item(item)
        item_path = selected_item["text"]
        parent_item = self.treeview.parent(item)
        while parent_item:
            item_path = self.treeview.item(parent_item)['text'] + '/' + item_path
            parent_item = self.treeview.parent(parent_item)
        return item_path

    def refresh_filetree(self):
        if not self.client:
            return

        try:
            filetree = get_filetree(self.client)
            self.treeview.delete(*self.treeview.get_children())

            load_filetree(self.treeview, filetree)
        except Exception as e:
            self.handle_error(e)


    def callback(self, event=None):
        pass

    def create_directory(self):
        if not self.client:
            return

        new_dir = simpledialog.askstring("Input", "Enter the new directory name:", parent=self.mainwindow)
        item = self.treeview.focus()
        # user cancelled
        if not new_dir:
            return
        
        if item:
            new_dir = self.get_item_path(item) + "/" + new_dir

        try:
            create_directory_handler(self.client, new_dir)
            self.refresh_filetree()
        except Exception as e:
            self.handle_error(e)

    def delete_file(self):
        if not self.client:
           return

        selected_item = self.treeview.focus()
        item_path = self.get_item_path(selected_item)


        # item that user selects by clicking on it
        try:
            delete_file_handler(self.client, item_path)
            self.refresh_filetree()
        except Exception as e:
            logger.error(f'HIHHIHIHI')
            self.handle_error(e)

    def download_file(self):
        if not self.client:
            return

        # get file the user has clicked on
        selected_item = self.treeview.focus()
        item_path = self.get_item_path(selected_item)

        # get path to save the file to
        folder_selected = filedialog.askdirectory()
        if not folder_selected:
            return
        
        try:
            download_file(self.client, item_path, folder_selected, self.download_completion, self.download_status, self.mainwindow)
        except Exception as e:
            self.handle_error(e)

    def upload_file(self):
        if not self.client:
            return

        item = self.treeview.focus()
        item_path = ''

       
        file_to_upload = filedialog.askopenfilename()
        if not file_to_upload:
            return
        
        if item:
            item_path = self.get_item_path(item) + "/" + Path(file_to_upload).name

        try:
            upload_file(self.client, file_to_upload, item_path, self.download_completion, self.download_status, self.mainwindow)
            self.refresh_filetree()
        except Exception as e:
            logger.error(f'Error uploading file {file_to_upload}: {e}')
            self.handle_error(e)

    def prompt_server_connection(self):
        # ask client if they'd like to disconnect later
        if self.client:
            return
        
        # TEST
        self.client = Client(SERVER_IP, SERVER_PORT)
        # Show connection status to ui
        self.connection_status.set(f'Connected to {self.client.server_ip}')

        self.client.connect()

        # Authenticate on startup
        # uncomment when we implement authentication
        # self.authenticate_client()

        self.client.start()
        self.refresh_filetree() 
 
    def close(self):
        if self.client:
            self.client.disconnect()

        self.mainwindow.destroy()

    def handle_error(self, message):
        error_message = messagebox.showerror("ERROR", message)

        logger.error(message)

if __name__ == "__main__":
    try:
        app = FileSharingApp()
        app.run()
    except KeyboardInterrupt:
        app.client.stop()
