import json
from pydantic import BaseModel
from typing import List, Dict, Optional
from app.models import RecommendationRequest
from google import genai
import os

genai_client = genai.Client()

def search_recipes_semantically(supabase, query_text: str, limit: int = 20) -> dict:
    """
    Generates a query embedding and retrieves semantic candidates from Supabase.
    Returns a dictionary mapping recipe_id -> semantic_score.
    """
    # Empty query: skip semantic search[cite: 1]
    if not query_text or not query_text.strip():
        return {}
        
    try:
        # Generate query embedding using the same model and dimensions[cite: 1]
        response = genai_client.models.embed_content(
            model='gemini-embedding-001',
            contents=query_text,
            config={'output_dimensionality': 768}
        )
        query_embedding = response.embeddings[0].values
        
        # Search recipe vectors via Supabase RPC[cite: 1]
        res = supabase.rpc(
            "match_recipe_embeddings", 
            {"query_embedding": query_embedding, "match_count": limit}
        ).execute()
        
        # Map the results to a dictionary of {recipe_id: semantic_score}
        return {row["recipe_id"]: row["semantic_score"] for row in res.data}
        
    except Exception as e:
        # Log safe internal error and trigger deterministic fallback[cite: 1]
        print(f"Semantic search failed: {e}")
        return {}


DEFAULT_STAPLES = ["water", "salt", "black pepper", "cooking oil", "olive oil"]

def summarize_pantry(pantry_data: List[dict]) -> Dict[str, dict]:
    summary = {}
    for item in pantry_data:
        if item.get("status") != "active" or item.get("current_quantity", 0) <= 0:
            continue
            
        name = item.get("name", "").lower()
        if not name:
            continue

        if name not in summary:
            summary[name] = {
                "normalizedName": name,
                "available": True,
                "sources": []
            }
        
        summary[name]["sources"].append({
            "pantryItemId": item["id"],
            "quantity": item["current_quantity"],
            "unit": item.get("unit")
        })
    return summary

def format_recipe_candidates(recipes_data: List[dict], ingredients_data: List[dict]) -> List[dict]:
    candidates = []
    ing_map = {}
    
    for ing in ingredients_data:
        r_id = ing["recipe_id"]
        if r_id not in ing_map:
            ing_map[r_id] = {"required": [], "optional": []}
            
        norm_name = ing.get("normalized_name")
        if not norm_name:
            continue
            
        if ing.get("optional", False):
            if norm_name not in ing_map[r_id]["optional"]:
                ing_map[r_id]["optional"].append(norm_name)
        else:
            if norm_name not in ing_map[r_id]["required"]:
                ing_map[r_id]["required"].append(norm_name)

    for r in recipes_data:
        r_id = r["id"]
        candidates.append({
            "recipeId": r_id,
            "title": r["title"],
            "requiredIngredients": ing_map.get(r_id, {}).get("required", []),
            "optionalIngredients": ing_map.get(r_id, {}).get("optional", []),
            "totalMinutes": r.get("total_minutes") or (r.get("prep_minutes") or 0) + (r.get("cook_minutes") or 0),
            "mealTypes": r.get("meal_types", []),
            "dietaryTags": r.get("dietary_tags", []),
            "sourceName": r.get("source_name"),
            "sourceUrl": r.get("source_url"),
            "instructions": r.get("instructions")
        })
        
    return candidates

