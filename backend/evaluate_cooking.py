import requests
import uuid
from supabase import create_client, Client

# --- Configuration ---
API_URL = "http://127.0.0.1:8000/api"
TEST_RECIPE_ID = "002539eb-2914-4e0d-acdf-01c3d2b21bfa" # Put a valid recipe ID from your database here

# Fill these in with your Supabase details and test account
SUPABASE_URL = "https://zcgswnockjwttpiqsrvj.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InpjZ3N3bm9ja2p3dHRwaXFzcnZqIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4NTAxNDIwNiwiZXhwIjoyMTAwNTkwMjA2fQ.iqoaKBMyyvSc9fZXnFqzQ0XgoNjmsjJT9FqiuEfsrZ4"
TEST_EMAIL = "test@t.com"
TEST_PASSWORD = "test"

def run_cooking_test():
    print("🔐 Logging into Supabase to get user token...")
    
    # 1. Automatically log in to get the token
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    try:
        auth_response = supabase.auth.sign_in_with_password({
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        })
        token = auth_response.session.access_token
        print("✅ Successfully logged in!\n")
    except Exception as e:
        print(f"❌ Login failed: {e}")
        print("Check your email, password, and Supabase keys.")
        return

    HEADERS = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }

    # 2. Test 1: Save Recipe
    print("--- Test 1: Save Recipe ---")
    res = requests.post(f"{API_URL}/recipes/{TEST_RECIPE_ID}/save", json={"recommendationRunId": None}, headers=HEADERS)
    print(f"Status: {res.status_code} - {res.text}\n")
    
    # 3. Test 2: Generate Cooking Draft
    print("--- Test 2: Generate Cooking Draft ---")
    res = requests.post(f"{API_URL}/recipes/{TEST_RECIPE_ID}/cooking-draft", headers=HEADERS)
    print(f"Status: {res.status_code}")
    
    if res.status_code != 200:
        print(f"Failed to generate draft: {res.text}")
        return
        
    draft_data = res.json().get("data", {})
    items = draft_data.get("items", [])
    print(f"Draft generated with {len(items)} items.\n")
    
    valid_deductions = []
    for item in items:
        if item.get("pantryItemId") and item.get("proposedQuantity"):
            valid_deductions.append({
                "pantryItemId": item["pantryItemId"],
                "recipeIngredientId": item.get("recipeIngredientId"),
                "quantity": item["proposedQuantity"],
                "unit": item["unit"]
            })
            
    if not valid_deductions:
        print("No valid pantry matches found to deduct. Add some matching inventory to test the transaction!")
        return
        
    # 4. Test 3: Complete Cooking Session (Atomic Update)
    print("--- Test 3: Complete Cooking Session ---")
    payload = {
        "idempotencyKey": str(uuid.uuid4()),
        "recommendationRunId": None,
        "deductions": valid_deductions
    }
    
    res = requests.post(f"{API_URL}/recipes/{TEST_RECIPE_ID}/cooking-complete", json=payload, headers=HEADERS)
    print(f"Status: {res.status_code} - {res.text}\n")
    
    # 5. Test 4: Duplicate Submission Protection (Idempotency)
    print("--- Test 4: Idempotency Check (Duplicate Click) ---")
    res_dup = requests.post(f"{API_URL}/recipes/{TEST_RECIPE_ID}/cooking-complete", json=payload, headers=HEADERS)
    print(f"Status: {res_dup.status_code} - {res_dup.text}")
    if "already completed" in res_dup.text:
        print("✅ PASS: Duplicate submission prevented.")
    else:
        print("❌ FAIL: Duplicate submission allowed.")

if __name__ == "__main__":
    run_cooking_test()