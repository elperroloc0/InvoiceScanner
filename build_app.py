import os
import subprocess
import sys

def build():
    print("--- Starting Titanium Elite Build Sequence ---")

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

    # Construct the PyInstaller command
    # Using python -m PyInstaller ensures we use the same environment's PyInstaller
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--onedir",
        "--windowed",
        "--name", "InvoiceScanner-Titanium",
        "--clean",

        # Explicitly add CustomTkinter data
        f"--add-data={ctk_path}{sep}customtkinter",

        # Hidden imports - Exhaustive list for stability
        "--hidden-import", "customtkinter",
        "--hidden-import", "PIL",
        "--hidden-import", "easyocr",
        "--hidden-import", "scipy.special",
        "--hidden-import", "scipy.spatial.transform._rotation_groups",
        "--hidden-import", "openai",
        "--hidden-import", "cv2",
        "--hidden-import", "sklearn.utils._typedefs",
        "--hidden-import", "sklearn.neighbors._partition_nodes",
        "--hidden-import", "regex",
        "--hidden-import", "certifi",
        "--hidden-import", "ssl",

        "project.py"
    ]

    print(f"Executing: {' '.join(cmd)}")
    result = subprocess.run(cmd)

    if result.returncode != 0:
        print("Error: Build failed!")
        sys.exit(result.returncode)

    # --- Automatic Zipping for Distribution ---
    print("\nCreating distribution archive...")
    import shutil
    archive_name = f"InvoiceScanner-Titanium-{sys.platform}"

    if sys.platform == "darwin":
        # macOS: Use system 'zip' to preserve symlinks and permissions (Critical for .app bundles)
        try:
            # We want to zip 'InvoiceScanner-Titanium.app' inside 'dist'
            # Resulting zip should contain the .app folder at root level
            cwd = os.getcwd()
            os.chdir("dist")
            zip_cmd = ["zip", "-r", "-y", f"../{archive_name}.zip", "InvoiceScanner-Titanium.app"]
            print(f"Running system zip: {' '.join(zip_cmd)}")
            subprocess.run(zip_cmd, check=True)
            os.chdir(cwd)
        except Exception as e:
            print(f"Error zipping on macOS: {e}")
            print("Fallback: Manual zip required if this fails.")

    elif sys.platform == "win32":
        # Windows: specific zip for folder
        shutil.make_archive(archive_name, 'zip', "dist/InvoiceScanner-Titanium")
    else:
        # Linux/Other: Generic fallback
        shutil.make_archive(archive_name, 'zip', "dist")

    print(f"\n--- Build Complete! ---")
    print(f"Distribution archive: {archive_name}.zip")

if __name__ == "__main__":
    build()
