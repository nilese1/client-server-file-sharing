#!/usr/bin/python3
import pathlib
import tkinter as tk
import pygubu

PROJECT_PATH = pathlib.Path(__file__).parent
ERROR_UI = PROJECT_PATH / "errorHandler.ui"
RESOURCE_PATHS = [PROJECT_PATH]

class ErrorHandler:
    def __init__(self, master=None, parent=None, on_first_object_cb=None):
        self.builder = pygubu.Builder(on_first_object=on_first_object_cb)
        self.builder.add_resource_paths(RESOURCE_PATHS)
        self.builder.add_from_file(ERROR_UI)

        self.mainwindow: tk.Toplevel = self.builder.get_object("toplevel4")

        self.mainwindow.grab_set()
        self.mainwindow.transient(parent)

        self.messageMain: tk.Message= self.builder.get_object("message4")
        self.message = tk.StringVar(value="If you're seeing this, that's a problem.")
        self.messageMain.config(textvariable=self.message)

        self.button: tk.Button = self.builder.get_object("okButton")
        self.button.config(command=self.mainwindow.destroy)

    def run(self):
        self.mainwindow.mainloop()

    def update_error(self, message):
        self.message.set(message)


error = ErrorHandler()
error.update_error("Hello World!!!")
error.run()
