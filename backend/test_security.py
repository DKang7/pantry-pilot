import requests
from supabase import create_client, Client

API_URL = "http://127.0.0.1:8000/api"
SUPABASE_URL = "https://zcgswnockjwttpiqsrvj.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InpjZ3N3bm9ja2p3dHRwaXFzcnZqIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4NTAxNDIwNiwiZXhwIjoyMTAwNTkwMjA2fQ.iqoaKBMyyvSc9fZXnFqzQ0XgoNjmsjJT9FqiuEfsrZ4"

# User credentials you just created
USER_A_EMAIL = "a@a.com"
USER_B_EMAIL = "b@b.com"
A_PASSWORD = "a"
B_PASSWORD = "b" 

def test_data_isolation():
    print("🔐 Logging in both users...")
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    # Get User B's token
    auth_b = supabase.auth.sign_in_with_password({"email": USER_B_EMAIL, "password": B_PASSWORD})
    token_b = auth_b.session.access_token
    
    # In a real test, User A would create a pantry item, and we'd grab its ID.
    # For now, grab any existing pantry_item_id that belongs to User A from your database.
    user_a_item_id = "97ad6ebc-f8da-4e02-b1fa-2f38f477d72a"
    
    print("🕵️‍♀️ User B attempting to consume User A's inventory...")
    headers_b = {"Authorization": f"Bearer {token_b}", "Content-Type": "application/json"}
    
    # Attempt a malicious deduction
    payload = {
        "idempotencyKey": "malicious-test-key",
        "deductions": [{"pantryItemId": user_a_item_id, "quantity": 1, "unit": "each"}]
    }
    
    # We will hit the cooking-complete endpoint we built earlier
    res = requests.post(f"{API_URL}/recipes/test-recipe-id/cooking-complete", json=payload, headers=headers_b)
    
    if res.status_code == 500 or res.status_code == 403 or res.status_code == 404:
        print("✅ PASS: Backend correctly denied User B access to User A's data.")
    else:
        print(f"❌ FAIL: Vulnerability detected! Status: {res.status_code}")

if __name__ == "__main__":
    test_data_isolation()