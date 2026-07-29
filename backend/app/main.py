import os
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from supabase import create_client, Client
from app.core.config import settings

load_dotenv()

app = FastAPI(title=settings.PROJECT_NAME)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Supabase client using your .env variables
url: str = os.environ.get("SUPABASE_URL", "")
key: str = os.environ.get("SUPABASE_KEY", "")
supabase: Client = create_client(url, key)

# Pydantic model validates the input data automatically
class InventoryItem(BaseModel):
    item_name: str
    quantity: int

@app.get("/api/inventory")
def get_inventory():
    try:
        response = supabase.table("inventory").select("*").execute()
        return response.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/inventory", status_code=201)
def add_inventory(item: InventoryItem):
    # Reject invalid data
    if item.quantity <= 0:
        raise HTTPException(status_code=422, detail="Quantity must be greater than 0")
    
    try:
        data = {"item_name": item.item_name, "quantity": item.quantity}
        response = supabase.table("inventory").insert(data).execute()
        return response.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))