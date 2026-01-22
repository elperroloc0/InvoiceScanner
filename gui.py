import os
import threading
import tkinter as tk
from tkinter import filedialog, messagebox

import customtkinter as ctk
from PIL import Image

# Import scanner logic
from scanner.config import ALLOWED_IMAGE_EXTENSIONS, SAVE_EXTENSIONS
from scanner.ocr import preprocess_receipt, run_ocr
from scanner.parser import parse_receipt
from scanner.storage import save_to_file

# Set appearance mode and theme
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")


class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("InvoiceScanner - Office Edition")
        self.geometry("1100x700")

        # Configure grid layout
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # --- Sidebar ---
        self.sidebar_frame = ctk.CTkFrame(self, width=200, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(4, weight=1)

        self.logo_label = ctk.CTkLabel(
            self.sidebar_frame, text="InvoiceScanner", font=ctk.CTkFont(size=20, weight="bold")
        )
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))

        self.open_button = ctk.CTkButton(self.sidebar_frame, text="Open Receipt", command=self.open_file)
        self.open_button.grid(row=1, column=0, padx=20, pady=10)

        self.label_status = ctk.CTkLabel(self.sidebar_frame, text="Status: Ready", text_color="gray")
        self.label_status.grid(row=2, column=0, padx=20, pady=10)

        # Export Section
        self.export_label = ctk.CTkLabel(self.sidebar_frame, text="Export As:", font=ctk.CTkFont(weight="bold"))
        self.export_label.grid(row=5, column=0, padx=20, pady=(10, 0))

        self.btn_export_json = ctk.CTkButton(
            self.sidebar_frame, text="JSON", state="disabled", fg_color="transparent", border_width=1
        )
        self.btn_export_json.grid(row=6, column=0, padx=20, pady=5)

        self.btn_export_csv = ctk.CTkButton(
            self.sidebar_frame, text="CSV / Excel", state="disabled", fg_color="transparent", border_width=1
        )
        self.btn_export_csv.grid(row=7, column=0, padx=20, pady=5)

        # --- Main Content ---
        self.main_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.main_frame.grid(row=0, column=1, padx=20, pady=20, sticky="nsew")
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_rowconfigure(1, weight=1)

        # Top Bar: Store Name
        self.store_label = ctk.CTkLabel(
            self.main_frame, text="Select an image to begin", font=ctk.CTkFont(size=24, weight="bold")
        )
        self.store_label.grid(row=0, column=0, padx=20, pady=(10, 20), sticky="w")

        # Center: Scrollable Table
        self.results_frame = ctk.CTkScrollableFrame(self.main_frame, label_text="Detected Items")
        self.results_frame.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
        self.results_frame.grid_columnconfigure(0, weight=3) # Name
        self.results_frame.grid_columnconfigure(1, weight=1) # Price

        # Bottom Bar: Total
        self.total_label = ctk.CTkLabel(
            self.main_frame, text="Total: --", font=ctk.CTkFont(size=20, weight="bold"), text_color="#1f6aa5"
        )
        self.total_label.grid(row=2, column=0, padx=20, pady=10, sticky="e")

        # --- State ---
        self.current_data = None
        self.processing = False

    def open_file(self):
        if self.processing:
            return

        file_types = [("Image files", "*.jpg *.jpeg *.png")]
        path = filedialog.askopenfilename(filetypes=file_types)

        if path:
            self.start_processing(path)

    def start_processing(self, path):
        self.processing = True
        self.open_button.configure(state="disabled")
        self.label_status.configure(text="Status: Processing...", text_color="#dce4ee")
        self.store_label.configure(text="Processing receipt...")
        self.clear_results()

        # Run in thread to not freeze GUI
        threading.Thread(target=self.process_image, args=(path,), daemon=True).start()

    def process_image(self, path):
        try:
            # 1. Preprocess
            img = preprocess_receipt(path)
            # 2. OCR
            raw = run_ocr(img, gpu=True)
            # 3. Parse
            self.current_data = parse_receipt(raw)

            # Update UI from main thread
            self.after(0, self.update_ui)
        except Exception as e:
            self.after(0, lambda: self.handle_error(str(e)))

    def update_ui(self):
        self.processing = False
        self.open_button.configure(state="normal")
        self.label_status.configure(text="Status: Done", text_color="#2fa572")

        if not self.current_data:
            self.store_label.configure(text="Failed to parse data")
            return

        self.store_label.configure(text=f"Store: {self.current_data['store']}")
        self.total_label.configure(text=f"Total: {self.current_data['total']:.2f}")

        # Fill table
        for i, item in enumerate(self.current_data["items"]):
            name = item.get("name", "Unknown")
            price = item.get("price", 0.0)

            # Row entry
            label_name = ctk.CTkLabel(self.results_frame, text=name, anchor="w")
            label_name.grid(row=i, column=0, padx=10, pady=5, sticky="w")

            label_price = ctk.CTkLabel(self.results_frame, text=f"{price:.2f}", anchor="e", text_color="gray")
            label_price.grid(row=i, column=1, padx=10, pady=5, sticky="e")

        # Enable export
        self.btn_export_json.configure(state="normal", command=lambda: self.export("jsonl"))
        self.btn_export_csv.configure(state="normal", command=lambda: self.export("csv"))

    def export(self, format):
        if not self.current_data:
            return

        path = filedialog.asksaveasfilename(
            defaultextension=f".{format}",
            filetypes=[(f"{format.upper()} files", f"*.{format}")],
            initialfile=f"invoice_{self.current_data['store'].lower()}.{format}"
        )

        if path:
            save_to_file(self.current_data, path)
            messagebox.showinfo("Export", f"Data saved to {os.path.basename(path)}")

    def clear_results(self):
        for widget in self.results_frame.winfo_children():
            widget.destroy()
        self.btn_export_json.configure(state="disabled")
        self.btn_export_csv.configure(state="disabled")
        self.total_label.configure(text="Total: --")

    def handle_error(self, err):
        self.processing = False
        self.open_button.configure(state="normal")
        self.label_status.configure(text="Status: Error", text_color="#e4534f")
        self.store_label.configure(text="Processing Error")
        messagebox.showerror("Error", f"An error occurred: {err}")


if __name__ == "__main__":
    app = App()
    app.mainloop()
