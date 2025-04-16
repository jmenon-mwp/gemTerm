# connections.py
import os
import tkinter as tk
from tkinter import simpledialog, messagebox, ttk

CONFIG_DIR = os.path.expanduser("~/.config/gemTerm")
CONNECTION_FILES_DIR = os.path.join(CONFIG_DIR, "connections")

def _ensure_connections_dir_exists():
    if not os.path.exists(CONNECTION_FILES_DIR):
        os.makedirs(CONNECTION_FILES_DIR)

def load_connections():
    connections_data = {}
    _ensure_connections_dir_exists()
    for filename in os.listdir(CONNECTION_FILES_DIR):
        if filename.endswith(".gemTerm"):
            unique_id = filename[:-len(".gemTerm")]
            filepath = os.path.join(CONNECTION_FILES_DIR, filename)
            try:
                connection_info = {}
                with open(filepath, 'r') as f:
                    for line in f:
                        if '=' in line:
                            key, value = line.strip().split('=', 1)
                            connection_info[key] = value
                if 'label' in connection_info:
                    connections_data[unique_id] = connection_info
            except Exception as e:
                print(f"Error loading connection from {filename}: {e}")
    return connections_data

def save_connection(unique_id, connection_data):
    _ensure_connections_dir_exists()
    filepath = os.path.join(CONNECTION_FILES_DIR, f"{unique_id}.gemTerm")
    try:
        with open(filepath, 'w') as f:
            for key, value in connection_data.items():
                f.write(f"{key}={value}\n")
    except Exception as e:
        messagebox.showerror("Error", f"Error saving connection '{connection_data.get('label', 'Unnamed')}' to file: {e}")

def add_new_connection(tree, root_node, connections_data):
    dialog = simpledialog.Toplevel(tree)
    dialog.title("Add New Connection")

    labels = ["Label:", "Type:", "Host:", "Auth Type:", "Username:", "Password:", "Private Key File:"]
    entry_vars = [tk.StringVar(dialog) for _ in labels]
    auth_types = ["Password", "Private Key"]
    connection_types = ["SSH", "RDP", "VNC"]
    entries = {}

    for i, label_text in enumerate(labels):
        label = ttk.Label(dialog, text=label_text)
        label.grid(row=i, column=0, padx=5, pady=5, sticky=tk.W)
        if label_text == "Type:":
            type_combo = ttk.Combobox(dialog, textvariable=entry_vars[i], values=connection_types)
            type_combo.grid(row=i, column=1, padx=5, pady=5, sticky=(tk.W, tk.E))
            entries[label_text[:-1].lower()] = type_combo
        elif label_text == "Auth Type:":
            auth_combo = ttk.Combobox(dialog, textvariable=entry_vars[i], values=auth_types)
            auth_combo.grid(row=i, column=1, padx=5, pady=5, sticky=(tk.W, tk.E))
            auth_combo.bind("<<ComboboxSelected>>", lambda event: update_auth_fields(auth_combo.get()))
            entries[label_text[:-1].lower().replace(' ', '_')] = auth_combo
        else:
            entry = ttk.Entry(dialog, textvariable=entry_vars[i])
            entry.grid(row=i, column=1, padx=5, pady=5, sticky=(tk.W, tk.E))
            entries[label_text[:-1].lower().replace(' ', '_')] = entry
            if label_text == "Password:" or label_text == "Private Key File:":
                entry.config(show="") # Ensure these are visible initially for setup

    def update_auth_fields(auth_type):
        if auth_type == "Password":
            entries['username'].config(state=tk.NORMAL)
            entries['password'].config(state=tk.NORMAL, show="")
            entries['private_key_file'].config(state=tk.DISABLED, show="")
            entry_vars[6].set("") # Clear private key file
        elif auth_type == "Private Key":
            entries['username'].config(state=tk.NORMAL)
            entries['password'].config(state=tk.DISABLED, show="")
            entry_vars[5].set("") # Clear password
            entries['private_key_file'].config(state=tk.NORMAL, show="")
        else:
            # Default state when no auth type is selected or for other types
            entries['username'].config(state=tk.DISABLED)
            entries['password'].config(state=tk.DISABLED, show="")
            entries['private_key_file'].config(state=tk.DISABLED, show="")
            entry_vars[4].set("")
            entry_vars[5].set("")
            entry_vars[6].set("")

    # Initialize the auth fields based on the initial value of the combobox
    if 'auth_type' in entries:
        update_auth_fields(entries['auth_type'].get())
    else:
        update_auth_fields(None) # Initialize to disabled if no selection

    def save_connection(): # Inner save_connection (command for the button)
        label = entry_vars[0].get()
        conn_type = entry_vars[1].get()
        host = entry_vars[2].get()
        auth_type = entry_vars[3].get()
        username = entry_vars[4].get()
        password = entry_vars[5].get()
        key_file = entry_vars[6].get()

        if not label or not conn_type or not host:
            messagebox.showerror("Error", "Label, Type, and Host are required.")
            return

        unique_id = os.urandom(8).hex()
        connection_data = {
            'label': label,
            'type': conn_type,
            'host': host,
            'auth.type': auth_type,
            'auth.username': username,
            'auth.password': password,
            'auth.key_file': key_file
        }
        connections.save_connection(unique_id, connection_data) # Call the module function
        tree.insert(root_node, tk.END, text=label, values=(unique_id,))
        dialog.destroy()

    save_button = ttk.Button(dialog, text="Save", command=save_connection)
    save_button.grid(row=len(labels), column=0, columnspan=2, padx=5, pady=10)

    dialog.transient(tree)
    dialog.grab_set()
    tree.wait_window(dialog)

def remove_selected_connection(tree, root_node, connections_data):
    selected_item = tree.selection()
    if not selected_item:
        messagebox.showinfo("Info", "Please select a connection to remove.")
        return

    item_text = tree.item(selected_item[0], 'text')
    unique_id = tree.item(selected_item[0], 'values')[0]

    if unique_id:
        filepath = os.path.join(CONNECTION_FILES_DIR, f"{unique_id}.gemTerm")
        try:
            os.remove(filepath)
            del connections_data[unique_id]
            tree.delete(selected_item[0])
        except FileNotFoundError:
            messagebox.showerror("Error", f"Connection file not found: {filepath}")
        except Exception as e:
            messagebox.showerror("Error", f"Error removing connection: {e}")