import logging
import os
import platform
import ssl
import threading
import webbrowser
from pathlib import Path
from tkinter import filedialog, messagebox

import certifi

import customtkinter as ctk
import requests
from PIL import Image

# Import scanner logic
from scanner.manager import ScannerManager
from scanner.ocr import preprocess_receipt
from scanner.storage import save_to_file


# --- Platform-Specific Data Directory ---
def get_app_data_dir():
    """Returns the appropriate writable directory for settings/data."""
    home = Path.home()
    if platform.system() == "Windows":
        return home / "AppData" / "Roaming" / "InvoiceScanner"
    elif platform.system() == "Darwin":
        return home / "Library" / "Application Support" / "InvoiceScanner"
    else:
        return home / ".local" / "share" / "InvoiceScanner"

APP_DATA_DIR = get_app_data_dir()
APP_DATA_DIR.mkdir(parents=True, exist_ok=True)
ENV_FILE = APP_DATA_DIR / ".env"

# --- SSL Certificate Fix for macOS Bundles ---
if platform.system() == "Darwin":
    os.environ["SSL_CERT_FILE"] = certifi.where()
    try:
        ssl_context = ssl.create_default_context(cafile=certifi.where())
        ssl._create_default_https_context = lambda: ssl_context
    except Exception as e:
        logging.warning(f"Failed to set SSL context: {e}")

logger = logging.getLogger("ContinuumUI")

# Set appearance mode and theme
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")


