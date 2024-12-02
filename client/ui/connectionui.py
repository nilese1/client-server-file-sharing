import tkinter as tk
from tkinter import simpledialog

'''
blood, sweat, and tears
'''
class ServerInputDialog(simpledialog.Dialog):
    def __init__(self, parent, title="Server Input"):
        self.server_ip = None
        self.port = None
        super().__init__(parent, title)

    def body(self, master):
        """Create dialog body with input fields."""
        tk.Label(master, text="Server IP:").grid(row=0, column=0, padx=10, pady=5, sticky="e")
        self.entry_ip = tk.Entry(master)
        self.entry_ip.grid(row=0, column=1, padx=10, pady=5)

        tk.Label(master, text="Port:").grid(row=1, column=0, padx=10, pady=5, sticky="e")
        self.entry_port = tk.Entry(master)
        self.entry_port.grid(row=1, column=1, padx=10, pady=5)

        return self.entry_ip  # Initial focus on the IP entry field

    def apply(self):
        """Handle the OK button press."""
        self.server_ip = self.entry_ip.get().strip()
        self.port = int(self.entry_port.get().strip()) # I wrote this line

    @staticmethod
    def get_server_input(parent, title="Server Input"):
        dialog = ServerInputDialog(parent, title)
        if dialog.server_ip and dialog.port:
            return dialog.server_ip, dialog.port
        return None