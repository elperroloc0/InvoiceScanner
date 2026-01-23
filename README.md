# InvoiceScanner Titanium Elite

A professional, vision-first receipt scanner for macOS and Windows.
Automatically extracts Store Name, Items, Prices, and Totals using a hybrid engine (Local Templates + OpenAI Vision AI).

![Titanium Dashboard](https://via.placeholder.com/800x450?text=Titanium+Dashboard+Preview)

## Features
- **Smart Routing (Auto-Pilot)**: Instantly detects if a receipt matches a known local template (e.g. Publix) for ultra-fast, free scanning.
- **Vision AI Fallback**: Uses OpenAI's GPT-4o Vision to "see" and parse complex, unknown receipts (fixing tax/total issues).
- **Pro Dashboard**: Live total calculation, row deletion, and red-flag validation for typos.
- **CSV/Excel Export**: Ready for your accounting software.

## 🚀 How to Install (For Users)

**No coding required.**

1. Go to the [Releases Page](https://github.com/elperroloc0/InvoiceScanner/releases) (link to be updated).
2. Download the `InvoiceScanner-Titanium` (macOS) or `.exe` (Windows).
3. **Launch the App**.
4. **First Run Setup**:
   - The app will asking for your **OpenAI API Key** (needed for the AI Vision features).
   - Enter it once, and it will be saved securely on your computer.
   - *Note: If you only scan supported local stores (like Publix), you can skip this, but AI features won't work.*

---

## 🛠️ For Developers (Build from Source)

If you want to modify the code or build it yourself:

### 1. Requirements
- Python 3.10+
- [Tesseract OCR](https://github.com/UB-Mannheim/tesseract/wiki) (optional, strictly for Tesseract engine fallback, mostly unused now)

### 2. Installation
```bash
git clone https://github.com/elperroloc0/InvoiceScanner.git
cd InvoiceScanner
pip install -r requirements.txt
```

### 3. Run Locally
```bash
python3 project.py
```

### 4. Build Standalone App
To create the `.app` or `.exe` file:
```bash
python3 build_app.py
```
Find the result in the `dist/` folder.

## License
MIT
