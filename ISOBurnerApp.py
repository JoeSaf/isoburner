import os
import subprocess
import tkinter as tk
from tkinter import ttk, simpledialog, filedialog, messagebox
from threading import Thread
import shutil
import tempfile

class ISOBurnerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("ISO Burner (Linux)")
        self.root.geometry("500x680")
        self.root.resizable(False, False)

        # Use ttk for a modern look
        self.style = ttk.Style()
        self.style.theme_use("clam")

        # Check for dependencies
        self.missing_deps = self.check_dependencies()
        
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
        
        # Dependencies Warning (if any)
        if self.missing_deps:
            deps_warning = tk.Label(root, text=f"Missing dependencies: {', '.join(self.missing_deps)}", 
                                   fg="red", font=("Arial", 10))
            deps_warning.pack(pady=2)

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
        self.iso_type_label = tk.Label(frame_iso, text="", fg="green")
        self.iso_type_label.pack(pady=2)

        # Burn Options
        frame_options = ttk.LabelFrame(root, text="3. Options", padding=10)
        frame_options.pack(fill="x", padx=10, pady=5)
        
        self.verify_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(frame_options, text="Verify after burning", variable=self.verify_var).pack(anchor="w")
        
        self.uefi_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(frame_options, text="Enable UEFI support (for Windows)", variable=self.uefi_var).pack(anchor="w")

        # Burn Button
        frame_burn = ttk.LabelFrame(root, text="4. Burn ISO", padding=10)
        frame_burn.pack(fill="x", padx=10, pady=5)

        self.burn_button = ttk.Button(frame_burn, text="Burn ISO", command=self.start_burning, style="TButton")
        self.burn_button.pack(pady=5)

        # Progress Bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(root, variable=self.progress_var, length=480, mode="determinate")
        self.progress_bar.pack(padx=10, pady=5)

        # Progress Output (Text Log)
        self.progress_text = tk.Text(root, height=10, width=60, wrap="word")
        self.progress_text.pack(pady=5)
        self.progress_text.config(state="disabled")

    def check_dependencies(self):
        """Check for required dependencies"""
        missing = []
        
        # Check for dd command
        if shutil.which("dd") is None:
            missing.append("dd")
            
        # Check for wimlib-imagex (needed for Windows ISOs)
        if shutil.which("wimlib-imagex") is None:
            missing.append("wimlib-imagex")
            
        # Check for NTFS utilities
        if shutil.which("mkfs.ntfs") is None:
            missing.append("ntfs-3g")
            
        return missing

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
            
            # Determine ISO type
            is_windows = self.is_windows_iso(file_path)
            if is_windows:
                self.iso_type_label.config(text="Detected: Windows Installation ISO", fg="green")
                
                # Warn if wimlib is missing
                if "wimlib-imagex" in self.missing_deps:
                    messagebox.showwarning("Missing Dependency", 
                                         "wimlib-imagex is required for Windows ISOs.\nPlease install it first.")
            else:
                self.iso_type_label.config(text="Detected: Standard ISO", fg="green")

    def get_usb_devices(self):
        devices = [f"/dev/{d}" for d in os.listdir("/dev/") if d.startswith("sd") and not d[-1].isdigit()]
        return devices if devices else ["No devices found"]

    def update_usb_devices(self):
        devices = self.get_usb_devices()
        self.device_dropdown["values"] = devices
        if devices:
            self.device_path.set(devices[0])

    def is_windows_iso(self, iso_path):
        """
        Improved Windows ISO detection using multiple methods:
        1. Look for Microsoft signature in ISO header
        2. Check for Windows boot files structure
        """
        try:
            # Method 1: Header check
            with open(iso_path, "rb") as f:
                data = f.read(8192)  # Read a larger chunk for better detection
                if b"Microsoft Corporation" in data or b"UDF" in data and b"BOOTMGR" in data:
                    return True
                    
            # Method 2: Mount and check content structure
            with tempfile.TemporaryDirectory() as temp_dir:
                try:
                    # Try to mount the ISO
                    mount_proc = subprocess.run(
                        ["mount", "-o", "loop,ro", iso_path, temp_dir],
                        stderr=subprocess.PIPE, stdout=subprocess.PIPE, timeout=5
                    )
                    
                    # Check for Windows-specific files
                    windows_indicators = [
                        "sources/install.wim", "sources/install.esd",
                        "bootmgr", "setup.exe"
                    ]
                    
                    for indicator in windows_indicators:
                        if os.path.exists(os.path.join(temp_dir, indicator)):
                            subprocess.run(["umount", temp_dir], stderr=subprocess.DEVNULL)
                            return True
                            
                    subprocess.run(["umount", temp_dir], stderr=subprocess.DEVNULL)
                except Exception:
                    # If mounting fails, ignore and continue with other methods
                    pass
                    
            # If neither method identifies as Windows, assume it's not
            return False
                
        except Exception as e:
            self.update_progress(f"Warning: Could not detect ISO type: {str(e)}")
            return False

    def start_burning(self):
        iso = self.iso_path.get()
        device = self.device_path.get()

        if not iso or device == "No devices found":
            messagebox.showerror("Error", "Please select a valid ISO and a USB drive.")
            return

        # Check if dependencies are missing
        if self.missing_deps:
            if messagebox.askyesno("Missing Dependencies", 
                                 f"The following dependencies are missing: {', '.join(self.missing_deps)}.\n\nContinue anyway?") is False:
                return

        confirm = messagebox.askyesno("Confirm", f"Write {iso} to {device}? This will erase all data on the USB drive!")
        if confirm:
            self.burn_button.config(state="disabled")
            self.progress_text.config(state="normal")
            self.progress_text.delete(1.0, tk.END)
            self.progress_text.insert(tk.END, "Burning started...\n")
            self.progress_text.config(state="disabled")
            self.progress_var.set(0)  # Reset progress bar

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

        is_windows = self.is_windows_iso(iso)
        enable_uefi = self.uefi_var.get()
        verify = self.verify_var.get()
        
        cmd = f"echo {password} | sudo -S "
        
        if is_windows:
            # First format the drive with NTFS
            self.update_progress("Formatting drive to NTFS...")
            format_cmd = cmd + f"mkfs.ntfs -f {device}"
            self.run_command(format_cmd, progress_weight=10)
            
            # Setup for UEFI if enabled
            if enable_uefi:
                self.update_progress("Setting up UEFI boot support...")
                uefi_cmd = cmd + f"parted {device} mklabel gpt mkpart primary fat32 1MiB 100MiB set 1 boot on"
                self.run_command(uefi_cmd, progress_weight=10)
                
                format_uefi_cmd = cmd + f"mkfs.fat -F32 {device}1"
                self.run_command(format_uefi_cmd, progress_weight=5)
            
            # Apply Windows image
            self.update_progress("Applying Windows image (this may take a while)...")
            wim_cmd = cmd + f"wimlib-imagex apply '{iso}' 1 {device}"
            self.run_command(wim_cmd, progress_weight=65)
        else:
            # Standard ISO burn with dd
            self.update_progress("Writing ISO to USB drive...")
            dd_cmd = cmd + f"dd if='{iso}' of='{device}' bs=4M status=progress && sync"
            self.run_command(dd_cmd, progress_weight=90)
        
        # Verify if requested
        if verify:
            self.update_progress("Verifying written data...")
            verify_cmd = cmd + f"cmp -n $(stat -c %s '{iso}') '{iso}' {device}"
            result = self.run_command(verify_cmd, progress_weight=10)
            
            if result == 0:
                self.update_progress("Verification successful! Data was written correctly.", success=True)
            else:
                self.update_progress("Verification failed! The written data does not match the ISO.", success=False)
        
        # Final sync to ensure all data is written
        sync_cmd = cmd + "sync"
        self.run_command(sync_cmd)
        
        self.progress_var.set(100)  # Ensure progress bar shows 100%
        self.burn_button.config(state="normal")

    def burn_iso(self, iso, device):
        is_windows = self.is_windows_iso(iso)
        enable_uefi = self.uefi_var.get()
        verify = self.verify_var.get()
        
        if is_windows:
            # Format USB to NTFS before applying Windows ISO
            self.update_progress("Formatting drive to NTFS...")
            subprocess.run(["mkfs.ntfs", "-f", device], 
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            self.progress_var.set(10)
            
            # Setup for UEFI if enabled
            if enable_uefi:
                self.update_progress("Setting up UEFI boot support...")
                subprocess.run(["parted", device, "mklabel", "gpt", "mkpart", "primary", 
                              "fat32", "1MiB", "100MiB", "set", "1", "boot", "on"],
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                self.progress_var.set(20)
                
                subprocess.run(["mkfs.fat", "-F32", f"{device}1"],
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                self.progress_var.set(25)
            
            # Apply Windows image
            self.update_progress("Applying Windows image (this may take a while)...")
            cmd = f"wimlib-imagex apply '{iso}' 1 {device}"
            result = self.run_command(cmd, progress_weight=65)
        else:
            # Standard ISO burn with dd
            self.update_progress("Writing ISO to USB drive...")
            cmd = f"dd if='{iso}' of='{device}' bs=4M status=progress && sync"
            result = self.run_command(cmd, progress_weight=90)
        
        # Verify if requested
        if verify and result == 0:
            self.update_progress("Verifying written data...")
            verify_cmd = f"cmp -n $(stat -c %s '{iso}') '{iso}' {device}"
            result = subprocess.run(verify_cmd, shell=True).returncode
            
            if result == 0:
                self.update_progress("Verification successful! Data was written correctly.", success=True)
            else:
                self.update_progress("Verification failed! The written data does not match the ISO.", success=False)
            
            self.progress_var.set(100)
        
        # Final success/failure message
        if result == 0:
            self.update_progress("ISO burned successfully!", success=True)
            messagebox.showinfo("Success", "ISO burned successfully!")
        else:
            self.update_progress("Error: Failed to burn ISO.", success=False)
            messagebox.showerror("Error", "Failed to burn ISO.")
        
        self.burn_button.config(state="normal")

    def run_command(self, cmd, progress_weight=0):
        """Run a command and update progress. Returns the command's return code."""
        process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
        
        current_progress = self.progress_var.get()
        target_progress = current_progress + progress_weight
        
        for line in process.stdout:
            self.update_progress(line.strip())
            
            # Try to update progress bar based on dd output
            if "bytes" in line and "copied" in line:
                try:
                    percentage = float(line.split("%")[0].split(" ")[-1])
                    # Scale the percentage to fit within our progress weight
                    scaled_progress = current_progress + (percentage / 100 * progress_weight)
                    self.progress_var.set(min(scaled_progress, target_progress))
                except (ValueError, IndexError):
                    pass
        
        process.wait()
        self.progress_var.set(target_progress)  # Ensure we reach target progress
        return process.returncode

    def update_progress(self, text, success=False):
        """Update the text progress log only."""
        self.progress_text.config(state="normal")
        if success:
            self.progress_text.insert(tk.END, text + "\n", "success")
            self.progress_text.tag_configure("success", foreground="green")
        elif "error" in text.lower() or "failed" in text.lower():
            self.progress_text.insert(tk.END, text + "\n", "error")
            self.progress_text.tag_configure("error", foreground="red")
        else:
            self.progress_text.insert(tk.END, text + "\n")
        self.progress_text.yview(tk.END)
        self.progress_text.config(state="disabled")
        self.root.update_idletasks()  # Force UI update

# Run the application
if __name__ == "__main__":
    root = tk.Tk()
    app = ISOBurnerApp(root)
    root.mainloop()