import json
import requests

# Ensure your backend is running locally before executing this script
API_URL = "http://localhost:8000/api/recommendations"

def run_evaluation(file_path):
    with open(file_path, "r") as f:
        test_cases = json.load(f)

    total_cases = len(test_cases)
    top_three_success = 0
    top_one_success = 0
    hard_filter_violations = 0

    print(f"Starting evaluation of {total_cases} test cases...\n")

    for case in test_cases:
        case_id = case.get("caseId")
        request_payload = case.get("request", {})
        
        # In a real evaluation, you would temporarily mock the pantry state 
        # or have a dedicated test user. For this script, we assume the API 
        # is hitting the test data you configured.
        
        try:
            response = requests.post(API_URL, json=request_payload)
            response.raise_for_status()
            data = response.json()
            results = data.get("results", [])
        except Exception as e:
            print(f"❌ Case {case_id} failed to fetch from API: {e}")
            continue

        if not results:
            print(f"⚠️ Case {case_id}: No results returned.")
            continue

        returned_ids = [r["recipeId"] for r in results]
        acceptable_ids = case.get("acceptableRecipeIds", [])
        must_not_include_ids = case.get("mustNotIncludeRecipeIds", [])

        # Metric 1 & 2: Relevance
        top_one = returned_ids[0] if returned_ids else None
        top_three = returned_ids[:3]

        if top_one in acceptable_ids:
            top_one_success += 1
        
        if any(rid in acceptable_ids for rid in top_three):
            top_three_success += 1

        # Metric 3: Hard-Filter Violations[cite: 1]
        violations = [rid for rid in returned_ids if rid in must_not_include_ids]
        if violations:
            hard_filter_violations += len(violations)
            print(f"🚨 Case {case_id} VIOLATION: Returned excluded recipes {violations}")

    # Calculate final metrics[cite: 1]
    print("\n--- Evaluation Results ---")
    print(f"Total Cases Evaluated: {total_cases}")
    print(f"Top-One Acceptance: {(top_one_success / total_cases) * 100:.1f}%")
    print(f"Acceptable Recipe in Top Three: {(top_three_success / total_cases) * 100:.1f}%")
    print(f"Hard-Filter Violations: {hard_filter_violations}")
    
    if hard_filter_violations > 0:
        print("\n⚠️ WARNING: Your hard-filter violation rate must be zero to pass.")
    else:
        print("\n✅ Hard filters are working perfectly.")

if __name__ == "__main__":
    # Point this to wherever you saved the JSON file
    run_evaluation("tests/evaluation-cases.json")