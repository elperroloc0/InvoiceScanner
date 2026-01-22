# Invoice Scanner (CS50P Final Project)

#### 🎥 Video Demo: <URL HERE>

## Description

**Invoice Scanner** I decided to build a Python tool that uses Computer Vision and Optical Character Recognition (OCR) to convert these raw images into structured formats like JSON or CSV. This tool isn't just about reading text; it's about making sense of the noise and extracting meaningful financial insights for my personal budget.

The program identifies:
- **Store Name**: Primarily focused on Publix, the retailer I visit most often.
- **Line Items**: Extracts item names, total prices, and unit weights.
- **Publix receipt patters**: Identifies promotions, discounts, and voided items to ensure accuracy.
- **Totals**: Extracts the final amount.

---

## Key Features

- **Image Preprocessing**: I implemented an OpenCV pipeline to denoise images and CLAHE to normalize contrast. I have also tried dynamic thresholding to remove shadows, but it didn't work well.
- **Parsing**: I combined regular expressions with state-based logic to handle items where names and prices were split across different lines—a common issue I found in almost each scanned receipt.
- **OCR**: I chose **EasyOCR** for its flexibility across various fonts and its ability to handle slightly blurry mobile photos.
- **Multi-Format Export**: I added support for `.json`, `.jsonl`, and `.csv` so I can easily import my data into any spreadsheet or database I choose to use.
The code automatization for that can be introdused in the future.
---

## File Structure
```.
├── project.py        # The core logic I wrote for OCR and parsing
├── test_project.py   # Unit tests I used to ensure extraction logic was correct
├── requirements.txt  # Libraries you'll need to run my code
└── samples/          # My input directory for sample receipt images
```

---

## ⚙️ Installation & Usage

1. **Clone and Install**:
   ```bash
   pip install -r requirements.txt
   ```
2. **Run the Scanner**:
   ```bash
   python project.py samples/receipt.jpg -o output.csv
   ```
Supported formats: `.csv`, `.json`, `.jsonl`.

---

## My Design Choices & Challenges

The biggest challenge I faced was converting "dirty" OCR text into high-fidelity data. I realized that a simple line-by-line regex wouldn't work because receipts are always messy. I opted for a state-machine-like approach to track the context of each line.

### Technical Implementation

#### Preprocessing Pipeline
My receipt photos were often poorly lit, so I spent a lot of time on the preprocessing chain. I found multiple preprocessing filters beyond the project scope, so I chose the one that worked best with the most of the receipts:
1. **Denoising**: I used `fastNlMeansDenoising` to remove graininess.
2. **Contrast Enhancement**: CLAHE helped to sharpen text against grey backgrounds.
3. **Shadow Removal**: I used division normalization to flatten the lighting, which was the final piece of the puzzle for my OCR accuracy.

#### Parsing Logic
- **Regex Strategies**: I used named capture groups in regex patterns to identify the most common patterns in Publix receipts, such as weights (e.g., `1.25 lb @ 0.79`) and multi-buy deals (`2 FOR 3.00`).
- **OCR Correction**: I implemented a regex system to fix common errors like `O` for `0` or `g` for `9` specifically in numeric contexts, ensuring my item names remained untouched.
- **Section Detection**: I used "Stop Hints" (e.g., `TOTAL`) to stop item extraction if a price that looks like a final amount is nearby so the parser doesn't stop early on header text.

### Why I chose EasyOCR
My first thought was to use LLM models like OpenAI's, but i watend something that can run locally and is fast.
I experimented with Tesseract, but I found that EasyOCR performed better with the mobile photos I had. I also integrated a confidence thresholding system that warns the user when the OCR might be inaccurate so the junk data is not saved automatically.


---

## 🧪 Testing

I built a test file with `pytest` that covers:
- **Normalization**: Standardizing whitespace and characters.
- **Edge Cases**: Verifying that negative prices for voids and promotions are handled correctly.
- **Split Patterns**: Testing my `merge_split_prices` logic on fragmented OCR lines.