class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.version = "2.0.4" # Current internal version
        self.title(f"InvoiceScanner Continuum v{self.version}")
        self.geometry("1400x900")
        self.minsize(1000, 700)

        # Configure grid layout
        self.grid_columnconfigure(0, weight=0) # Sidebar
        self.grid_columnconfigure(1, weight=2) # Image Preview
        self.grid_columnconfigure(2, weight=3) # Data Entry
        self.grid_rowconfigure(0, weight=1)

        # --- Sidebar ---
        self.sidebar_frame = ctk.CTkFrame(self, width=240, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(10, weight=1)

        self.logo_label = ctk.CTkLabel(
            self.sidebar_frame, text="CONTINUUM", font=ctk.CTkFont(size=24, weight="bold", family="Inter")
        )
        self.logo_label.grid(row=0, column=0, padx=20, pady=(30, 40))

        # Main Actions
        self.open_button = ctk.CTkButton(
            self.sidebar_frame, text="Select Image", command=self.open_file,
            height=45, font=ctk.CTkFont(weight="bold")
        )
        self.open_button.grid(row=1, column=0, padx=20, pady=10)

        # Status & Progress Center
        self.mode_label = ctk.CTkLabel(self.sidebar_frame, text="ENGINE STATUS", font=ctk.CTkFont(size=12, weight="bold"))
        self.mode_label.grid(row=2, column=0, padx=20, pady=(30, 10), sticky="w")

        self.engine_info = ctk.CTkLabel(self.sidebar_frame, text="Mode: Smart Detection", text_color="gray", font=ctk.CTkFont(size=11))
        self.engine_info.grid(row=3, column=0, padx=20, pady=0, sticky="w")

        # Status & Progress
        self.status_frame = ctk.CTkFrame(self.sidebar_frame, fg_color="transparent")
        self.status_frame.grid(row=4, column=0, padx=20, pady=(40, 0), sticky="ew")

        self.label_status = ctk.CTkLabel(self.status_frame, text="System Ready", text_color="#1a8b5a", font=ctk.CTkFont(size=13))
        self.label_status.grid(row=0, column=0, sticky="w")

        self.progress_bar = ctk.CTkProgressBar(self.status_frame, orientation="horizontal", mode="indeterminate", height=6)
        self.progress_bar.grid(row=1, column=0, pady=(10, 0), sticky="ew")
        self.progress_bar.set(0)

        # Export (Sticky Bottom)
        self.export_frame = ctk.CTkFrame(self.sidebar_frame, fg_color="transparent")
        self.export_frame.grid(row=11, column=0, padx=20, pady=30, sticky="ew")

        self.export_label = ctk.CTkLabel(self.export_frame, text="EXPORT DATA", font=ctk.CTkFont(size=11, weight="bold"))
        self.export_label.pack(anchor="w", pady=(0, 10))

        self.btn_export_json = ctk.CTkButton(
            self.export_frame, text="JSON Lines", state="disabled", fg_color="transparent", border_width=1, height=35
        )
        self.btn_export_json.pack(fill="x", pady=5)

        self.btn_export_csv = ctk.CTkButton(
            self.export_frame, text="Excel / CSV", state="disabled", fg_color="transparent", border_width=1, height=35
        )
        self.btn_export_csv.pack(fill="x", pady=5)

        # Settings button (Manual API Key change)
        self.btn_settings = ctk.CTkButton(
            self.sidebar_frame, text="⚙️ OpenAI API Key",
            command=self.change_api_key,
            fg_color="transparent", border_width=1, height=30,
            font=ctk.CTkFont(size=11)
        )
        self.btn_settings.grid(row=12, column=0, padx=20, pady=(0, 20), sticky="ew")

        # --- Central Viewer (Image) ---
        self.viewer_frame = ctk.CTkFrame(self, corner_radius=15, border_width=1, border_color="#333333")
        self.viewer_frame.grid(row=0, column=1, padx=(20, 10), pady=20, sticky="nsew")
        self.viewer_frame.grid_rowconfigure(0, weight=1)
        self.viewer_frame.grid_columnconfigure(0, weight=1)

        self.img_scroll_frame = ctk.CTkScrollableFrame(self.viewer_frame, fg_color="transparent", corner_radius=10)
        self.img_scroll_frame.grid(row=0, column=0, sticky="nsew", padx=2, pady=2)

        self.img_placeholder = ctk.CTkLabel(self.img_scroll_frame, text="No Receipt Selected", text_color="#555555")
        self.img_placeholder.pack(expand=True, pady=100)

        self.image_label = ctk.CTkLabel(self.img_scroll_frame, text="") # Placeholder for actual image
        self.image_label.pack(fill="both", expand=True)

        # --- Data Dashboard (Right) ---
        self.data_frame = ctk.CTkFrame(self, corner_radius=15, border_width=1, border_color="#333333")
        self.data_frame.grid(row=0, column=2, padx=(10, 20), pady=20, sticky="nsew")
        self.data_frame.grid_columnconfigure(0, weight=1)
        self.data_frame.grid_rowconfigure(2, weight=1)

        # Dashboard Header
        self.dash_header = ctk.CTkFrame(self.data_frame, fg_color="transparent")
        self.dash_header.grid(row=0, column=0, padx=20, pady=20, sticky="ew")

        self.store_entry = ctk.CTkEntry(
            self.dash_header, font=ctk.CTkFont(size=28, weight="bold"),
            height=50, border_width=0, fg_color="transparent", placeholder_text="Store Name"
        )
        self.store_entry.pack(side="left", fill="x", expand=True)

        self.btn_add_item = ctk.CTkButton(
            self.dash_header, text="+ Add Row", width=100, command=self.add_manual_row,
            fg_color="#2fa572", hover_color="#23865a", height=32
        )
        self.btn_add_item.pack(side="right", padx=(10, 0))

        # Dashboard Scroll Area
        self.table_header = ctk.CTkFrame(self.data_frame, height=30, fg_color="#1a1a1a")
        self.table_header.grid(row=1, column=0, sticky="ew", padx=20)
        ctk.CTkLabel(self.table_header, text="PRODUCT NAME", font=ctk.CTkFont(size=11, weight="bold")).place(x=10, y=5)
        ctk.CTkLabel(self.table_header, text="PRICE", font=ctk.CTkFont(size=11, weight="bold")).place(relx=0.8, y=5)

        self.scroll_frame = ctk.CTkScrollableFrame(self.data_frame, fg_color="transparent", corner_radius=0)
        self.scroll_frame.grid(row=2, column=0, padx=10, pady=(0, 10), sticky="nsew")
        self.scroll_frame.grid_columnconfigure(0, weight=4) # Name
        self.scroll_frame.grid_columnconfigure(1, weight=1) # Price

        # Total Bar
        self.dash_footer = ctk.CTkFrame(self.data_frame, height=80, fg_color="#1a1a1a", corner_radius=10)
        self.dash_footer.grid(row=3, column=0, padx=20, pady=20, sticky="ew")

        self.total_label = ctk.CTkLabel(self.dash_footer, text="SUMMARY TOTAL", font=ctk.CTkFont(size=12, weight="bold"))
        self.total_label.place(x=20, y=15)

        self.total_entry = ctk.CTkEntry(
            self.dash_footer, font=ctk.CTkFont(size=32, weight="bold"),
            width=180, height=40, border_width=0, fg_color="transparent",
            text_color="#1f6aa5", justify="right"
        )
        self.total_entry.insert(0, "0.00")
        self.total_entry.place(relx=0.98, rely=0.6, anchor="e")

        # --- State ---
        self.current_data = {"store": "", "items": [], "total": 0.0}
        self.item_entries = []
        self.processing = False
        self.current_image_path = None

        # Background Checks
        self.after(500, self.check_api_key)
        self.after(2000, lambda: threading.Thread(target=self.check_for_updates, daemon=True).start())

    def check_for_updates(self):
        """Checks GitHub for newer versions via version.json."""
        url = "https://raw.githubusercontent.com/elperroloc0/InvoiceScanner/main/version.json"
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                latest = data.get("latest_version", "1.0.0")
                if latest != self.version:
                    changelog = data.get("changelog", "")
                    self.after(0, lambda: self.prompt_update(latest, changelog))
        except Exception as e:
            logger.debug(f"Update check failed: {e}")

    def prompt_update(self, version, changelog):
        msg = f"A new version (v{version}) is available!\n\nChanges:\n{changelog}\n\nWould you like to go to the download page?"
        if messagebox.askyesno("Update Available", msg):
            webbrowser.open("https://github.com/elperroloc0/InvoiceScanner/releases/latest")

    def check_api_key(self):
        # 1. Try loading from os environment (for dev/CI)
        key = os.getenv("OPEN_AI_API")

        # 2. Try loading from persistent .env file
        if not key and ENV_FILE.exists():
            try:
                with open(ENV_FILE, "r") as f:
                    for line in f:
                        if line.startswith("OPEN_AI_API="):
                            key = line.strip().split("=", 1)[1]
                            os.environ["OPEN_AI_API"] = key
                            break
            except Exception as e:
                logger.warning(f"Failed to read .env: {e}")

        if not key:
            dialog = ctk.CTkInputDialog(text="Enter your OpenAI API Key:", title="Security Setup")
            key = dialog.get_input()
            if key:
                os.environ["OPEN_AI_API"] = key
                # Persist to .env for future runs (in App Data)
                try:
                    with open(ENV_FILE, "w") as f:
                        f.write(f"OPEN_AI_API={key}\n")
                    logger.info(f"API Key saved securely to {ENV_FILE}")
                except Exception as e:
                    logger.error(f"Failed to save API key: {e}")
            else:
                logger.warning("No API Key provided. AI Vision functions will fail.")
                messagebox.showwarning("Limited Mode", "No API Key provided. Only Local Templates (e.g. Publix) will work.")

    def change_api_key(self):
        """Allows manual update of the API key via the settings button."""
        current_key = os.getenv("OPEN_AI_API", "")
        # Mask the key for security in the dialog
        masked_key = f"{current_key[:4]}...{current_key[-4:]}" if len(current_key) > 8 else "Not Set"

        dialog = ctk.CTkInputDialog(
            text=f"Current: {masked_key}\n\nEnter new OpenAI API Key:",
            title="API Configuration"
        )
        new_key = dialog.get_input()

        if new_key:
            os.environ["OPEN_AI_API"] = new_key
            try:
                with open(ENV_FILE, "w") as f:
                    f.write(f"OPEN_AI_API={new_key}\n")
                logger.info("API Key updated and saved to .env.")
                messagebox.showinfo("Success", "API Key updated successfully!")
            except Exception as e:
                logger.error(f"Failed to save API key: {e}")
                messagebox.showerror("Error", f"Failed to save key: {e}")

    def open_file(self):
        if self.processing:
            return

        file_types = [("Receipt Images", "*.jpg *.jpeg *.png *.JPG *.PNG")]
        path = filedialog.askopenfilename(filetypes=file_types)

        if path:
            self.current_image_path = path
            self.show_image_preview(path)
            self.start_processing(path)

    def show_image_preview(self, path):
        try:
            self.img_placeholder.place_forget()

            # Load and scale image for preview
            img = Image.open(path)

            # Scale logic: Fixed width, variable height
            w, h = img.size
            canvas_w = 550 # Wider canvas for Continuum
            target_w = canvas_w - 40
            scale = target_w / w
            target_h = int(h * scale)

            img = img.resize((target_w, target_h), Image.Resampling.LANCZOS)
            ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(target_w, target_h))

            self.image_label.configure(image=ctk_img)
            self.image_label.pack(pady=10) # Add some padding inside scroll
        except Exception as e:
            print(f"Preview error: {e}")

    def start_processing(self, path):
        self.processing = True
        self.open_button.configure(state="disabled")
        self.progress_bar.start()
        self.label_status.configure(text="Processing...", text_color="#dce4ee")
        self.engine_info.configure(text="Mode: Detecting Path...", text_color="#1f6aa5")

        self.store_entry.delete(0, "end")
        self.store_entry.insert(0, "Scanning Digital Ink...")
        self.clear_results()

        print(f"[DEBUG] Starting Smart Scan Sequence...")
        threading.Thread(target=self.process_image, args=(path,), daemon=True).start()

    def process_image(self, path):
        try:
            self.after(0, lambda: self.label_status.configure(text="Preparing Optics..."))
            img = preprocess_receipt(path)

            self.after(0, lambda: self.label_status.configure(text="Smart Routing..."))

            # Use the new Smart Manager
            self.current_data = ScannerManager.process(img)

            self.after(0, self.update_ui)
        except Exception as e:
            err_msg = str(e)
            self.after(0, lambda: self.handle_error(err_msg))

    def update_ui(self):
        self.processing = False
        self.open_button.configure(state="normal")
        self.progress_bar.stop()
        self.progress_bar.set(0)
        self.label_status.configure(text="Verification Required", text_color="#1f6aa5")

        if not self.current_data:
            self.store_entry.delete(0, "end")
            self.store_entry.insert(0, "Extraction Error")
            return

        # Header Info
        self.store_entry.delete(0, "end")
        self.store_entry.insert(0, self.current_data.get("store", "New Store"))

        t_val = self.current_data.get("total", 0.0)
        self.total_entry.delete(0, "end")
        self.total_entry.insert(0, f"{t_val:.2f}" if t_val is not None else "0.00")
        self.total_entry.bind("<KeyRelease>", lambda e: self.validate_entry_color(self.total_entry))

        # Table Rows
        self.clear_results()
        items = self.current_data.get("items", [])
        for item in items:
            self.add_item_row(item.get("name", ""), item.get("price", 0.0))

        # IMPORTANT: Recalculate total from items to ensure initial UI consistency
        self.recalculate_total()

        # Enable export (only if we have items)
        if self.item_entries:
            self.btn_export_json.configure(state="normal", command=lambda: self.export("jsonl"), fg_color="#333333")
            self.btn_export_csv.configure(state="normal", command=lambda: self.export("csv"), fg_color="#333333")

    def add_manual_row(self):
        self.add_item_row("", 0.0)
        # Enable export if this is the first row
        if len(self.item_entries) == 1:
            self.btn_export_json.configure(state="normal", command=lambda: self.export("jsonl"), fg_color="#333333")
            self.btn_export_csv.configure(state="normal", command=lambda: self.export("csv"), fg_color="#333333")

    def add_item_row(self, name, price):
        row_id = len(self.item_entries)

        # Row Container for styling
        row_frame = ctk.CTkFrame(self.scroll_frame, fg_color="transparent")
        row_frame.grid(row=row_id, column=0, columnspan=2, sticky="ew", pady=2)
        row_frame.grid_columnconfigure(0, weight=4) # Name column
        row_frame.grid_columnconfigure(1, weight=1) # Price column
        row_frame.grid_columnconfigure(2, weight=0) # Delete column

        name_entry = ctk.CTkEntry(row_frame, height=35, corner_radius=5, border_width=1)
        name_entry.insert(0, str(name))
        name_entry.grid(row=0, column=0, padx=(0, 5), sticky="ew")

        price_entry = ctk.CTkEntry(row_frame, height=35, corner_radius=5, border_width=1, justify="right")
        price_entry.insert(0, f"{price:.2f}" if isinstance(price, (int, float)) else str(price))
        price_entry.grid(row=0, column=1, padx=(5, 5), sticky="ew")

        # Live calculation bind
        price_entry.bind("<KeyRelease>", lambda e: self.on_price_change(price_entry))

        delete_btn = ctk.CTkButton(
            row_frame, text="✕", width=35, height=35, fg_color="#333333",
            hover_color="#e4534f", command=lambda rf=row_frame, pe=price_entry, ne=name_entry: self.delete_row(rf, ne, pe)
        )
        delete_btn.grid(row=0, column=2, padx=(5, 0))

        self.item_entries.append((name_entry, price_entry, row_frame))

    def on_price_change(self, entry):
        self.validate_entry_color(entry)
        self.recalculate_total()

    def validate_entry_color(self, entry):
        try:
            float(entry.get())
            entry.configure(border_color=["#979da2", "#565b5e"]) # Default color
        except ValueError:
            entry.configure(border_color="#e4534f") # Red for error

    def recalculate_total(self):
        new_total = 0.0
        for _, p_ent, _ in self.item_entries:
            try:
                new_total += float(p_ent.get())
            except ValueError:
                pass
        self.total_entry.delete(0, "end")
        self.total_entry.insert(0, f"{new_total:.2f}")

    def delete_row(self, frame, name_ent, price_ent):
        # Remove from state
        self.item_entries = [x for x in self.item_entries if x[0] != name_ent]
        # Remove from UI
        frame.destroy()
        self.recalculate_total()

        if not self.item_entries:
            self.btn_export_json.configure(state="disabled", fg_color="transparent")
            self.btn_export_csv.configure(state="disabled", fg_color="transparent")

    def export(self, format):
        if not self.item_entries:
            return

        # Prepare payload from UI
        export_data = {
            "store": self.store_entry.get(),
            "items": [],
            "total": 0.0
        }

        for n_ent, p_ent, _ in self.item_entries:
            try:
                p = float(p_ent.get())
            except:
                p = 0.0
            export_data["items"].append({"name": n_ent.get(), "price": p})

        try:
            export_data["total"] = float(self.total_entry.get())
        except:
            export_data["total"] = sum(x["price"] for x in export_data["items"])

        # File Dialog
        filename = f"scan_{export_data['store'].replace(' ', '_').lower()}.{format}"
        path = filedialog.asksaveasfilename(
            defaultextension=f".{format}",
            filetypes=[(f"{format.upper()} files", f"*.{format}")],
            initialfile=filename
        )

        if path:
            save_to_file(export_data, path)
            messagebox.showinfo("Continuum Export", f"Data saved successfully to:\n{os.path.basename(path)}")
            self.label_status.configure(text="Exported Successfully", text_color="#2fa572")

    def clear_results(self):
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()
        self.item_entries = []
        self.btn_export_json.configure(state="disabled", fg_color="transparent")
        self.btn_export_csv.configure(state="disabled", fg_color="transparent")

    def handle_error(self, err):
        self.processing = False
        self.open_button.configure(state="normal")
        self.progress_bar.stop()
        self.progress_bar.set(0)
        self.label_status.configure(text="System Fault", text_color="#e4534f")
        self.store_entry.delete(0, "end")
        self.store_entry.insert(0, "Scanning Failed")
        messagebox.showerror("Continuum Error", f"Critical failure during scan:\n{err}")


if __name__ == "__main__":
    app = App()
    app.mainloop()
