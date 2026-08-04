import os
import shutil
import uuid
import json
from datetime import datetime
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from supabase import create_client, Client
from app.core.config import settings
from PIL import Image

try:
    from google import genai
except ImportError:
    genai = None

load_dotenv()

app = FastAPI(title=settings.PROJECT_NAME)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Supabase client using environment variables
url: str = os.environ.get("SUPABASE_URL", "")
key: str = os.environ.get("SUPABASE_KEY", "")
supabase: Client = create_client(url, key)

# Initialize Gemini Client (automatically reads GEMINI_API_KEY from environment)
client = genai.Client() if genai is not None else None

# Local storage directory for uploaded receipt files
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


# --- Models ---
class InventoryItem(BaseModel):
    item_name: str
    quantity: int


# --- Existing Inventory Routes ---
@app.get("/api/inventory")
def get_inventory():
    try:
        response = supabase.table("inventory").select("*").execute()
        return response.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/inventory", status_code=201)
def add_inventory(item: InventoryItem):
    if item.quantity <= 0:
        raise HTTPException(status_code=422, detail="Quantity must be greater than 0")
    
    try:
        data = {"item_name": item.item_name, "quantity": item.quantity}
        response = supabase.table("inventory").insert(data).execute()
        return response.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- Day 6 Receipt Processing Route ---
@app.post("/api/receipts")
async def upload_receipt(file: UploadFile = File(...)):
    # 1. Validate file format
    allowed_types = ["image/jpeg", "image/png", "application/pdf"]
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="File type not supported. Please upload a JPEG, PNG, or PDF.")

    if client is None:
        raise HTTPException(status_code=503, detail="Receipt extraction is unavailable because the Gemini SDK is not installed.")

    # 2. Save file locally with secure name
    file_extension = file.filename.split(".")[-1]
    secure_filename = f"{uuid.uuid4()}.{file_extension}"
    file_path = os.path.join(UPLOAD_DIR, secure_filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # 3. Insert initial receipt record into database
    new_receipt = {
        "user_id": "00000000-0000-0000-0000-000000000000", # Placeholder UUID
        "original_filename": file.filename,
        "storage_key": secure_filename,
        "status": "processing",
    }

    db_response = supabase.table("receipts").insert(new_receipt).execute()
    if not db_response.data:
        raise HTTPException(status_code=500, detail="Failed to create receipt record.")

    receipt_record = db_response.data[0]
    receipt_id = receipt_record["id"]

    # 4. Extract items using Gemini
    try:
        img = Image.open(file_path)
        prompt = """
        Analyze this grocery receipt. Extract the data into valid JSON matching this structure:
        {
          "storeName": "Name",
          "purchaseDate": "YYYY-MM-DD",
          "currency": "USD",
          "total": 0.00,
          "items": [
            {
              "rawText": "Original line text",
              "normalizedName": "Normalized grocery name",
              "quantity": 1.0,
              "unit": "lb or item",
              "price": 0.00
            }
          ]
        }
        Exclude taxes, subtotals, change, and store messages.
        Return ONLY the raw JSON object.
        """
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[prompt, img]
        )

        # Handle formatting block quotes if returned by Gemini
        raw_json = response.text.strip()
        if raw_json.startswith("```"):
            lines = raw_json.splitlines()
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            raw_json = "\n".join(lines).strip()

        extracted_data = json.loads(raw_json)

        # 5. Insert draft items into database
        draft_items = []
        for index, item in enumerate(extracted_data.get("items", [])):
            draft_items.append({
                "receipt_id": receipt_id,
                "raw_text": item.get("rawText", ""),
                "normalized_name": item.get("normalizedName"),
                "quantity": item.get("quantity"),
                "unit": item.get("unit"),
                "price": item.get("price"),
                "sort_order": index
            })

        if draft_items:
            supabase.table("receipt_item_drafts").insert(draft_items).execute()

        # Update receipt status to needs_review
        supabase.table("receipts").update({
            "status": "needs_review",
            "store_name": extracted_data.get("storeName"),
            "purchase_date": extracted_data.get("purchaseDate"),
            "total": extracted_data.get("total")
        }).eq("id", receipt_id).execute()

    except Exception as e:
        # Update receipt status to failed if an error occurs
        supabase.table("receipts").update({
            "status": "failed",
            "error_code": str(e)
        }).eq("id", receipt_id).execute()
        
        raise HTTPException(status_code=500, detail=f"Extraction failed: {str(e)}")

    return {
        "receiptId": receipt_id,
        "status": "needs_review",
    }

# --- Model for Approval Payload ---
class ApprovedItem(BaseModel):
    id: str
    normalized_name: str
    quantity: float
    included: bool

class ApprovalPayload(BaseModel):
    items: list[ApprovedItem]


# --- Fetch Draft Receipt for Review ---
@app.get("/api/receipts/{receipt_id}")
def get_receipt_review(receipt_id: str):
    # Fetch receipt header
    receipt_res = supabase.table("receipts").select("*").eq("id", receipt_id).execute()
    if not receipt_res.data:
        raise HTTPException(status_code=404, detail="Receipt not found")
    
    receipt = receipt_res.data[0]

    # Fetch draft items
    items_res = supabase.table("receipt_item_drafts").select("*").eq("receipt_id", receipt_id).order("sort_order").execute()

    return {
        "receipt": receipt,
        "items": items_res.data
    }


# --- Approve and Save to Pantry ---
@app.post("/api/receipts/{receipt_id}/approve")
def approve_receipt(receipt_id: str, payload: ApprovalPayload):
    # 1. Prevent duplicate approvals
    receipt_res = supabase.table("receipts").select("status").eq("id", receipt_id).execute()
    if not receipt_res.data:
        raise HTTPException(status_code=404, detail="Receipt not found")
    
    if receipt_res.data[0]["status"] == "completed":
        raise HTTPException(status_code=400, detail="This receipt has already been approved.")

    # 2. Filter items marked for inclusion
    items_to_add = []
    for item in payload.items:
        if item.included and item.normalized_name.strip():
            # Convert quantity to integer if needed for inventory schema
            qty = max(1, int(item.quantity))
            items_to_add.append({
                "item_name": item.normalized_name,
                "quantity": qty
            })

    # 3. Add approved items to main inventory table
    if items_to_add:
        supabase.table("inventory").insert(items_to_add).execute()

    # 4. Mark receipt as completed
    supabase.table("receipts").update({
        "status": "completed",
        "approved_at": datetime.utcnow().isoformat()
    }).eq("id", receipt_id).execute()

    return {
        "status": "completed",
        "pantryItemsCreated": len(items_to_add)
    }