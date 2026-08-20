import os
import hashlib
from dotenv import load_dotenv
from supabase import create_client, Client
from google import genai

load_dotenv()

# Initialize Admin Supabase Client (bypasses RLS)
url: str = os.environ.get("SUPABASE_URL", "")
key: str = os.environ.get("SUPABASE_KEY", "")
supabase: Client = create_client(url, key)

# Initialize Gemini Client
genai_client = genai.Client()

def generate_content_hash(text: str) -> str:
    """Creates a stable hash of the recipe text to prevent redundant embedding."""
    return hashlib.sha256(text.encode('utf-8')).hexdigest()

def build_embedding_text(recipe: dict, ingredients: list) -> str:
    """Constructs a stable text representation of the recipe[cite: 2]."""
    text_parts = [
        f"Title: {recipe.get('title', '')}",
        f"Description: {recipe.get('description', '')}",
        f"Cuisine: {recipe.get('cuisine', 'Unknown')}",
        f"Meal types: {', '.join(recipe.get('meal_types', []))}",
        f"Dietary tags: {', '.join(recipe.get('dietary_tags', []))}",
        "Ingredients:"
    ]
    
    for ing in ingredients:
        name = ing.get('normalized_name', '')
        if name:
            text_parts.append(f"- {name}")
            
    text_parts.append(f"Preparation: {recipe.get('prep_instructions_summary', f'Ready in {recipe.get('total_minutes', 0)} minutes.')}")
    
    return "\n".join(text_parts)

def run_embedding_job():
    print("Fetching active recipes and ingredients...")
    
    # 1. Load active recipes[cite: 2]
    recipes_res = supabase.table("recipes").select("*").eq("status", "active").execute()
    ingredients_res = supabase.table("recipe_ingredients").select("*").execute()
    
    recipes = recipes_res.data
    ingredients = ingredients_res.data
    
    if not recipes:
        print("No active recipes found.")
        return

    # Group ingredients by recipe_id
    ing_map = {}
    for ing in ingredients:
        r_id = ing["recipe_id"]
        if r_id not in ing_map:
            ing_map[r_id] = []
        ing_map[r_id].append(ing)

    # 2. Check existing embeddings to avoid redundant work[cite: 2]
    existing_embeddings_res = supabase.table("recipe_embeddings").select("recipe_id, content_hash").execute()
    existing_map = {row["recipe_id"]: row["content_hash"] for row in existing_embeddings_res.data}

    stats = {"active": len(recipes), "current": 0, "generated": 0, "failed": 0}

    for recipe in recipes:
        recipe_id = recipe["id"]
        recipe_ings = ing_map.get(recipe_id, [])
        
        # 3. Build stable embedding text and hash[cite: 2]
        embedding_text = build_embedding_text(recipe, recipe_ings)
        content_hash = generate_content_hash(embedding_text)
        
        # 4. Check if embedding already exists and is up to date[cite: 2]
        if recipe_id in existing_map and existing_map[recipe_id] == content_hash:
            stats["current"] += 1
            continue
            
        print(f"Generating embedding for: {recipe.get('title')}")
        
        try:
            # 5. Generate embedding using the current Gemini model (forced to 768 dimensions)
            response = genai_client.models.embed_content(
                model='gemini-embedding-001',
                contents=embedding_text,
                config={'output_dimensionality': 768}
            )
            vector = response.embeddings[0].values
            
            # 6. Store the vector and metadata
            data = {
                "recipe_id": recipe_id,
                "embedding": vector,
                "embedding_model": "gemini-embedding-001",
                "embedding_dimensions": 768,
                "content_hash": content_hash,
                "embedding_text": embedding_text,
                "status": "completed"
            }
            
            # Upsert logic (if it exists but hash changed, we update)
            if recipe_id in existing_map:
                supabase.table("recipe_embeddings").update(data).eq("recipe_id", recipe_id).execute()
            else:
                supabase.table("recipe_embeddings").insert(data).execute()
                
            stats["generated"] += 1
            
        except Exception as e:
            print(f"Failed to embed recipe {recipe_id}: {str(e)}")
            stats["failed"] += 1
            # 7. Record failures[cite: 2]
            supabase.table("recipe_embeddings").insert({
                "recipe_id": recipe_id,
                "status": "failed",
                "content_hash": content_hash
            }).execute()

    # 8. Print summary[cite: 2]
    print("\n--- Embedding Job Summary ---")
    print(f"Active recipes: {stats['active']}")
    print(f"Already current: {stats['current']}")
    print(f"Embeddings generated: {stats['generated']}")
    print(f"Embeddings failed: {stats['failed']}")

if __name__ == "__main__":
    run_embedding_job()