#!/usr/bin/env python3
"""
OCR PDF to Text Converter

This script converts OCR-enhanced PDFs to text files.
It processes PDFs from the ocr_enhance directory and saves text files
to the ocr_text directory.

Requirements:
- pypdf
- tqdm

Usage:
    python ocr_pdf2text.py [--max-workers N]

Options:
    --max-workers N  Number of parallel workers (default: 4)
"""

import os
import sys
import argparse
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from tqdm import tqdm
from pypdf import PdfReader

def convert_pdf_to_text(pdf_path, text_path):
    """Convert a PDF file to text"""
    try:
        # Create parent directory if it doesn't exist
        os.makedirs(os.path.dirname(text_path), exist_ok=True)
        
        # Skip if output file already exists
        if os.path.exists(text_path):
            return (pdf_path, text_path, "SKIPPED (already exists)")
        
        # Extract text using PyPDF
        reader = PdfReader(pdf_path)
        text_content = ""
        
        for page in reader.pages:
            text_content += page.extract_text() + "\n"
        
        # Write text to output file
        with open(text_path, 'w', encoding='utf-8') as f:
            f.write(text_content)
            
        # Check if we got meaningful text
        if len(text_content.strip()) > 100:
            return (pdf_path, text_path, "SUCCESS")
        else:
            return (pdf_path, text_path, "WARNING: Extracted text is very short")
            
    except Exception as e:
        return (pdf_path, text_path, f"ERROR: {str(e)}")

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Convert OCR-enhanced PDFs to text")
    parser.add_argument("--max-workers", type=int, default=4, help="Number of parallel workers")
    args = parser.parse_args()
    
    # Define paths
    script_dir = Path(__file__).parent.absolute()
    pdf_dir = (script_dir / "ocr_enhance").resolve()
    text_dir = (script_dir / "ocr_text").resolve()
    
    # Create output directory if it doesn't exist
    os.makedirs(text_dir, exist_ok=True)
    
    print(f"Source PDF directory: {pdf_dir}")
    print(f"Text output directory: {text_dir}")
    
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
        # Create corresponding output path with .txt extension
        text_path = text_dir / rel_path.with_suffix('.txt')
        pdf_pairs.append((pdf_file, text_path))
    
    # Show first few files for verification
    for i in range(min(3, len(pdf_pairs))):
        print(f"Input: {pdf_pairs[i][0]}")
        print(f"Output: {pdf_pairs[i][1]}")
        print()
    
    # Initialize counters
    results = {
        "SUCCESS": 0,
        "WARNING": 0,
        "SKIPPED": 0,
        "ERROR": 0
    }
    
    # Process PDFs with progress bar
    with ThreadPoolExecutor(max_workers=args.max_workers) as executor:
        # Submit all tasks
        future_to_pdf = {executor.submit(convert_pdf_to_text, pdf_file, text_path): pdf_file 
                         for pdf_file, text_path in pdf_pairs}
        
        # Process results as they complete with a progress bar
        for future in tqdm(future_to_pdf, total=len(pdf_pairs), desc="Converting PDFs to text"):
            try:
                pdf_file, text_path, status = future.result()
                
                # Update counters based on status
                if "SUCCESS" in status:
                    results["SUCCESS"] += 1
                elif "WARNING" in status:
                    results["WARNING"] += 1
                    print(f"Warning for {pdf_file}: {status}")
                elif "SKIPPED" in status:
                    results["SKIPPED"] += 1
                elif "ERROR" in status:
                    results["ERROR"] += 1
                    print(f"Error processing {pdf_file}: {status}")
            except Exception as e:
                print(f"Error with future: {str(e)}")
                results["ERROR"] += 1
    
    # Print summary
    print("\nProcessing Summary:")
    print(f"Total PDFs: {len(pdf_pairs)}")
    print(f"Successfully converted: {results['SUCCESS']}")
    print(f"Converted with warnings: {results['WARNING']}")
    print(f"Skipped (already processed): {results['SKIPPED']}")
    print(f"Errors: {results['ERROR']}")
    
    if results['SUCCESS'] > 0 or results['WARNING'] > 0:
        print(f"\nText files have been saved to: {text_dir}")

if __name__ == "__main__":
    main()
