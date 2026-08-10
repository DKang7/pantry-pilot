import json
import os
import re
import hashlib
from supabase import create_client, Client

# Initialize Supabase (Use SERVICE_ROLE_KEY here to bypass RLS for importing)
SUPABASE_URL = "https://zcgswnockjwttpiqsrvj.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InpjZ3N3bm9ja2p3dHRwaXFzcnZqIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc4NTAxNDIwNiwiZXhwIjoyMTAwNTkwMjA2fQ.iqoaKBMyyvSc9fZXnFqzQ0XgoNjmsjJT9FqiuEfsrZ4"

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Missing Supabase credentials in environment.")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Normalization Lookups
UNIT_ALIASES = {
    "tablespoon": "tbsp", "tablespoons": "tbsp", "tbsp.": "tbsp",
    "teaspoon": "tsp", "teaspoons": "tsp",
    "cups": "cup", "ounces": "oz", "pounds": "lb",
    "grams": "g", "kilograms": "kg"
}

PREP_WORDS = ["diced", "chopped", "sliced", "minced", "grated", "peeled", "drained", "rinsed", "softened", "melted", "finely"]

def get_aliases():
    """Fetch ingredient aliases from the database."""
    res = supabase.table("ingredient_aliases").select("*").execute()
    return {row["alias"].lower(): row["canonical_name"].lower() for row in res.data}

def parse_quantity(text):
    """Extracts leading numbers, decimals, or fractions (e.g., '1 1/2', '0.5')."""
    match = re.match(r'^(\d+\s+\d+/\d+|\d+/\d+|\d+(\.\d+)?)', text)
    if match:
        qty_str = match.group(1).strip()
        try:
            if ' ' in qty_str and '/' in qty_str:
                whole, frac = qty_str.split(' ')
                num, den = frac.split('/')
                return float(whole) + (float(num) / float(den)), text[match.end():].strip()
            elif '/' in qty_str:
                num, den = qty_str.split('/')
                return float(num) / float(den), text[match.end():].strip()
            return float(qty_str), text[match.end():].strip()
        except:
            pass
    return None, text

def parse_ingredient_line(raw_text, db_aliases):
    """Pipeline to parse and normalize a single ingredient line."""
    parsed = {
        "raw_text": raw_text,
        "normalized_name": None,
        "quantity": None,
        "unit": None,
        "preparation": None,
        "optional": "optional" in raw_text.lower()
    }
    
    # Clean up whitespace
    text = re.sub(r'\s+', ' ', raw_text.strip().lower())
    
    # 1. Parse Quantity
    qty, remaining = parse_quantity(text)
    parsed["quantity"] = qty
    
    # 2. Extract Preparation Words
    prep_found = []
    for word in PREP_WORDS:
        if word in remaining:
            prep_found.append(word)
            remaining = remaining.replace(word, "").strip()
    if prep_found:
        parsed["preparation"] = " ".join(prep_found).strip()

    # Clean punctuation
    remaining = remaining.replace(',', '').replace('.', '').strip()

    # 3. Parse Unit
    words = remaining.split(' ')
    if words and words[0] in UNIT_ALIASES:
        parsed["unit"] = UNIT_ALIASES[words[0]]
        remaining = " ".join(words[1:]).strip()
    elif words and words[0] in UNIT_ALIASES.values():
        parsed["unit"] = words[0]
        remaining = " ".join(words[1:]).strip()
        
    # Remove obvious plurals if no exact match (basic fallback)
    if remaining.endswith('s') and not remaining.endswith('ss'):
        singular = remaining[:-1]
    else:
        singular = remaining

    # 4. Alias Mapping
    # Apply database mapping, otherwise use the cleaned string
    parsed["normalized_name"] = db_aliases.get(remaining, db_aliases.get(singular, singular))
    
    return parsed

def generate_content_hash(source_id, title):
    """Generates a stable hash to prevent duplicate imports."""
    raw = f"{source_id}-{title}".lower().encode('utf-8')
    return hashlib.sha256(raw).hexdigest()

def run_import(filepath):
    db_aliases = get_aliases()
    
    with open(filepath, 'r') as f:
        recipes_data = json.load(f)

    stats = {
        "read": len(recipes_data), "imported": 0, "skipped": 0, 
        "failed": 0, "ingredients": 0
    }

    for recipe in recipes_data:
        try:
            # Validate basic rules
            if not recipe.get("title") or len(recipe.get("ingredients", [])) < 2:
                stats["failed"] += 1
                continue

            content_hash = generate_content_hash(recipe.get("sourceExternalId", ""), recipe["title"])
            
            # Check for duplicates using the content hash
            existing = supabase.table("recipes").select("id").eq("content_hash", content_hash).execute()
            if existing.data:
                stats["skipped"] += 1
                continue

            # Insert Recipe
            new_recipe = {
                "source_external_id": recipe.get("sourceExternalId"),
                "title": recipe["title"],
                "description": recipe.get("description"),
                "instructions": recipe.get("instructions", []),
                "prep_minutes": recipe.get("prepMinutes"),
                "cook_minutes": recipe.get("cookMinutes"),
                "servings": recipe.get("servings"),
                "cuisine": recipe.get("cuisine"),
                "source_name": recipe.get("source", {}).get("name", "Unknown"),
                "source_url": recipe.get("source", {}).get("url"),
                "license_note": recipe.get("source", {}).get("license"),
                "content_hash": content_hash,
                "status": "active"
            }
            
            recipe_res = supabase.table("recipes").insert(new_recipe).execute()
            recipe_id = recipe_res.data[0]["id"]
            stats["imported"] += 1

            # Parse and Insert Ingredients
            parsed_ingredients = []
            for i, raw_line in enumerate(recipe["ingredients"]):
                if not raw_line.strip():
                    continue
                parsed = parse_ingredient_line(raw_line, db_aliases)
                parsed["recipe_id"] = recipe_id
                parsed["sort_order"] = i
                parsed_ingredients.append(parsed)
            
            if parsed_ingredients:
                supabase.table("recipe_ingredients").insert(parsed_ingredients).execute()
                stats["ingredients"] += len(parsed_ingredients)

        except Exception as e:
            print(f"Error importing {recipe.get('title', 'Unknown')}: {e}")
            stats["failed"] += 1

    print("\n--- Import Summary ---")
    print(f"Recipes read: {stats['read']}")
    print(f"Recipes imported: {stats['imported']}")
    print(f"Recipes skipped as duplicates: {stats['skipped']}")
    print(f"Recipes failed: {stats['failed']}")
    print(f"Ingredients imported: {stats['ingredients']}")

if __name__ == "__main__":
    # Adjust path if your JSON is located elsewhere
    target_file = "data/recipes/raw/recipes-v1.json"
    run_import(target_file)