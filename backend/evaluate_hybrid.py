import requests
import time

API_URL = "http://127.0.0.1:8000/api/recommendations"
# Replace with your actual valid token from your frontend local storage for testing
# Or temporarily remove the auth dependency in main.py for the evaluation run
HEADERS = {"Content-Type": "application/json"} 

test_cases = [
    {
        "name": "Mood/Style - Comforting",
        "payload": {"queryText": "Something comforting.", "limit": 3}
    },
    {
        "name": "Cuisine/Format - Mediterranean",
        "payload": {"queryText": "Something Mediterranean-inspired.", "limit": 3}
    },
    {
        "name": "Constraint Combination - Quick Vegetarian",
        "payload": {"queryText": "A comforting vegetarian dinner.", "maxTotalMinutes": 30, "limit": 3}
    },
    {
        "name": "Impossible Request - Exclude Override Test",
        "payload": {"queryText": "A peanut recipe", "excludeIngredients": ["peanut"], "limit": 3}
    },
    {
        "name": "Deterministic Fallback - Empty Query",
        "payload": {"queryText": "", "maxMissingIngredients": 1, "limit": 3}
    }
]

def run_evaluations():
    print("🚀 Starting Hybrid Recommendation Evaluation...\n")
    
    total_latency = 0
    violations = 0
    
    for case in test_cases:
        print(f"--- Test Case: {case['name']} ---")
        
        start_time = time.time()
        response = requests.post(API_URL, json=case["payload"], headers=HEADERS)
        end_time = time.time()
        
        latency_ms = (end_time - start_time) * 1000
        total_latency += latency_ms
        
        if response.status_code != 200:
            print(f"❌ Error: {response.status_code} - {response.text}\n")
            continue
            
        data = response.json()
        results = data.get("results", [])
        
        print(f"Latency: {latency_ms:.0f} ms")
        print(f"Retrieval Mode: {data.get('retrievalMode')}")
        print(f"Results returned: {len(results)}")
        
        # Check Hard Filter Violations (Exclude override test)
        if "excludeIngredients" in case["payload"]:
            excluded = case["payload"]["excludeIngredients"]
            for res in results:
                # Check if any excluded ingredient made it into the matched list
                if any(ex in res["matchedRequiredIngredients"] for ex in excluded):
                    violations += 1
                    print(f"❌ VIOLATION: Excluded ingredient found in recipe {res['recipeId']}")
        
        if results:
            top_recipe = results[0]
            print(f"Top Match: {top_recipe['title']} (Hybrid Score: {top_recipe.get('hybridScore')})")
            if top_recipe.get("aiExplanation"):
                print(f"Explanation: {top_recipe['aiExplanation']}")
        else:
            print("Top Match: None (Expected for strict constraints without matches)")
            
        print("\n")
        
    print("=== Evaluation Summary ===")
    print(f"Average Latency: {total_latency / len(test_cases):.0f} ms")
    print(f"Hard Filter Violations: {violations}")
    if violations == 0:
        print("✅ PASS: Semantic search did not override hard constraints.")
    else:
        print("❌ FAIL: Hard constraints were violated.")

if __name__ == "__main__":
    run_evaluations()
