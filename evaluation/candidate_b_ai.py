import sys
import time
from pathlib import Path
import pytesseract
from PIL import Image

def extract_receipt(image_path: str, output_path: str):
    # Record processing time
    start_time = time.time()
    
    print(f"Processing {image_path} with Tesseract OCR...")
    
    try:
        # Open the PNG image
        img = Image.open(image_path)
        
        # Run Tesseract to extract raw text
        raw_text = pytesseract.image_to_string(img)
        
        processing_time = time.time() - start_time
        
        # Save the raw output
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            f.write(raw_text)
            
        print(f"Success! Took {processing_time:.2f} seconds. Saved to {output_path}")

    except Exception as e:
        # Report errors clearly
        print(f"Failed to process {image_path}. Error: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 candidate_b_ocr.py <path_to_receipt_image>")
        sys.exit(1)
        
    input_file = sys.argv[1]
    filename = Path(input_file).stem
    output_file = f"outputs/candidate-b/{filename}.txt"
    
    extract_receipt(input_file, output_file)