import os
import requests
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

# Initialize Supabase
supabase: Client = create_client(os.environ.get("SUPABASE_URL", ""), os.environ.get("SUPABASE_KEY", ""))

print("Fetching recipes...")

# TheMealDB allows searching by first letter on their free tier (API key '1')
alphabet = "abcdefghijklmnopqrstuvwxyz"
total_added = 0

for letter in alphabet:
    response = requests.get(f"https://www.themealdb.com/api/json/v1/1/search.php?f={letter}")
    data = response.json()
    
    if not data.get("meals"):
        continue
        
    for meal in data["meals"]:
        try:
            # 1. Insert Recipe
            recipe_res = supabase.table("recipes").insert({
                "title": meal["strMeal"],
                "prep_minutes": 15, # API doesn't provide times, using defaults
                "cook_minutes": 30,
                "source_name": "TheMealDB",
                "status": "active",
                "instructions": [step.strip() for step in meal["strInstructions"].split("\r\n") if step.strip()],
                "description": f"A traditional {meal['strArea']} {meal['strCategory']} dish."
            }).execute()
            
            recipe_id = recipe_res.data[0]["id"]
            
            # 2. Extract and format ingredients (TheMealDB uses strIngredient1 through strIngredient20)
            ingredients = []
            for i in range(1, 21):
                ing_name = meal.get(f"strIngredient{i}")
                ing_measure = meal.get(f"strMeasure{i}")
                
                if ing_name and ing_name.strip():
                    ingredients.append({
                        "recipe_id": recipe_id,
                        "raw_text": f"{ing_measure} {ing_name}".strip(),
                        "normalized_name": ing_name.strip().lower(),
                        "quantity": 1, # Placeholder for your normalization engine
                        "unit": ing_measure.strip() if ing_measure and ing_measure.strip() else "each",
                        "sort_order": i
                    })
            
            # 3. Insert Ingredients
            if ingredients:
                supabase.table("recipe_ingredients").insert(ingredients).execute()
                
            total_added += 1
            print(f"Successfully added: {meal['strMeal']}")
            
        except Exception as e:
            print(f"Skipped {meal.get('strMeal')} due to error: {e}")

print(f"\nComplete! Bulk imported {total_added} recipes to your database.")