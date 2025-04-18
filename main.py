# main.py
import tkinter as tk
from tkinter import ttk
from tkinter import font as tkFont
from tkinter import simpledialog
from tkinter import messagebox
import subprocess
import platform
import time
from PIL import Image, ImageTk
import os
import connections  # Import the connections module
import config  # Import the config module

class TabbedInterface(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("gemTerm")

        # Load initial window size from config
        initial_size = config.get_window_size()
        self.geometry(initial_size)

        style = ttk.Style(self)
        style.theme_use('clam')

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
            command=lambda: connections.add_new_connection(self.connections_tree, self.connections_root, self.connections_data))
        self.add_host_button.pack(side=tk.LEFT)

        # Button to remove selected connection (-)
        self.remove_host_button = ttk.Button(self.button_frame, text="-", width=2,
            command=lambda: connections.remove_selected_connection(self.connections_tree, self.connections_root, self.connections_data))
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
            # Store a dictionary containing both the frame and the unique_id
            self.tab_content_frames[content_frame] = {'unique_id': unique_id, 'tab_name': tab_name}

            xterm_title = f"{unique_id}"
            try:
                font_family = self.default_font['family']
                font_size = self.default_font['size']
                process = subprocess.Popen(["xterm", "-xrm", "XTerm.vt100.allowTitleOps: false", "-T", xterm_title, "-fa", font_family, "-fs", str(font_size)])
                pid = process.pid
                self.xterm_processes[unique_id] = process # Use unique_id as key here as well?

                def reparent_and_send_command(tab):
                    tab_info = self.tab_content_frames.get(tab)
                    if tab_info:
                        current_unique_id = tab_info['unique_id']
                        content_frame_id = str(tab.winfo_id())
                        try:
                            time.sleep(0.2)  # Give xterm a moment to open
                            output = subprocess.check_output(["xdotool", "search", "--name", f"^{current_unique_id}$"], text=True)
                            window_ids = output.strip().split('\n')
                            if window_ids:
                                xterm_wid = window_ids[0]
                                subprocess.run(["xdotool", "windowreparent", xterm_wid, content_frame_id])

                                # Force resize after a small delay to ensure it's reparented
                                self.after(250, lambda current_tab=tab: self.force_xterm_resize(current_tab))

                                # Send the command to the xterm window
                                subprocess.run(["xdotool", "type", command_to_run])
                                subprocess.run(["xdotool", "key", "Return"])

                                self.monitor_xterm_process(current_unique_id, process) # Use unique_id for monitoring
                            else:
                                print(f"Warning: Could not find xterm window with title: {current_unique_id} to reparent or send command.")
                        except FileNotFoundError:
                            print("Warning: xdotool not found. Reparenting and command sending might not work.")
                        except subprocess.CalledProcessError as e:
                            print(f"Warning: xdotool failed: {e}")
                    else:
                        print(f"Warning: Could not find tab info for {tab}")

                self.after(250, lambda current_tab=content_frame: reparent_and_send_command(current_tab))
                content_frame.bind("<Configure>", lambda event, current_tab=content_frame: self.on_tab_resize(current_tab, event))

            except FileNotFoundError:
                tkinter.messagebox.showerror("Error", "xterm not found. Please ensure it is installed.")
                self.notebook.forget(content_frame)
                del self.xterm_processes[unique_id] # Use unique_id for deletion
                del self.tab_content_frames[content_frame] # Use frame as key
        elif platform.system() == "Windows":
            tkinter.messagebox.showerror("Unsupported Platform", "Launching external terminals is primarily for Linux.")
        elif platform.system() == "Darwin":  # macOS
            tkinter.messagebox.showerror("Unsupported Platform", "Launching external terminals is primarily for Linux.")
        else:
            tkinter.messagebox.showerror("Unsupported Platform", f"Launching external terminals is not supported on {platform.system()}.")

    def get_xterm_title(self, tab_frame):
        tab_info = self.tab_content_frames.get(tab_frame)
        if tab_info:
            return tab_info['unique_id']
        return None

    def close_tab(self, tab_to_close):
        tab_info = self.tab_content_frames.get(tab_to_close)
        if tab_info:
            unique_id = tab_info['unique_id']
            if unique_id in self.xterm_processes:
                process = self.xterm_processes[unique_id]
                print(f"Attempting to kill process: {process}") # Debug print
                try:
                    subprocess.run(["kill", "-15", str(process.pid)])
                    time.sleep(0.1)
                    subprocess.run(["kill", "-9", str(process.pid)])
                except FileNotFoundError:
                    pass
                except subprocess.CalledProcessError:
                    pass
                del self.xterm_processes[unique_id]
            self.notebook.forget(tab_to_close)
            del self.tab_content_frames[tab_to_close]

    def monitor_xterm_process(self, tab_name, process):
        self.after(100, self._check_process, tab_name, process)

    def _check_process(self, tab_name, process):
        if process.poll() is not None:
            # Process has finished
            if tab_name in self.tab_content_frames:
                self.notebook.forget(self.tab_content_frames[tab_name])
                del self.tab_content_frames[tab_name]
                if tab_name in self.xterm_processes:
                    del self.xterm_processes[tab_name]
            print(f"XTerm for tab '{tab_name}' has exited.")
        else:
            # Process is still running, check again after 100ms
            self.after(100, self._check_process, tab_name, process)

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
                        tk.messagebox.showinfo("Info", f"Connection type '{connection_info.get('type')}' not yet supported for {selected_item_label}")

                except FileNotFoundError:
                    tk.messagebox.showerror("Error", f"Connection file not found for {selected_item_label}")
                except Exception as e:
                    tk.messagebox.showerror("Error", f"Error reading connection file for {selected_item_label}: {e}")

    def on_tab_resize(self, tab_frame, event):
        if platform.system() == "Linux":
            tab_info = self.tab_content_frames.get(tab_frame)
            if tab_info:
                unique_id = tab_info['unique_id']
                try:
                    tab_width = event.width
                    tab_height = event.height
                    output = subprocess.check_output(["xdotool", "search", "--name", f"^{unique_id}$"], text=True)
                    window_ids = output.strip().split('\n')
                    if window_ids:
                        xterm_wid = window_ids[0]
                        subprocess.run(["xdotool", "windowsize", xterm_wid, tab_width, tab_height])
                except FileNotFoundError:
                    print("Warning: xdotool not found. Resizing might not work.")
                except subprocess.CalledProcessError as e:
                    print(f"Warning: xdotool failed to resize window: {e}")

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

if __name__ == "__main__":
    app = TabbedInterface()
    app.mainloop()