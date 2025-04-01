
### **Creating a Release for ISO Burner (Linux - AppImage)**
This guide explains how to package `ISOBurnerApp.py` into an AppImage and create a GitHub release.

---

## **1️⃣ Install Dependencies**
Ensure you have the required tools installed:

```sh
sudo pacman -S pyinstaller github-cli
```

If you don’t have `yay`, install it or use another AUR helper.

---

## **2️⃣ Build the Executable**
Use PyInstaller to generate a standalone binary:

```sh
pyinstaller --onefile --noconsole ISOBurnerApp.py
```

- `--onefile`: Packages everything into a single file.
- `--noconsole`: Prevents a terminal window from opening.

After this, your binary will be in `dist/ISOBurnerApp`.

---