#!/usr/bin/env python3
"""
OCR Enhancement Script for APTnotes PDFs

This script enhances scanned PDFs using OCRmyPDF to improve text extraction quality.
It processes PDFs from the aptnote_download directory and saves enhanced versions
to the ocr_enhance directory.

Requirements:
- ocrmypdf (and its dependencies including Tesseract OCR)
- pypdf
- tqdm

Usage:
    python ocr_enhance.py [--check-only] [--max-workers N]

Options:
    --check-only     Only check which PDFs need OCR without processing them
    --max-workers N  Number of parallel workers (default: 4)
"""

import os
import re
import sys
import argparse
import subprocess
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import shutil
from tqdm import tqdm
from pypdf import PdfReader

def needs_ocr(pdf_path):
    """Check if a PDF has extractable text or needs OCR"""
    try:
        reader = PdfReader(pdf_path)
        # Check first 3 pages or all pages if less than 3
        pages_to_check = min(3, len(reader.pages))
        
        for i in range(pages_to_check):
            text = reader.pages[i].extract_text()
            # If we get a reasonable amount of text, assume it's already good
            if len(text) > 100:  # Arbitrary threshold
                return False
        
        # If we get here, the PDF likely needs OCR
        return True
    except Exception as e:
        print(f"Error checking {pdf_path}: {str(e)}")
        # If there's an error reading the PDF, assume it needs OCR
        return True

def enhance_pdf(pdf_path, output_path):
    """Enhance a PDF with OCRmyPDF"""
    try:
        # Create parent directory if it doesn't exist
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Skip if output file already exists
        if os.path.exists(output_path):
            return (pdf_path, output_path, "SKIPPED (already exists)")
        
        # Check if PDF needs OCR
        if not needs_ocr(pdf_path):
            # If PDF doesn't need OCR, just copy it
            shutil.copy2(pdf_path, output_path)
            return (pdf_path, output_path, "COPIED (already has text)")
        
        # Run OCRmyPDF with appropriate options
        # --skip-text: Skip pages that already have text
        # --deskew: Straighten pages
        # --clean: Clean pages before OCR
        # --optimize 3: Optimize PDF for size (level 3)
        # --language eng: Use English language for OCR
        cmd = [
            "ocrmypdf",
            "--skip-text",
            "--deskew",
            "--clean",
            "--optimize", "3",
            "--language", "eng",
            str(pdf_path),
            str(output_path)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            return (pdf_path, output_path, "SUCCESS")
        else:
            return (pdf_path, output_path, f"ERROR: {result.stderr}")
            
    except Exception as e:
        return (pdf_path, output_path, f"EXCEPTION: {str(e)}")

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Enhance PDFs with OCR")
    parser.add_argument("--check-only", action="store_true", help="Only check which PDFs need OCR")
    parser.add_argument("--max-workers", type=int, default=4, help="Number of parallel workers")
    args = parser.parse_args()
    
    # Define paths
    script_dir = Path(__file__).parent.absolute()
    pdf_dir = (script_dir / "../aptnote_download").resolve()
    output_dir = (script_dir / "ocr_enhance").resolve()
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"Source PDF directory: {pdf_dir}")
    print(f"Enhanced PDF output directory: {output_dir}")
    
    # Find all PDF files recursively
    pdf_files = list(pdf_dir.glob("**/*.pdf"))
    print(f"Found {len(pdf_files)} PDF files")
    
    if len(pdf_files) == 0:
        print("No PDF files found. Check the directory path.")
        return
    
    # Prepare output paths
    pdf_pairs = []
    for pdf_file in pdf_files:
        # Get relative path from pdf_dir
        rel_path = pdf_file.relative_to(pdf_dir)
        # Create corresponding output path
        out_path = output_dir / rel_path
        pdf_pairs.append((pdf_file, out_path))
    
    # Show first few files for verification
    for i in range(min(3, len(pdf_pairs))):
        print(f"Input: {pdf_pairs[i][0]}")
        print(f"Output: {pdf_pairs[i][1]}")
        print()
    
    # If check-only mode, just check which PDFs need OCR
    if args.check_only:
        print("Checking which PDFs need OCR...")
        needs_ocr_count = 0
        has_text_count = 0
        
        for pdf_file, _ in tqdm(pdf_pairs, desc="Checking PDFs"):
            if needs_ocr(pdf_file):
                needs_ocr_count += 1
                print(f"Needs OCR: {pdf_file}")
            else:
                has_text_count += 1
        
        print(f"\nSummary: {needs_ocr_count} PDFs need OCR, {has_text_count} already have text")
        return
    
    # Initialize counters
    results = {
        "SUCCESS": 0,
        "COPIED": 0,
        "SKIPPED": 0,
        "ERROR": 0,
        "EXCEPTION": 0
    }
    
    # Process PDFs with progress bar
    with ThreadPoolExecutor(max_workers=args.max_workers) as executor:
        # Submit all tasks
        future_to_pdf = {executor.submit(enhance_pdf, input_path, output_path): input_path 
                         for input_path, output_path in pdf_pairs}
        
        # Process results as they complete with a progress bar
        for future in tqdm(future_to_pdf, total=len(pdf_pairs), desc="Enhancing PDFs"):
            try:
                input_path, output_path, status = future.result()
                
                # Update counters based on status
                if "SUCCESS" in status:
                    results["SUCCESS"] += 1
                elif "COPIED" in status:
                    results["COPIED"] += 1
                elif "SKIPPED" in status:
                    results["SKIPPED"] += 1
                elif "ERROR" in status:
                    results["ERROR"] += 1
                    print(f"Error processing {input_path}: {status}")
                elif "EXCEPTION" in status:
                    results["EXCEPTION"] += 1
                    print(f"Exception processing {input_path}: {status}")
            except Exception as e:
                print(f"Error with future: {str(e)}")
    
    # Print summary
    print("\nProcessing Summary:")
    print(f"Total PDFs: {len(pdf_pairs)}")
    print(f"Successfully OCR'd: {results['SUCCESS']}")
    print(f"Copied (already had text): {results['COPIED']}")
    print(f"Skipped (already processed): {results['SKIPPED']}")
    print(f"Errors: {results['ERROR']}")
    print(f"Exceptions: {results['EXCEPTION']}")

if __name__ == "__main__":
    main()
