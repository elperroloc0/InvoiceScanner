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

    # --- Automatic Zipping for Distribution ---
    print("\nCreating distribution archive...")
    import shutil
    archive_name = f"InvoiceScanner-Titanium-{sys.platform}"

    # We zip the contents of the dist folder
    if sys.platform == "win32":
        # Windows: Zip the folder containing the .exe
        shutil.make_archive(archive_name, 'zip', "dist/InvoiceScanner-Titanium")
    elif sys.platform == "darwin":
        # macOS: Zip the .app bundle
        app_path = "dist/InvoiceScanner-Titanium.app"
        if os.path.exists(app_path):
            shutil.make_archive(archive_name, 'zip', "dist", "InvoiceScanner-Titanium.app")
        else:
            # Fallback for onedir without .app suffix
            shutil.make_archive(archive_name, 'zip', "dist/InvoiceScanner-Titanium")
    else:
        # Generic fallback
        shutil.make_archive(archive_name, 'zip', "dist")

    print(f"\n--- Build Complete! ---")
    print(f"Executable directory: dist/InvoiceScanner-Titanium")
    print(f"Distribution archive: {archive_name}.zip")

if __name__ == "__main__":
    build()
