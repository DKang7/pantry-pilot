import os
import sys
import shutil
import uuid
import json
import logging
from datetime import datetime
from contextlib import asynccontextmanager
import time

# --- Third-Party Imports ---
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, UploadFile, File, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from supabase import create_client, Client, ClientOptions
from google import genai
from PIL import Image

# 1. LOAD ENV VARS FIRST! 
# This must happen before importing app.engine so Gemini can find the key.
load_dotenv()

# --- Local Imports ---
from app.core.config import settings
from app.models import (
    InventoryActionRequest, NewItemRequest, ApprovalPayload,
    RecommendationRequest, RecommendationResponse,
    SaveRecipeRequest, DismissRecipeRequest, RecipeFeedbackRequest,
    DeductionItem, CookingCompleteRequest
)
from app.engine import (
    search_recipes_semantically,
    calculate_hybrid_score,
    sort_hybrid_results,
    summarize_pantry,              
    rank_recipes,                  
    format_recipe_candidates,
    generate_llm_explanations,
    build_consumption_proposal
)

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Environment Validation ---
# Required server-side configuration variables
REQUIRED_ENV_VARS = [
    "SUPABASE_URL",
    "SUPABASE_KEY",
    "GEMINI_API_KEY"
]

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Validate environment variables on startup."""
    missing_vars = [var for var in REQUIRED_ENV_VARS if not os.getenv(var)]
    if missing_vars:
        logger.error(f"Deployment failed: Missing required environment variables: {', '.join(missing_vars)}")
        # Exit immediately to prevent a broken production deployment
        sys.exit(1)
    
    logger.info("Environment configuration validated successfully.")
    yield

# --- App Initialization ---
app = FastAPI(title=settings.PROJECT_NAME, lifespan=lifespan)

# --- Basic Rate Limiting & Feature Flags ---
request_counts = {}
ENABLE_LLM_EXPLANATIONS = os.getenv("ENABLE_LLM_EXPLANATIONS", "true").lower() == "true"

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def add_request_id_and_log(request: Request, call_next):
    # Generate a unique request ID like "req_7f49b18"
    request_id = f"req_{uuid.uuid4().hex[:7]}"
    start_time = time.time()
    
    # Process the actual request
    try:
        response = await call_next(request)
        status_code = response.status_code
    except Exception as e:
        status_code = 500
        raise e
    finally:
        duration_ms = int((time.time() - start_time) * 1000)
        
        # Log the operation securely as structured JSON
        logger.info(json.dumps({
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": "error" if status_code >= 400 else "info",
            "requestId": request_id,
            "operation": f"{request.method} {request.url.path}",
            "applicationVersion": "v0.1.0-beta.1",
            "status": "failed" if status_code >= 400 else "success",
            "durationMs": duration_ms,
            "fallbackUsed": False
        }))
        
        # Return the ID in the headers so the frontend can display it if an error occurs
        if 'response' in locals():
            response.headers["X-Request-ID"] = request_id
            
    return response

# --- Initialize External Clients ---
url: str = os.environ.get("SUPABASE_URL", "")
key: str = os.environ.get("SUPABASE_KEY", "")
if not url or not key:
    print("🚨 WARNING: SUPABASE_URL or SUPABASE_KEY is missing from environment variables!")
supabase: Client = create_client(url, key)

gemini_api_key = os.environ.get("GEMINI_API_KEY")
if not gemini_api_key:
    print("🚨 WARNING: GEMINI_API_KEY is missing from environment variables!")
genai_client = genai.Client(api_key=gemini_api_key)

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# --- Authentication Dependency ---
def get_user_supabase(request: Request) -> Client:
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authentication token")
    token = auth_header.replace("Bearer ", "")
    return create_client(url, key, options=ClientOptions(headers={"Authorization": f"Bearer {token}"}))


# ==========================================
#                  ROUTES
# ==========================================
@app.get("/")
def read_root():
    return {"message": "PantryPilot API is running. Check /api/health for status."}

@app.get("/api/health")
def health_check():
    """Basic health endpoint that exposes no secrets."""
    return {
        "status": "ok",
        "version": "v0.1.0-beta.1",
        "buildTime": "2026-08-24T12:00:00Z",
        "environment": "production"
    }

@app.get("/api/health/dependencies")
def dependency_health_check():
    """Checks lightweight availability without consuming AI quotas."""
    try:
        # A lightweight query just to see if Supabase responds
        supabase.table("pantry_items").select("id").limit(1).execute()
        db_status = "ok"
    except Exception:
        db_status = "degraded"

    return {
        "status": "degraded" if db_status == "degraded" else "ok",
        "database": {"status": db_status},
        "receiptExtraction": {"status": "unknown"}, # Mocked as unknown to save quota
        "llmExplanation": {"status": "unknown"}     # Mocked as unknown to save quota
    }


# --- Recommendations Routes ---
@app.post("/api/recommendations", response_model=RecommendationResponse)
async def get_recommendations(payload: RecommendationRequest, request: Request, client: Client = Depends(get_user_supabase)):
    """Endpoint for returning deterministically ranked and semantically retrieved recipe recommendations."""
    try:
        # Basic MVP Rate Limit: Prevent abuse by checking IP (simplified for this assignment)
        client_ip = request.client.host if request.client else "unknown"
        request_counts[client_ip] = request_counts.get(client_ip, 0) + 1
        if request_counts[client_ip] > 50:
            raise HTTPException(status_code=429, detail="Too many recommendation requests. Try again later.")
        
        # 1. Fetch user's active pantry inventory
        pantry_res = client.table("pantry_items").select("*").eq("status", "active").execute()
        user_pantry = summarize_pantry(pantry_res.data)
        
        # 2. Fetch all active recipes and format candidates
        recipes_res = client.table("recipes").select("*").eq("status", "active").execute()
        ingredients_res = client.table("recipe_ingredients").select("*").execute()
        recipe_candidates = format_recipe_candidates(recipes_res.data, ingredients_res.data)

        # 3. Execute Semantic Search (if natural language query provided)
        semantic_scores = {}
        retrieval_mode = "deterministic"
        
        if payload.queryText and payload.queryText.strip():
            semantic_scores = search_recipes_semantically(client, payload.queryText, limit=20)
            if semantic_scores:
                retrieval_mode = "hybrid"

        # 4. Get Deterministic Results (This applies your hard filters and calculates scores)
        deterministic_results = rank_recipes(user_pantry, recipe_candidates, payload)

        valid_candidates = []

        # 5. Merge Semantic Scores and Calculate Hybrid Scores
        for result in deterministic_results:
            res_dict = result if isinstance(result, dict) else result.model_dump()
            recipe_id = res_dict.get("recipeId")
            
            det_score = res_dict.get("deterministicScore") or res_dict.get("score", 0)
            det_explanation = res_dict.get("deterministicExplanation") or res_dict.get("explanation", "Matched based on pantry.")
            source_name = res_dict.get("sourceName") or res_dict.get("source_name", "PantryPilot")
            
            sem_score = semantic_scores.get(recipe_id, 0)
            
            if retrieval_mode == "hybrid":
                hybrid_score = calculate_hybrid_score(det_score, sem_score)
            else:
                hybrid_score = det_score

            valid_candidates.append({
                "recipeId": recipe_id,
                "title": res_dict.get("title", "Unknown Recipe"),
                "totalMinutes": res_dict.get("totalMinutes", 0),
                "coveragePercent": res_dict.get("coveragePercent", 0),
                "matchedRequiredIngredients": res_dict.get("matchedRequiredIngredients", []),
                "missingRequiredIngredients": res_dict.get("missingRequiredIngredients", []),
                "assumedStaples": res_dict.get("assumedStaples", []),
                "deterministicScore": det_score,
                "deterministicExplanation": det_explanation,
                "semanticScore": sem_score if retrieval_mode == "hybrid" else None,
                "hybridScore": hybrid_score,
                "sourceName": source_name,
                "aiExplanation": None # Filled in Step 7
            })

        # 6. Sort the candidates
        sorted_results = sort_hybrid_results(valid_candidates)
        
        # 7. Truncate to the requested limit
        limit = payload.limit if payload.limit else 5
        final_results = sorted_results[:limit]

        # Generate explanations for the top results
        if retrieval_mode == "hybrid" and ENABLE_LLM_EXPLANATIONS:
            ai_explanations = generate_llm_explanations(final_results, payload.queryText)
            for res in final_results:
                recipe_id = res.get("recipeId")
                res["aiExplanation"] = ai_explanations.get(recipe_id, None)

        # 8. Return the strict contract requirements
        return {
            "algorithmVersion": "hybrid-v1",
            "retrievalMode": retrieval_mode,
            "queryText": payload.queryText,
            "pantryItemCount": len(user_pantry.keys()),
            "results": final_results
        }
        
    except Exception as e:
        logger.error(f"Error in recommendation engine: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate recommendations.")


# --- Inventory Routes ---
@app.get("/api/inventory")
async def get_pantry_inventory(request: Request, client: Client = Depends(get_user_supabase)):
    try:
        response = client.table("pantry_items").select("*").in_("status", ["active"]).execute()
        return response.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/inventory/{item_id}/action")
async def process_inventory_action(item_id: str, payload: InventoryActionRequest, request: Request, client: Client = Depends(get_user_supabase)):
    try:
        token = request.headers.get("Authorization", "").replace("Bearer ", "")
        user_res = client.auth.get_user(token)
        user_id = user_res.user.id

        item = client.table("pantry_items").select("*").eq("id", item_id).eq("user_id", user_id).execute()
        if not item.data:
            raise HTTPException(status_code=404, detail="Item not found")
        
        current_item = item.data[0]
        old_qty = current_item["current_quantity"]
        
        if payload.action_type == "consume":
            new_qty = max(0, old_qty - payload.amount)
            qty_delta = -payload.amount
        elif payload.action_type == "adjust":
            new_qty = payload.amount
            qty_delta = new_qty - old_qty
        else:
            raise HTTPException(status_code=400, detail="Invalid action type")

        status = "depleted" if new_qty <= 0 else "active"
        
        update_fields = {
            "current_quantity": new_qty,
            "status": status
        }
        
        if payload.action_type == "adjust" and hasattr(payload, 'unit') and payload.unit:
            update_fields["unit"] = payload.unit
            current_item["unit"] = payload.unit

        client.table("pantry_items").update(update_fields).eq("id", item_id).execute()

        client.table("inventory_events").insert({
            "user_id": user_id,
            "pantry_item_id": item_id, 
            "event_type": payload.action_type,
            "quantity_delta": qty_delta, 
            "quantity_before": old_qty,
            "quantity_after": new_qty, 
            "unit": current_item["unit"], 
            "note": payload.note
        }).execute()

        return {"success": True}
    except Exception as e:
        logger.error(f"Error modifying item {item_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/inventory/manual")
async def add_manual_item(payload: NewItemRequest, request: Request, client: Client = Depends(get_user_supabase)):
    try:
        token = request.headers.get("Authorization", "").replace("Bearer ", "")
        user_res = client.auth.get_user(token)
        user_id = user_res.user.id

        existing = client.table("pantry_items").select("*").eq("user_id", user_id).eq("name", payload.name).eq("status", "active").execute()
        
        if existing.data:
            existing_item = existing.data[0]
            new_qty = existing_item["current_quantity"] + payload.quantity
            
            item_response = client.table("pantry_items").update({
                "current_quantity": new_qty
            }).eq("id", existing_item["id"]).execute()
            new_item = item_response.data[0]

            client.table("inventory_events").insert({
                "user_id": user_id,
                "pantry_item_id": new_item["id"], 
                "event_type": "manual_add",
                "quantity_delta": payload.quantity, 
                "quantity_before": existing_item["current_quantity"],
                "quantity_after": new_qty, 
                "unit": payload.unit, 
                "note": "Added manually (consolidated)"
            }).execute()
            
        else:
            item_response = client.table("pantry_items").insert({
                "user_id": user_id,
                "name": payload.name, 
                "category": payload.category.lower() if payload.category else "pantry",
                "current_quantity": payload.quantity, 
                "unit": payload.unit,
                "purchase_date": payload.purchase_date, 
                "source_type": "manual", 
                "status": "active"
            }).execute()
            
            new_item = item_response.data[0]

            client.table("inventory_events").insert({
                "user_id": user_id,
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
        logger.error(f"Error adding manual item: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# --- Receipt Routes ---
@app.post("/api/receipts")
async def upload_receipt(request: Request, file: UploadFile = File(...), client: Client = Depends(get_user_supabase)):
    allowed_types = ["image/jpeg", "image/png", "application/pdf"]
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="File type not supported.")

    file_extension = file.filename.split(".")[-1]
    secure_filename = f"{uuid.uuid4()}.{file_extension}"
    file_path = os.path.join(UPLOAD_DIR, secure_filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    user_res = client.auth.get_user(token)
    user_id = user_res.user.id

    new_receipt = {
        "user_id": user_id,
        "original_filename": file.filename, 
        "storage_key": secure_filename, 
        "status": "processing"
    }
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
def get_receipt_review(receipt_id: str, request: Request, client: Client = Depends(get_user_supabase)):
    receipt_res = client.table("receipts").select("*").eq("id", receipt_id).execute()
    if not receipt_res.data:
        raise HTTPException(status_code=404, detail="Receipt not found")
    items_res = client.table("receipt_item_drafts").select("*").eq("receipt_id", receipt_id).order("sort_order").execute()
    return {"receipt": receipt_res.data[0], "items": items_res.data}

@app.post("/api/receipts/{receipt_id}/approve")
def approve_receipt(receipt_id: str, payload: ApprovalPayload, request: Request, client: Client = Depends(get_user_supabase)):
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


# --- User Actions Routes ---
@app.post("/api/recipes/{recipe_id}/save")
async def save_recipe(recipe_id: str, payload: SaveRecipeRequest, request: Request, client: Client = Depends(get_user_supabase)):
    try:
        token = request.headers.get("Authorization").replace("Bearer ", "")
        user_res = client.auth.get_user(token)
        user_id = user_res.user.id

        client.table("saved_recipes").upsert({
            "user_id": user_id,
            "recipe_id": recipe_id,
            "recommendation_run_id": payload.recommendationRunId
        }, on_conflict="user_id, recipe_id").execute()

        client.table("recipe_user_actions").insert({
            "user_id": user_id,
            "recipe_id": recipe_id,
            "recommendation_run_id": payload.recommendationRunId,
            "action_type": "saved"
        }).execute()

        return {"success": True, "message": "Recipe saved."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/recipes/{recipe_id}/save")
async def unsave_recipe(recipe_id: str, request: Request, client: Client = Depends(get_user_supabase)):
    try:
        token = request.headers.get("Authorization").replace("Bearer ", "")
        user_res = client.auth.get_user(token)
        user_id = user_res.user.id

        client.table("saved_recipes").delete().eq("user_id", user_id).eq("recipe_id", recipe_id).execute()

        client.table("recipe_user_actions").insert({
            "user_id": user_id,
            "recipe_id": recipe_id,
            "action_type": "unsaved"
        }).execute()

        return {"success": True, "message": "Recipe unsaved."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/recommendations/{run_id}/recipes/{recipe_id}/dismiss")
async def dismiss_recommendation(run_id: str, recipe_id: str, payload: DismissRecipeRequest, request: Request, client: Client = Depends(get_user_supabase)):
    try:
        token = request.headers.get("Authorization").replace("Bearer ", "")
        user_res = client.auth.get_user(token)
        user_id = user_res.user.id

        client.table("recipe_user_actions").insert({
            "user_id": user_id,
            "recommendation_run_id": run_id,
            "recipe_id": recipe_id,
            "action_type": "dismissed",
            "reason": payload.reason,
            "note": payload.note
        }).execute()

        return {"success": True, "message": "Recommendation dismissed."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/recipes/{recipe_id}/feedback")
async def recipe_feedback(recipe_id: str, payload: RecipeFeedbackRequest, request: Request, client: Client = Depends(get_user_supabase)):
    try:
        token = request.headers.get("Authorization").replace("Bearer ", "")
        user_res = client.auth.get_user(token)
        user_id = user_res.user.id

        client.table("recipe_user_actions").insert({
            "user_id": user_id,
            "recommendation_run_id": payload.recommendationRunId,
            "recipe_id": recipe_id,
            "action_type": payload.actionType,
            "reason": payload.reason,
            "note": payload.note
        }).execute()

        return {"success": True, "message": "Feedback recorded."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/recipes/{recipe_id}/cooking-draft")
async def generate_cooking_draft(recipe_id: str, request: Request, client: Client = Depends(get_user_supabase)):
    try:
        ingredients_res = client.table("recipe_ingredients").select("*").eq("recipe_id", recipe_id).execute()
        recipe_ingredients = ingredients_res.data
        
        pantry_res = client.table("pantry_items").select("*").eq("status", "active").execute()
        active_pantry = pantry_res.data
        
        proposal = build_consumption_proposal(recipe_id, recipe_ingredients, active_pantry)

        logger.info(json.dumps({
            "operation": "recipe_recommendation",
            "recipeId": recipe_id,
            "status": "success",
            "resultCount": len(proposal.get("items", [])),
            "fallbackUsed": False
        }))
        
        return {"success": True, "data": proposal}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/recipes/{recipe_id}/cooking-complete")
async def complete_cooking_session(recipe_id: str, payload: CookingCompleteRequest, request: Request, client: Client = Depends(get_user_supabase)):
    try:
        token = request.headers.get("Authorization").replace("Bearer ", "")
        user_res = client.auth.get_user(token)
        user_id = user_res.user.id
        
        deductions_json = [item.dict() for item in payload.deductions]

        response = client.rpc(
            "confirm_cooking_session",
            {
                "p_user_id": user_id,
                "p_recipe_id": recipe_id,
                "p_run_id": payload.recommendationRunId,
                "p_idempotency_key": payload.idempotencyKey,
                "p_deductions": deductions_json
            }
        ).execute()
        
        return response.data
        
    except Exception as e:
        error_msg = str(e)
        if "Insufficient quantity" in error_msg:
            raise HTTPException(status_code=400, detail="One or more items have insufficient quantity. Please review your inventory.")
        elif "Pantry item" in error_msg and "changed" in error_msg:
            raise HTTPException(status_code=409, detail="Your pantry inventory changed after this review was created. Please refresh.")
        raise HTTPException(status_code=500, detail=f"Database error: {error_msg}")
