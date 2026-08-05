import os
import shutil
import uuid
import json
from datetime import datetime
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, UploadFile, File, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from supabase import create_client, Client, ClientOptions
from app.core.config import settings
from google import genai
from PIL import Image
from typing import Optional

load_dotenv()

app = FastAPI(title=settings.PROJECT_NAME)

@app.get("/")
def health_check():
    return {"status": "PantryPilot API is live"}

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Supabase client safely
url: str = os.environ.get("SUPABASE_URL", "")
key: str = os.environ.get("SUPABASE_KEY", "")
if not url or not key:
    print("🚨 WARNING: SUPABASE_URL or SUPABASE_KEY is missing from environment variables!")
supabase: Client = create_client(url, key)

def get_user_supabase(request: Request) -> Client:
    """Extracts the JWT from the request and creates a user-scoped Supabase client."""
    auth_header = request.headers.get("Authorization")
    
    if not auth_header or not auth_header.startswith("Bearer "):
        # If there's no token, we throw an immediate 401 Unauthorized error
        raise HTTPException(status_code=401, detail="Missing or invalid authentication token")
    
    token = auth_header.replace("Bearer ", "")
    
    # Create a fresh client that passes the user's token directly to PostgreSQL
    scoped_client = create_client(
        url, 
        key, 
        options=ClientOptions(headers={"Authorization": f"Bearer {token}"})
    )
    
    return scoped_client

# Initialize Gemini
client = genai.Client()

# Local storage directory
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


# --- Pydantic Models ---
class InventoryActionRequest(BaseModel):
    action_type: str
    amount: float
    note: Optional[str] = None

class ApprovedItem(BaseModel):
    id: str
    normalized_name: str
    quantity: float
    included: bool

class ApprovalPayload(BaseModel):
    items: list[ApprovedItem]

class NewItemRequest(BaseModel):
    name: str
    category: str
    quantity: float
    unit: str
    purchase_date: str


# --- Day 7 Inventory Routes ---

@app.get("/api/inventory")
async def get_pantry_inventory(client: Client = Depends(get_user_supabase)):
    """Fetch all active pantry items for the authenticated user."""
    try:
        response = client.table("pantry_items").select("*").in_("status", ["active"]).execute()
        return response.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/inventory/{item_id}/action")
async def process_inventory_action(item_id: str, payload: InventoryActionRequest, client: Client = Depends(get_user_supabase)):
    """Process an atomic inventory change using the user's credentials."""
    try:
        response = client.rpc(
            "apply_inventory_change",
            {
                "p_item_id": item_id,
                "p_event_type": payload.action_type,
                "p_amount": payload.amount,
                "p_note": payload.note
            }
        ).execute()
        return {"success": True, "data": response.data}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/inventory/manual")
async def add_manual_item(payload: NewItemRequest, client: Client = Depends(get_user_supabase)):
    """Manually add a new item and log the initial event securely."""
    try:
        # 1. We no longer need a hardcoded user_id; RLS handles it automatically via the token
        item_response = client.table("pantry_items").insert({
            "name": payload.name,
            "category": payload.category.lower(),
            "current_quantity": payload.quantity,
            "unit": payload.unit,
            "purchase_date": payload.purchase_date,
            "source_type": "manual",
            "status": "active"
        }).execute()
        
        new_item = item_response.data[0]

        client.table("inventory_events").insert({
            "pantry_item_id": new_item["id"],
            "event_type": "manual_add",
            "quantity_delta": payload.quantity,
            "quantity_before": 0,
            "quantity_after": payload.quantity,
            "unit": payload.unit,
            "note": "Added manually"
        }).execute()

        return {"success": True, "data": new_item}
    except Exception as e:
        print("THE CRASH REASON IS:", str(e))
        raise HTTPException(status_code=500, detail=str(e))


# --- Day 6 Receipt Routes (Updated for Day 7 Auth) ---

