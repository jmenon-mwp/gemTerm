# main.py
import tkinter as tk
from tkinter import ttk
from tkinter import font as tkFont
import subprocess
import platform
import tkinter.messagebox
import time
from tkinter import simpledialog
import connections  # Import the connections module
import config  # Import the config module
from PIL import Image, ImageTk
import os

class TabbedInterface(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("gemTerm")

        # Load initial window size from config
        initial_size = config.get_window_size()
        self.geometry(initial_size)

        # Apply the 'clam' theme directly
        style = ttk.Style(self)
        style.theme_use('clam')
        print("Using theme: clam")

        # Left Frame for the Buttons and Treeview
        self.left_frame = ttk.Frame(self)
        self.left_frame.pack(side=tk.LEFT, fill=tk.Y)

        # Frame to hold the add and remove buttons horizontally
        self.button_frame = ttk.Frame(self.left_frame)
        self.button_frame.pack(pady=5, padx=5, fill=tk.X)

        # Initialize connections dictionary from config
        self.connections_data = connections.load_connections()

        # Button to add new connection (+)
        self.add_host_button = ttk.Button(self.button_frame, text="+", width=2,
                                            command=lambda: connections.add_new_connection(
                                                self.connections_tree, self.connections_root, self.connections_data
                                            ))
        self.add_host_button.pack(side=tk.LEFT)

        # Button to remove selected connection (-)
        self.remove_host_button = ttk.Button(self.button_frame, text="-", width=2,
                                               command=lambda: connections.remove_selected_connection(
                                                   self.connections_tree, self.connections_root, self.connections_data
                                               ))
        self.remove_host_button.pack(side=tk.LEFT, padx=2)

        # Settings Button with Gear Icon
        try:
            image_path = os.path.join("images", "gear_icon.png")
            gear_image = Image.open(image_path)
            gear_photo = ImageTk.PhotoImage(gear_image.resize((16, 16)))
            self.settings_icon = gear_photo
            self.settings_button = ttk.Button(self.button_frame, image=self.settings_icon, command=self.open_settings)
            self.settings_button.pack(side=tk.LEFT, padx=2)
        except FileNotFoundError:
            print("Warning: 'images/gear_icon.png' not found. Settings button will have text.")
            self.settings_button = ttk.Button(self.button_frame, text="⚙", width=2, command=self.open_settings)
            self.settings_button.pack(side=tk.LEFT, padx=2)
        except Exception as e:
            print(f"Warning: Error loading gear icon: {e}")
            self.settings_button = ttk.Button(self.button_frame, text="⚙", width=2, command=self.open_settings)
            self.settings_button.pack(side=tk.LEFT, padx=2)

        # Treeview for connections
        self.connections_tree = ttk.Treeview(self.left_frame, columns=('unique_id',))
        self.connections_tree.heading('#0', text='Connections')
        self.connections_tree.heading('unique_id', text='Unique ID')
        self.connections_tree.column('unique_id', width=0, stretch=tk.NO) # Hide the unique ID column
        self.connections_tree.pack(fill=tk.BOTH, expand=True)

        # Add the top-level "Connections" item
        self.connections_root = self.connections_tree.insert("", tk.END, text="Connections")

        # Populate the treeview with loaded connections
        for unique_id, data in self.connections_data.items():
            self.connections_tree.insert(self.connections_root, tk.END, text=data['label'], values=(unique_id,))

        self.connections_tree.bind("<Double-1>", self.on_treeview_doubleclick)

        # Right Frame (Notebook/Tabbed Interface)
        self.right_frame = ttk.Frame(self)
        self.right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        self.right_frame.grid_columnconfigure(0, weight=1)
        self.right_frame.grid_rowconfigure(0, weight=1)

        self.notebook = ttk.Notebook(self.right_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        self.xterm_processes = {}  # Dictionary to store xterm processes (tab_name: pid)
        self.tab_content_frames = {} # Dictionary to store the content frames of each tab

        # Bind the closing protocol to our on_closing method
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

        # Load the default font
        self.default_font = tkFont.Font(family=config.get_default_font()[0], size=config.get_default_font()[1])

    def open_settings(self):
        config.open_settings(self)

    def on_closing(self):
        """Saves the current window size before closing."""
        self.update()  # Ensure the window's geometry is up-to-date
        width = self.winfo_width()
        height = self.winfo_height()
        config.save_window_size(width, height)

        for pid in self.xterm_processes.values():
            try:
                subprocess.run(["kill", "-15", str(pid)]) # Try graceful termination
                time.sleep(0.1)
                subprocess.run(["kill", "-9", str(pid)])  # Force kill if needed
            except FileNotFoundError:
                pass
            except subprocess.CalledProcessError:
                pass
        self.destroy()

    def create_xterm_process(self, tab_name, command_to_run, unique_id):
        if platform.system() == "Linux":
            content_frame = ttk.Frame(self.notebook)
            content_frame.pack(fill=tk.BOTH, expand=True)
            content_frame.grid_columnconfigure(0, weight=1)
            content_frame.grid_rowconfigure(0, weight=1)
            self.notebook.add(content_frame, text=tab_name)
            self.notebook.select(content_frame)
            self.tab_content_frames[tab_name] = content_frame

            xterm_title = f"{unique_id}"
            try:
                font_family = self.default_font['family']
                font_size = self.default_font['size']
                process = subprocess.Popen(["xterm", "-T", xterm_title, "-fa", font_family, "-fs", str(font_size)])
                pid = process.pid
                self.xterm_processes[tab_name] = process

                def reparent_and_send_command(tab):
                    content_frame_id = str(self.tab_content_frames[tab].winfo_id())
                    try:
                        time.sleep(0.2)  # Give xterm a moment to open
                        output = subprocess.check_output(["xdotool", "search", "--name", f"^{xterm_title}$"], text=True)
                        window_ids = output.strip().split('\n')
                        if window_ids:
                            xterm_wid = window_ids[0]
                            subprocess.run(["xdotool", "windowreparent", xterm_wid, content_frame_id])
                            self.force_xterm_resize(tab)

                            # Send the command to the xterm window
                            subprocess.run(["xdotool", "type", "--window", xterm_wid, command_to_run])
                            subprocess.run(["xdotool", "key", "--window", xterm_wid, "Return"])

                            self.monitor_xterm_process(tab, process)
                        else:
                            print(f"Warning: Could not find xterm window with title: {xterm_title} to reparent or send command.")
                    except FileNotFoundError:
                        print("Warning: xdotool not found. Reparenting and command sending might not work.")
                    except subprocess.CalledProcessError as e:
                        print(f"Warning: xdotool failed: {e}")

                self.after(250, lambda current_tab_name=tab_name: reparent_and_send_command(current_tab_name))
                content_frame.bind("<Configure>", lambda event, current_tab_name=tab_name: self.on_tab_resize(current_tab_name))

            except FileNotFoundError:
                tkinter.messagebox.showerror("Error", "xterm not found. Please ensure it is installed.")
                self.notebook.forget(content_frame)
                del self.xterm_processes[tab_name]
                del self.tab_content_frames[tab_name]
        elif platform.system() == "Windows":
            tkinter.messagebox.showerror("Unsupported Platform", "Launching external terminals is primarily for Linux.")
        elif platform.system() == "Darwin":  # macOS
            tkinter.messagebox.showerror("Unsupported Platform", "Launching external terminals is primarily for Linux.")
        else:
            tkinter.messagebox.showerror("Unsupported Platform", f"Launching external terminals is not supported on {platform.system()}.")

    def monitor_xterm_process(self, tab_name, process):
        if tab_name in self.xterm_processes and self.xterm_processes[tab_name] == process:
            if process.poll() is not None:
                # xterm has exited
                if tab_name in self.tab_content_frames:
                    tab_to_close = self.tab_content_frames[tab_name]
                    self.notebook.forget(tab_to_close)
                    del self.tab_content_frames[tab_name]
                    del self.xterm_processes[tab_name]
            else:
                # Continue monitoring after 1 second
                self.after(1000, self.monitor_xterm_process, tab_name, process)

    def on_treeview_doubleclick(self, event):
        item_id = self.connections_tree.selection()
        if item_id:
            selected_item_label = self.connections_tree.item(item_id[0], 'text')
            unique_id = self.connections_tree.item(item_id[0], 'values')[0]

            if selected_item_label != "Connections" and unique_id:
                connection_file_path = os.path.join(connections.CONNECTION_FILES_DIR, f"{unique_id}.gemTerm")
                connection_info = {}
                try:
                    with open(connection_file_path, 'r') as f:
                        for line in f:
                            if '=' in line:
                                key, value = line.strip().split('=', 1)
                                connection_info[key] = value

                    if connection_info.get('type') == "SSH":
                        user_host = connection_info.get('host')
                        username = connection_info.get('auth.username')
                        password = connection_info.get('auth.password')
                        key_file = connection_info.get('auth.key_file')
                        auth_type = connection_info.get('auth.type')

                        ssh_command = "ssh -o StrictHostKeyChecking=no "
                        if username:
                            ssh_command += f"{username}@"
                        ssh_command += f"{user_host} "

                        if auth_type == "Private Key" and key_file:
                            ssh_command += f"-i \"{key_file}\" "
                        # We will NOT automatically append the password here for security reasons.
                        # The user will be prompted in the xterm if needed (password-based auth without keys).
                        # If you absolutely need to send the password, you would do:
                        # ssh_command += f"&& echo \"{password}\" | sshpass -i - ssh -o StrictHostKeyChecking=no {target}"
                        # BUT THIS IS DISCOURAGED DUE TO SECURITY RISKS.

                        self.create_xterm_process(selected_item_label, ssh_command.strip(), unique_id)

                    elif connection_info.get('type') == "RDP":
                        host = connection_info.get('host')
                        rdp_command = f"rdesktop {host}"
                        self.create_xterm_process(selected_item_label, rdp_command, unique_id)
                    elif connection_info.get('type') == "VNC":
                        host = connection_info.get('host')
                        vnc_command = f"vncviewer {host}"
                        self.create_xterm_process(selected_item_label, vnc_command, unique_id)
                    else:
                        tkinter.messagebox.showinfo("Info", f"Connection type '{connection_info.get('type')}' not yet supported for {selected_item_label}")

                except FileNotFoundError:
                    tkinter.messagebox.showerror("Error", f"Connection file not found for {selected_item_label}")
                except Exception as e:
                    tkinter.messagebox.showerror("Error", f"Error reading connection file for {selected_item_label}: {e}")

    def on_tab_resize(self, tab_name):
        self.force_xterm_resize(tab_name)

    def force_xterm_resize(self, tab_name):
        if tab_name in self.xterm_processes and tab_name in self.tab_content_frames:
            process = self.xterm_processes[tab_name]
            content_frame = self.tab_content_frames[tab_name]
            if content_frame.winfo_exists():
                width = content_frame.winfo_width()
                height = content_frame.winfo_height()
                if width > 1 and height > 1:  # Ensure dimensions are valid
                    for attempt in range(2):  # Try twice
                        try:
                            output = subprocess.check_output(["xdotool", "search", "--name", f"^{self.get_xterm_title(tab_name)}$"], text=True)
                            window_ids = output.strip().split('\n')
                            if window_ids:
                                xterm_wid = window_ids[0]
                                subprocess.run(["xdotool", "windowsize", xterm_wid, str(width), str(height)])
                                return  # Exit if successful
                        except FileNotFoundError:
                            print("Warning: xdotool not found. Automatic xterm resizing might not work perfectly.")
                            return
                        except subprocess.CalledProcessError as e:
                            if attempt == 0:
                                time.sleep(0.1)  # Small delay before retry
                            else:
                                print(f"Warning: xdotool search failed after retries: {e}")
                                return

    def get_xterm_title(self, tab_name):
        return f"XTerm - {tab_name}"

if __name__ == "__main__":
    app = TabbedInterface()
    app.mainloop()