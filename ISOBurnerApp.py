import os
import subprocess
import tkinter as tk
from tkinter import ttk, simpledialog, filedialog, messagebox
from threading import Thread

class ISOBurnerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("ISO Burner (Linux Only)")
        self.root.geometry("500x500")
        self.root.resizable(False, False)

        # Use ttk for a modern look
        self.style = ttk.Style()
        self.style.theme_use("clam")
        
        # Top Frame (Title & Close Button)
        top_frame = tk.Frame(root, bg="black", height=40)
        top_frame.pack(fill="x")

        title_label = tk.Label(top_frame, text="ISO Burner", fg="white", bg="black", font=("Arial", 14, "bold"))
        title_label.pack(side="left", padx=10, pady=5)

        close_button = tk.Button(top_frame, text="X", command=self.close_app, fg="white", bg="red", font=("Arial", 10, "bold"))
        close_button.pack(side="right", padx=10)

        # Status Label (Root Check)
        self.status_label = tk.Label(root, text="", font=("Arial", 10, "bold"))
        self.status_label.pack(pady=5)
        self.check_root_status()

        # USB Selection
        frame_usb = ttk.LabelFrame(root, text="1. Choose USB Device", padding=10)
        frame_usb.pack(fill="x", padx=10, pady=5)
        
        self.device_path = tk.StringVar()
        self.device_dropdown = ttk.Combobox(frame_usb, textvariable=self.device_path, state="readonly")
        self.device_dropdown.pack(fill="x", padx=5, pady=2)
        ttk.Button(frame_usb, text="Rescan Devices", command=self.update_usb_devices).pack(pady=5)
        self.update_usb_devices()

        # ISO Selection
        frame_iso = ttk.LabelFrame(root, text="2. Choose ISO File", padding=10)
        frame_iso.pack(fill="x", padx=10, pady=5)

        self.iso_path = tk.StringVar()
        ttk.Button(frame_iso, text="Browse ISO", command=self.select_iso).pack(pady=2)
        self.iso_label = tk.Label(frame_iso, text="No file selected", fg="blue")
        self.iso_label.pack(pady=5)

        # Burn Button
        frame_burn = ttk.LabelFrame(root, text="3. Burn ISO", padding=10)
        frame_burn.pack(fill="x", padx=10, pady=5)

        self.burn_button = ttk.Button(frame_burn, text="Burn ISO", command=self.start_burning, style="TButton")
        self.burn_button.pack(pady=5)

        # Progress Output (Text Log)
        self.progress_text = tk.Text(root, height=10, width=60, wrap="word")
        self.progress_text.pack(pady=5)
        self.progress_text.config(state="disabled")

    def check_root_status(self):
        if os.geteuid() == 0:
            self.status_label.config(text="Running as root", fg="red")
        else:
            self.status_label.config(text="Not running as root", fg="blue")

    def close_app(self):
        self.root.quit()
        self.root.destroy()

    def select_iso(self):
        file_path = filedialog.askopenfilename(filetypes=[("ISO Files", "*.iso")])
        if file_path:
            self.iso_path.set(file_path)
            self.iso_label.config(text=f"Selected: {os.path.basename(file_path)}")

    def get_usb_devices(self):
        devices = [f"/dev/{d}" for d in os.listdir("/dev/") if d.startswith("sd") and not d[-1].isdigit()]
        return devices if devices else ["No devices found"]

    def update_usb_devices(self):
        devices = self.get_usb_devices()
        self.device_dropdown["values"] = devices
        if devices:
            self.device_path.set(devices[0])

    def start_burning(self):
        iso = self.iso_path.get()
        device = self.device_path.get()

        if not iso or device == "No devices found":
            messagebox.showerror("Error", "Please select a valid ISO and a USB drive.")
            return

        confirm = messagebox.askyesno("Confirm", f"Write {iso} to {device}? This will erase all data on the USB drive!")
        if confirm:
            self.burn_button.config(state="disabled")
            self.progress_text.config(state="normal")
            self.progress_text.delete(1.0, tk.END)
            self.progress_text.insert(tk.END, "Burning started...\n")
            self.progress_text.config(state="disabled")

            if os.geteuid() == 0:
                Thread(target=self.burn_iso, args=(iso, device)).start()
            else:
                self.request_sudo_and_burn(iso, device)

    def request_sudo_and_burn(self, iso, device):
        password = simpledialog.askstring("Root Password", "Enter root password:", show="*")
        if not password:
            messagebox.showerror("Error", "No password entered. Burning cancelled.")
            self.burn_button.config(state="normal")
            return

        cmd = f"echo {password} | sudo -S dd if='{iso}' of='{device}' bs=4M status=progress && sync"
        Thread(target=self.run_command, args=(cmd,)).start()

    def burn_iso(self, iso, device):
        cmd = f"dd if='{iso}' of='{device}' bs=4M status=progress && sync"
        Thread(target=self.run_command, args=(cmd,)).start()

    def run_command(self, cmd):
        process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)

        for line in process.stdout:
            self.update_progress(line.strip())

        process.wait()

        if process.returncode == 0:
            self.update_progress("ISO burned successfully!", success=True)
            messagebox.showinfo("Success", "ISO burned successfully!")
        else:
            self.update_progress("Error: Failed to burn ISO.", success=False)
            messagebox.showerror("Error", "Failed to burn ISO.")

        self.burn_button.config(state="normal")

    def update_progress(self, text, success=False):
        """Update the text progress log only."""
        self.progress_text.config(state="normal")
        self.progress_text.insert(tk.END, text + "\n")
        self.progress_text.yview(tk.END)
        self.progress_text.config(state="disabled")

# Run the application
if __name__ == "__main__":
    root = tk.Tk()
    app = ISOBurnerApp(root)
    root.mainloop()