def rank_recipes(pantry: Dict[str, dict], recipes: List[dict], request: RecommendationRequest) -> List[dict]:
    results = []
    assume_staples = request.assumeStaples
    
    for recipe in recipes:
        req_ingredients = recipe.get("requiredIngredients", [])
        opt_ingredients = recipe.get("optionalIngredients", [])
        
        if not req_ingredients:
            continue
        
        matched_req = []
        missing_req = []
        assumed_staples_used = []
        matched_opt = []
        missing_opt = []
        priority_used = []
        
        for ing in req_ingredients:
            if ing in pantry and pantry[ing]["available"]:
                matched_req.append(ing)
                if ing in request.prioritizeIngredients:
                    priority_used.append(ing)
            elif assume_staples and ing in DEFAULT_STAPLES:
                assumed_staples_used.append(ing)
            else:
                missing_req.append(ing)
                
        for ing in opt_ingredients:
            if ing in pantry and pantry[ing]["available"]:
                matched_opt.append(ing)
            else:
                missing_opt.append(ing)

        if request.maxMissingIngredients is not None:
            if len(missing_req) > request.maxMissingIngredients:
                continue
                
        if request.excludeIngredients:
            has_excluded = any(
                ex in req_ingredients or ex in opt_ingredients 
                for ex in request.excludeIngredients
            )
            if has_excluded:
                continue

        recipe_time = recipe.get("totalMinutes")
        if request.maxTotalMinutes is not None:
            if recipe_time is None or recipe_time > request.maxTotalMinutes:
                continue

        if request.mealTypes:
            recipe_meals = recipe.get("mealTypes", [])
            if not any(m in recipe_meals for m in request.mealTypes):
                continue
                
        non_staple_req_count = len(req_ingredients) - len(assumed_staples_used)
        coverage_ratio = len(matched_req) / non_staple_req_count if non_staple_req_count > 0 else 1.0
        coverage_points = coverage_ratio * 70

        priority_points = 0.0
        if request.prioritizeIngredients:
            priority_ratio = len(priority_used) / len(request.prioritizeIngredients)
            priority_points = priority_ratio * 15
            
        time_points = 0.0
        if request.maxTotalMinutes and recipe_time:
            time_fit = 1.0 - (recipe_time / request.maxTotalMinutes)
            time_points = max(0.0, min(1.0, time_fit)) * 10
            
        optional_points = 0.0
        if opt_ingredients:
            optional_ratio = len(matched_opt) / len(opt_ingredients)
            optional_points = optional_ratio * 5
            
        total_score = coverage_points + priority_points + time_points + optional_points
        
        explanation = f"Matches {len(matched_req)} of {non_staple_req_count} required non-staple ingredients."
        if priority_used:
            explanation += f" Uses {len(priority_used)} priority ingredients."
        if missing_req:
            explanation += f" Missing: {', '.join(missing_req)}."
            
        results.append({
            "recipeId": recipe["recipeId"],
            "title": recipe["title"],
            "score": total_score,
            "coveragePercent": round(coverage_ratio * 100),
            "totalMinutes": recipe_time,
            "matchedRequiredIngredients": matched_req,
            "missingRequiredIngredients": missing_req,
            "assumedStaples": assumed_staples_used,
            "missingOptionalIngredients": missing_opt,
            "priorityIngredientsUsed": priority_used,
            "quantityWarnings": ["Quantity sufficiency has not been verified."] if matched_req else [],
            "scoreBreakdown": {
                "pantryCoverage": round(coverage_points, 2),
                "priorityIngredientUsage": round(priority_points, 2),
                "timeFit": round(time_points, 2),
                "optionalCoverage": round(optional_points, 2)
            },
            "explanation": explanation
        })

    results.sort(key=lambda x: (
        -x["score"],
        -x["coveragePercent"],
        -len(x["priorityIngredientsUsed"]),
        len(x["missingRequiredIngredients"]),
        x["totalMinutes"] or 9999,
        x["title"],
        x["recipeId"]
    ))
    
    limited_results = results[:request.limit]
    for r in limited_results:
        r["score"] = round(r["score"])
        
    return limited_results

def calculate_hybrid_score(deterministic_score: float, semantic_score: float) -> float:
    """Calculates the hybrid score with a 70/30 weight split."""
    # If there is no semantic score (e.g., deterministic fallback), just use the deterministic score.
    if semantic_score is None:
        return deterministic_score
        
    hybrid = (deterministic_score * 0.70) + (semantic_score * 0.30)
    return round(hybrid, 1)

def sort_hybrid_results(results: list) -> list:
    """Sorts candidate recipes according to the strict Day 10 ranking rules."""
    return sorted(
        results,
        key=lambda r: (
            r.get("hybridScore", 0) or 0,              # 1. Higher hybrid score
            r.get("deterministicScore", 0),            # 2. Higher deterministic score[cite: 1]
            -len(r.get("missingRequiredIngredients", [])), # 3. Fewer missing required ingredients (negative to sort ascending)[cite: 1]
            r.get("semanticScore", 0) or 0,            # 4. Higher semantic score[cite: 1]
            -r.get("totalMinutes", 999),               # 5. Shorter total time (negative to sort ascending)[cite: 1]
            r.get("title", ""),                        # 6. Alphabetical recipe title (reversed logically, but standard alphabetical is fine)[cite: 1]
            r.get("recipeId", "")                      # 7. Recipe ID[cite: 1]
        ),
        reverse=True # We reverse because we want the highest scores first
    )

class RecipeExplanation(BaseModel):
    recipeId: str
    whyRecommended: str
    caveats: List[str]

class ExplanationResponse(BaseModel):
    results: List[RecipeExplanation]

