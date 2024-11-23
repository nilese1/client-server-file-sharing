import tkinter as tk
from tkinter import simpledialog

'''
Dialog I created with my blood, sweat, and tears
'''
class LoginDialog(simpledialog.Dialog):
    def body(self, master):
        self.username_label = tk.Label(master, text="Username:")
        self.username_label.grid(row=0)
        self.username_entry = tk.Entry(master)
        self.username_entry.grid(row=0, column=1)

        self.password_label = tk.Label(master, text="Password:")
        self.password_label.grid(row=1)
        self.password_entry = tk.Entry(master)
        self.password_entry.grid(row=1, column=1)

        return self.username_entry  # Initial focus

    def apply(self):
        self.result = (self.username_entry.get(), self.password_entry.get())

