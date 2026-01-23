import os
import subprocess
import sys

def build():
    print("--- Starting Titanium Elite Build Sequence ---")

    # Check for PyInstaller
    try:
        import PyInstaller
    except ImportError:
        print("Error: PyInstaller not found. Install it with: pip install pyinstaller")
        return

    # Helper to clean previous builds
    if os.path.exists("dist"):
        print("Cleaning previous builds...")
        import shutil
        shutil.rmtree("build", ignore_errors=True)
        shutil.rmtree("dist", ignore_errors=True)

    # Get CustomTkinter path for data inclusion
    import customtkinter
    ctk_path = os.path.dirname(customtkinter.__file__)

    # Separator for --add-data
    sep = ";" if sys.platform == "win32" else ":"

    cmd = [
        "pyinstaller",
        "--noconfirm",
        "--onedir", # Changed from --onefile to --onedir for instant startup (no unpacking)
        "--windowed",
        "--name", "InvoiceScanner-Titanium",
        "--clean",

        # Explicitly add CustomTkinter data
        f"--add-data={ctk_path}{sep}customtkinter",

        # Hidden imports often missed by analysis
        "--hidden-import", "customtkinter",
        "--hidden-import", "PIL",
        "--hidden-import", "easyocr",
        "--hidden-import", "openai",
        "--hidden-import", "sklearn.utils._typedefs", # Common EasyOCR/scikit-image issue
        "--hidden-import", "sklearn.neighbors._partition_nodes",

        # Collect data for EasyOCR if needed (basic models)
        # Note: Heavy models might need manual copy, this is a basic config

        "project.py"
    ]

    print(f"Executing: {' '.join(cmd)}")
    subprocess.run(cmd)

    print("\n--- Build Complete! ---")
    print(f"Check the 'dist' folder for your executable: InvoiceScanner-Titanium")

if __name__ == "__main__":
    build()