def generate_llm_explanations(top_results: list, query_text: str) -> dict:
    """
    Generates grounded explanations for the top 3 results using Gemini.
    Returns a dict mapping recipeId -> aiExplanation string.
    """
    if not query_text or not query_text.strip() or not top_results:
        return {}

    # 1. Prepare the strict evidence (only for the top 3 recipes)[cite: 1]
    evidence = []
    for res in top_results[:3]:
        evidence.append({
            "recipeId": res.get("recipeId"),
            "title": res.get("title"),
            "matchedIngredients": res.get("matchedRequiredIngredients", []),
            "missingIngredients": res.get("missingRequiredIngredients", []),
            "assumedStaples": res.get("assumedStaples", []),
            "totalMinutes": res.get("totalMinutes", 0)
        })

    # 2. Build the strict prompt[cite: 1]
    prompt = f"""
    You are a helpful AI assistant for PantryPilot. Explain why these recipes were recommended.
    User's natural language request: "{query_text}"

    Here is the strict evidence for the top recommendations:
    {json.dumps(evidence, indent=2)}

    Rules:
    1. Reference only facts provided in the evidence.
    2. Mention important missing ingredients.
    3. Do not claim that a quantity is sufficient unless verified.
    4. Do not invent new ingredients, recipes, or health/safety guarantees.
    5. Be concise (1-2 sentences).
    """

    try:
        # 3. Request schema-validated JSON from Gemini[cite: 1]
        client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config={
                'response_mime_type': 'application/json',
                'response_schema': ExplanationResponse,
                'temperature': 0.1 # Keep it highly deterministic
            }
        )
        
        # 4. Parse the response and map it to the recipe IDs[cite: 1]
        parsed_response = json.loads(response.text)
        explanations_map = {}
        for item in parsed_response.get("results", []):
            explanations_map[item["recipeId"]] = item["whyRecommended"]
            
        return explanations_map
        
    except Exception as e:
        print(f"LLM Explanation generation failed (falling back to deterministic): {e}")
        return {}

def build_consumption_proposal(recipe_id: str, recipe_ingredients: list, pantry_items: list) -> dict:
    """
    Generates a deterministic draft of pantry deductions by matching recipe ingredients 
    to active pantry records.
    """
    proposal = {
        "recipeId": recipe_id,
        "items": [],
        "warnings": []
    }
    
    # Group pantry records by normalized name
    pantry_map = {}
    for item in pantry_items:
        name = (item.get("normalized_name") or item.get("name", "")).lower().strip()
        if name not in pantry_map:
            pantry_map[name] = []
        pantry_map[name].append(item)
        
    for name, items in pantry_map.items():
        # Sort by oldest purchase date first to suggest older matching inventory
        items.sort(key=lambda x: x.get("purchase_date") or "")
        
    for ri in recipe_ingredients:
        req_name = (ri.get("normalized_name") or ri.get("name", "")).lower().strip()
        req_qty = ri.get("quantity", 0)
        req_unit = (ri.get("unit") or "").lower().strip()
        
        matches = pantry_map.get(req_name, [])
        
        # Handle Missing Ingredient[cite: 2]
        if not matches:
            proposal["items"].append({
                "recipeIngredientId": ri.get("id"),
                "ingredientName": req_name,
                "pantryItemId": None,
                "currentQuantity": 0,
                "proposedQuantity": None,
                "unit": req_unit,
                "remainingQuantity": 0,
                "included": False,
                "matchingStatus": "missing"
            })
            continue
            
        # Select the oldest matching record
        selected_pantry = matches[0]
        pantry_qty = selected_pantry.get("current_quantity", 0)
        pantry_unit = (selected_pantry.get("unit") or "").lower().strip()
        
        # Evaluate unit compatibility[cite: 2]
        if req_unit == pantry_unit:
            status = "exact_match"
            proposed = req_qty
            remaining = max(0, pantry_qty - proposed)
            included = True
        else:
            status = "unit_incompatible"
            proposed = None
            remaining = pantry_qty
            included = False
            proposal["warnings"].append(f"'{req_name}' requires manual confirmation because the recipe and pantry units do not match.")
            
        proposal["items"].append({
            "recipeIngredientId": ri.get("id"),
            "ingredientName": req_name,
            "pantryItemId": selected_pantry.get("id"),
            "currentQuantity": pantry_qty,
            "proposedQuantity": proposed,
            "unit": pantry_unit if status == "unit_incompatible" else req_unit,
            "remainingQuantity": remaining,
            "included": included,
            "matchingStatus": status
        })
        
    return proposal