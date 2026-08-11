import os
import shutil
import uuid
import json
from datetime import datetime
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, UploadFile, File, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from supabase import create_client, Client, ClientOptions
from google import genai
from PIL import Image

# Import configurations and local modules
from app.core.config import settings
from app.models import (
    InventoryActionRequest, NewItemRequest, ApprovalPayload,
    RecommendationRequest, RecommendationResponse
)
from app.engine import summarize_pantry, format_recipe_candidates, rank_recipes

load_dotenv()

app = FastAPI(title=settings.PROJECT_NAME)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize External Clients
url: str = os.environ.get("SUPABASE_URL", "")
key: str = os.environ.get("SUPABASE_KEY", "")
if not url or not key:
    print("🚨 WARNING: SUPABASE_URL or SUPABASE_KEY is missing from environment variables!")
supabase: Client = create_client(url, key)

genai_client = genai.Client()
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Authentication Dependency
def get_user_supabase(request: Request) -> Client:
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authentication token")
    token = auth_header.replace("Bearer ", "")
    return create_client(url, key, options=ClientOptions(headers={"Authorization": f"Bearer {token}"}))

@app.get("/")
def health_check():
    return {"status": "PantryPilot API is live"}


# --- Recommendations Routes ---

@app.post("/api/recommendations", response_model=RecommendationResponse)
async def get_recommendations(request: RecommendationRequest):
    """Endpoint for returning deterministically ranked recipe recommendations."""
    try:
        # Load user's active pantry inventory
        pantry_res = supabase.table("pantry_items").select("*").eq("status", "active").execute()

        #print("RAW PANTRY DATA FROM DB:", pantry_res.data) #--

        pantry_summary = summarize_pantry(pantry_res.data)

        #print("SUMMARIZED PANTRY DATA:", pantry_summary) #--

        # Load active recipes and ingredients
        recipes_res = supabase.table("recipes").select("*").eq("status", "active").execute()
        ingredients_res = supabase.table("recipe_ingredients").select("*").execute()
        
        recipe_candidates = format_recipe_candidates(recipes_res.data, ingredients_res.data)

        # Run the matching algorithm[cite: 1]
        ranked_results = rank_recipes(pantry_summary, recipe_candidates, request)

        # Handle Empty State[cite: 1]
        if not ranked_results:
            return {
                "algorithmVersion": "deterministic-v1",
                "generatedAt": datetime.utcnow().isoformat() + "Z",
                "pantryItemCount": len(pantry_summary),
                "filters": request.dict(),
                "results": [],
                "message": "No recipes matched the current pantry and filters."
            }

        return {
            "algorithmVersion": "deterministic-v1",
            "generatedAt": datetime.utcnow().isoformat() + "Z",
            "pantryItemCount": len(pantry_summary),
            "filters": request.dict(),
            "results": ranked_results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- Inventory Routes ---

@app.get("/api/inventory")
async def get_pantry_inventory(client: Client = Depends(get_user_supabase)):
    try:
        response = client.table("pantry_items").select("*").in_("status", ["active"]).execute()
        return response.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/inventory/{item_id}/action")
async def process_inventory_action(item_id: str, payload: InventoryActionRequest, client: Client = Depends(get_user_supabase)):
    try:
        response = client.rpc(
            "apply_inventory_change",
            {"p_item_id": item_id, "p_event_type": payload.action_type, "p_amount": payload.amount, "p_note": payload.note}
        ).execute()
        return {"success": True, "data": response.data}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/inventory/manual")
async def add_manual_item(payload: NewItemRequest, client: Client = Depends(get_user_supabase)):
    try:
        item_response = client.table("pantry_items").insert({
            "name": payload.name, "category": payload.category.lower(),
            "current_quantity": payload.quantity, "unit": payload.unit,
            "purchase_date": payload.purchase_date, "source_type": "manual", "status": "active"
        }).execute()
        new_item = item_response.data[0]

        client.table("inventory_events").insert({
            "pantry_item_id": new_item["id"], "event_type": "manual_add",
            "quantity_delta": payload.quantity, "quantity_before": 0,
            "quantity_after": payload.quantity, "unit": payload.unit, "note": "Added manually"
        }).execute()

        return {"success": True, "data": new_item}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- Receipt Routes ---

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

    new_receipt = {"original_filename": file.filename, "storage_key": secure_filename, "status": "processing"}
    db_response = client.table("receipts").insert(new_receipt).execute()
    if not db_response.data:
        raise HTTPException(status_code=500, detail="Failed to create receipt record.")

    receipt_id = db_response.data[0]["id"]

    try:
        img = Image.open(file_path)
        prompt = """Analyze this grocery receipt... (JSON structure logic)"""
        response = genai_client.models.generate_content(model='gemini-2.5-flash', contents=[prompt, img])

        raw_json = response.text.strip()
        if raw_json.startswith("```"):
            lines = raw_json.splitlines()
            if lines[0].startswith("```"): lines = lines[1:]
            if lines and lines[-1].startswith("```"): lines = lines[:-1]
            raw_json = "\n".join(lines).strip()

        extracted_data = json.loads(raw_json)

        draft_items = [
            {"receipt_id": receipt_id, "raw_text": item.get("rawText", ""), "normalized_name": item.get("normalizedName"),
             "quantity": item.get("quantity"), "unit": item.get("unit"), "price": item.get("price"), "sort_order": index}
            for index, item in enumerate(extracted_data.get("items", []))
        ]

        if draft_items:
            client.table("receipt_item_drafts").insert(draft_items).execute()

        client.table("receipts").update({
            "status": "needs_review", "store_name": extracted_data.get("storeName"),
            "purchase_date": extracted_data.get("purchaseDate"), "total": extracted_data.get("total")
        }).eq("id", receipt_id).execute()

    except Exception as e:
        client.table("receipts").update({"status": "failed", "error_code": str(e)}).eq("id", receipt_id).execute()
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

    pantry_inserts = [
        {"name": item.normalized_name, "current_quantity": max(1, int(item.quantity)), "category": "pantry",
         "unit": "each", "source_type": "receipt", "source_receipt_id": receipt_id,
         "purchase_date": receipt_res.data[0].get("purchase_date"), "status": "active"}
        for item in payload.items if item.included and item.normalized_name.strip()
    ]

    if pantry_inserts:
        insert_res = client.table("pantry_items").insert(pantry_inserts).execute()
        events = [
            {"pantry_item_id": new_item["id"], "event_type": "purchase", "quantity_delta": new_item["current_quantity"],
             "quantity_before": 0, "quantity_after": new_item["current_quantity"], "unit": new_item["unit"],
             "note": "Imported from receipt", "source_receipt_id": receipt_id}
            for new_item in insert_res.data
        ]
        if events:
            client.table("inventory_events").insert(events).execute()

    client.table("receipts").update({"status": "completed", "approved_at": datetime.utcnow().isoformat()}).eq("id", receipt_id).execute()
    return {"status": "completed", "pantryItemsCreated": len(pantry_inserts)}