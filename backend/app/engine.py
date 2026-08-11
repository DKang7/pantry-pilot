from typing import List, Dict
from app.models import RecommendationRequest

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
            "sourceName": r.get("source_name")
        })
        
    return candidates

def rank_recipes(pantry: Dict[str, dict], recipes: List[dict], request: RecommendationRequest) -> List[dict]:
    results = []
    assume_staples = request.assumeStaples
    
    for recipe in recipes:
        req_ingredients = recipe.get("requiredIngredients", [])
        opt_ingredients = recipe.get("optionalIngredients", [])
        
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