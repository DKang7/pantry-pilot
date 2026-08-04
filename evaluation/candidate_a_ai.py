import sys
import time
from pathlib import Path
from PIL import Image
import os
from dotenv import load_dotenv

# Use the new package structure
from google import genai

PROJECT_ROOT = Path(__file__).resolve().parents[1]

# Load the project-level .env file reliably, regardless of the current working directory.
load_dotenv(PROJECT_ROOT / ".env")


def create_client() -> genai.Client:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is not set. Add a valid key to the project .env file or export it before running this script."
        )

    return genai.Client(api_key=api_key)

def extract_receipt(image_path: str, output_path: str):
    start_time = time.time()

    print(f"Processing {image_path} with Multimodal AI (Gemini)...")

    try:
        client = create_client()

        # The new SDK automatically converts PIL Images
        img = Image.open(image_path)

        prompt = """
        Analyze this grocery receipt. Extract the data into valid JSON matching this structure:
        {
          "storeName": "Name",
          "purchaseDate": "YYYY-MM-DD",
          "currency": "USD",
          "items": [
            {
              "rawText": "Original line text",
              "name": "Normalized grocery name",
              "quantity": 1.0,
              "unit": "lb or item",
              "price": 0.00
            }
          ]
        }
        Exclude taxes, subtotals, change, and store messages.
        Return ONLY the raw JSON object, without markdown formatting.
        """

        # Use the updated generate_content method
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[prompt, img]
        )

        processing_time = time.time() - start_time

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            f.write(response.text)

        print(f"Success! Took {processing_time:.2f} seconds. Saved to {output_path}")

    except Exception as e:
        print(f"Failed to process {image_path}. Error: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 candidate_a_ai.py <path_to_receipt_image>")
        sys.exit(1)
        
    input_file = sys.argv[1]
    filename = Path(input_file).stem
    output_file = f"outputs/candidate-a/{filename}.json"
    
    extract_receipt(input_file, output_file)