@echo off
echo ===== APTnotes OCR Enhancement Pipeline =====
echo.
echo This script will:
echo 1. Enhance PDFs with OCR
echo 2. Convert enhanced PDFs to text
echo.
echo Press Ctrl+C to cancel or any key to continue...
pause > nul

echo.
echo ===== Step 1: Installing required packages =====
pip install ocrmypdf pypdf tqdm

echo.
echo ===== Step 2: Enhancing PDFs with OCR =====
python ocr_enhance.py

echo.
echo ===== Step 3: Converting enhanced PDFs to text =====
python ocr_pdf2text.py

echo.
echo ===== Pipeline completed =====
echo.
echo Check the ocr_enhance directory for enhanced PDFs
echo Check the ocr_text directory for extracted text
echo.
pause