@app.post("/api/receipts")
async def upload_receipt(file: UploadFile = File(...), client: Client = Depends(get_user_supabase)):
    allowed_types = ["image/jpeg", "image/png", "application/pdf"]
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="File type not supported.")

    file_extension = file.filename.split(".")[-1]
    secure_filename = f"{uuid.uuid4()}.{file_extension}"
    file_path = os.path.join(UPLOAD_DIR, secure_filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    new_receipt = {
        "original_filename": file.filename,
        "storage_key": secure_filename,
        "status": "processing",
    }

    db_response = client.table("receipts").insert(new_receipt).execute()
    if not db_response.data:
        raise HTTPException(status_code=500, detail="Failed to create receipt record.")

    receipt_id = db_response.data[0]["id"]

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
        Exclude taxes, subtotals, change, and store messages. Return ONLY the raw JSON object.
        """
        response = genai_client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[prompt, img]
        )

        raw_json = response.text.strip()
        if raw_json.startswith("```"):
            lines = raw_json.splitlines()
            if lines[0].startswith("```"): lines = lines[1:]
            if lines and lines[-1].startswith("```"): lines = lines[:-1]
            raw_json = "\n".join(lines).strip()

        extracted_data = json.loads(raw_json)

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
            client.table("receipt_item_drafts").insert(draft_items).execute()

        client.table("receipts").update({
            "status": "needs_review",
            "store_name": extracted_data.get("storeName"),
            "purchase_date": extracted_data.get("purchaseDate"),
            "total": extracted_data.get("total")
        }).eq("id", receipt_id).execute()

    except Exception as e:
        client.table("receipts").update({
            "status": "failed",
            "error_code": str(e)
        }).eq("id", receipt_id).execute()
        raise HTTPException(status_code=500, detail=f"Extraction failed: {str(e)}")

    return {"receiptId": receipt_id, "status": "needs_review"}

@app.get("/api/receipts/{receipt_id}")
def get_receipt_review(receipt_id: str, client: Client = Depends(get_user_supabase)):
    receipt_res = client.table("receipts").select("*").eq("id", receipt_id).execute()
    if not receipt_res.data:
        raise HTTPException(status_code=404, detail="Receipt not found")
    
    items_res = client.table("receipt_item_drafts").select("*").eq("receipt_id", receipt_id).order("sort_order").execute()

    return {"receipt": receipt_res.data[0], "items": items_res.data}

@app.post("/api/receipts/{receipt_id}/approve")
def approve_receipt(receipt_id: str, payload: ApprovalPayload, client: Client = Depends(get_user_supabase)):
    receipt_res = client.table("receipts").select("*").eq("id", receipt_id).execute()
    if not receipt_res.data:
        raise HTTPException(status_code=404, detail="Receipt not found")
    
    if receipt_res.data[0]["status"] == "completed":
        raise HTTPException(status_code=400, detail="This receipt has already been approved.")

    pantry_inserts = []
    for item in payload.items:
        if item.included and item.normalized_name.strip():
            qty = max(1, int(item.quantity))
            pantry_inserts.append({
                "name": item.normalized_name,
                "current_quantity": qty,
                "category": "pantry",
                "unit": "each",
                "source_type": "receipt",
                "source_receipt_id": receipt_id,
                "purchase_date": receipt_res.data[0].get("purchase_date"),
                "status": "active"
            })

    if pantry_inserts:
        insert_res = client.table("pantry_items").insert(pantry_inserts).execute()
        
        events = []
        for new_item in insert_res.data:
            events.append({
                "pantry_item_id": new_item["id"],
                "event_type": "purchase",
                "quantity_delta": new_item["current_quantity"],
                "quantity_before": 0,
                "quantity_after": new_item["current_quantity"],
                "unit": new_item["unit"],
                "note": "Imported from receipt",
                "source_receipt_id": receipt_id
            })
        if events:
            client.table("inventory_events").insert(events).execute()

    client.table("receipts").update({
        "status": "completed",
        "approved_at": datetime.utcnow().isoformat()
    }).eq("id", receipt_id).execute()

    return {"status": "completed", "pantryItemsCreated": len(pantry_inserts)}