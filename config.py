# config.py
import json
import os
import tkinter as tk
from tkinter import ttk
from tkinter import font as tkFont

CONFIG_DIR = os.path.expanduser("~/.config/gemTerm")
CONFIG_FILE = os.path.join(CONFIG_DIR, "gemterm_config.json")

def _ensure_config_dir_exists():
    if not os.path.exists(CONFIG_DIR):
        os.makedirs(CONFIG_DIR)

def load_config():
    _ensure_config_dir_exists()
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                print("Warning: Error decoding config file. Using defaults.")
                return {"window_size": "800x600", "default_font": ["Monospace", 10]}
    return {"window_size": "800x600", "default_font": ["Monospace", 10]}

def save_config(config_data):
    _ensure_config_dir_exists()
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config_data, f, indent=4)

def get_window_size():
    return load_config().get("window_size", "800x600")

def save_window_size(width, height):
    config_data = load_config()
    config_data["window_size"] = f"{width}x{height}"
    save_config(config_data)

def get_default_font():
    return load_config().get("default_font", ["Monospace", 10])

def save_default_font(font_tuple):
    config_data = load_config()
    config_data["default_font"] = list(font_tuple)
    save_config(config_data)

def open_settings(root):
    """Opens the settings window."""
    settings_window = tk.Toplevel(root)
    settings_window.title("gemTerm Settings")

    # Font Selection
    font_label = ttk.Label(settings_window, text="Default Font:")
    font_label.grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)

    font_families = sorted(tkFont.families())
    font_family_var = tk.StringVar(settings_window)
    current_font = get_default_font()
    font_family_var.set(current_font[0]) # Set initial value

    font_family_dropdown = ttk.Combobox(settings_window, textvariable=font_family_var, values=font_families)
    font_family_dropdown.grid(row=0, column=1, padx=5, pady=5, sticky=(tk.W, tk.E))

    size_label = ttk.Label(settings_window, text="Size:")
    size_label.grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)

    font_sizes = [8, 9, 10, 11, 12, 14, 16]
    font_size_var = tk.IntVar(settings_window)
    font_size_var.set(current_font[1]) # Set initial value

    font_size_dropdown = ttk.Combobox(settings_window, textvariable=font_size_var, values=font_sizes, width=5)
    font_size_dropdown.grid(row=1, column=1, padx=5, pady=5, sticky=tk.W)

    def apply_font():
        selected_family = font_family_var.get()
        selected_size = font_size_var.get()
        new_font = (selected_family, selected_size)
        save_default_font(new_font)
        if hasattr(root, 'default_font'):
            root.default_font.configure(family=selected_family, size=selected_size)
        print(f"Default font set to: {new_font}") # Placeholder for applying font to UI

    apply_button = ttk.Button(settings_window, text="Apply", command=apply_font)
    apply_button.grid(row=2, column=0, columnspan=2, padx=5, pady=10)