import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

# Ensure this is using your service_role key to bypass RLS!
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(url, key)

def fix_ingredient_units():
    print("Fetching ingredients...")
    res = supabase.table("recipe_ingredients").select("*").execute()
    ingredients = res.data
    
    if not ingredients:
        print("No ingredients found in the database.")
        return

    updates = 0
    for ing in ingredients:
        name = ing.get("normalized_name", "")
        unit = ing.get("unit")
        qty = ing.get("quantity")
        ing_id = ing["id"]
        
        if not name:
            continue

        new_name = name
        new_unit = unit
        new_qty = qty
        
        # 1. Fix "slice" or "slices"
        if name.startswith("slice "):
            new_unit = "slice"
            new_name = name.replace("slice ", "", 1)
        elif name.startswith("slices "):
            new_unit = "slice"
            new_name = name.replace("slices ", "", 1)
            
        # 2. Fix "can" or "cans"
        elif name.startswith("can "):
            new_unit = "can"
            new_name = name.replace("can ", "", 1)
        elif name.startswith("cans "):
            new_unit = "can"
            new_name = name.replace("cans ", "", 1)
            
        # 3. Fix "pinch of" (and handle missing quantity)
        elif name.startswith("pinch of "):
            new_unit = "pinch"
            new_name = name.replace("pinch of ", "", 1)
            if not new_qty or new_qty == 0:
                new_qty = 0.125 # Arbitrary small amount so math doesn't fail
        
        # If a change was detected, update the database
        if new_name != name:
            print(f"🛠️ Fixing: '{name}' -> Name: '{new_name}', Unit: '{new_unit}', Qty: {new_qty}")
            supabase.table("recipe_ingredients").update({
                "normalized_name": new_name.strip(),
                "unit": new_unit,
                "quantity": new_qty
            }).eq("id", ing_id).execute()
            updates += 1
            
    print(f"\n✅ Done! Cleaned up {updates} edge-case ingredients.")

if __name__ == "__main__":
    fix_ingredient_units()