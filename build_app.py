import os
import subprocess
import sys
import shutil

def build():
    print("--- Starting Titanium Elite Build Sequence (Robust Mode) ---")

    # 1. Check for PyInstaller
    try:
        import PyInstaller
    except ImportError:
        print("Error: PyInstaller not found. Install it with: pip install pyinstaller")
        return

    # 2. Get CustomTkinter path for data inclusion
    import customtkinter
    ctk_path = os.path.dirname(customtkinter.__file__)

    # separator for pyinstaller is ; on windows and : on unix
    sep = ":" if sys.platform != "win32" else ";"

    # We include the entire customtkinter folder to get json/theme files
    # Syntax: source_path:destination_folder
    # On macOS/Linux destination should be 'customtkinter' relative to the bundle
    ctk_data = f"{ctk_path}{sep}customtkinter"

    cmd = [
        "pyinstaller",
        "--noconfirm",
        "--onedir",       # CHANGED: Use directory mode for MUCH faster launch
        "--windowed",
        "--name", "InvoiceScanner-Continuum",
        "--clean",
        "--add-data", ctk_data,
        # Including necessary packages
        "--hidden-import", "customtkinter",
        "--hidden-import", "PIL",
        "--hidden-import", "easyocr",
        "--hidden-import", "openai",
        "--hidden-import", "regex",
        "--hidden-import", "cv2",
        "--hidden-import", "requests",
        "project.py"
    ]

    print(f"Executing: {' '.join(cmd)}")
    subprocess.run(cmd)

    print("\n--- Build Complete! ---")
    print(f"Check the 'dist' folder for your executable.")
    print("TIP: If it doesn't open, try running 'dist/InvoiceScanner-Continuum' from the terminal to see error logs.")

if __name__ == "__main__":
    build()
