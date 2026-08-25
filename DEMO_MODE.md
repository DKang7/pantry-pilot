# Resilient Portfolio Demo Mode

To ensure the project remains understandable during third-party service outages or quota exhaustion, PantryPilot includes a clearly labeled sample-data demo mode[cite: 2].

## Demo Flow
1. **Trigger:** User clicks "Try Demo" on the landing page[cite: 2].
2. **Extraction Bypass:** The application bypasses live AI vision extraction and routes the request to the `/api/test/receipt-extract/fake-success` endpoint, which returns precomputed JSON[cite: 2].
3. **Review & Pantry:** The user reviews the synthetic receipt data and approves it, populating a temporary local state rather than the production database[cite: 2].
4. **Fallback Recommendations:** Recipe recommendations default to the deterministic algorithm if the vector database is unreachable[cite: 2].

**Portfolio Resilience:** The repository README includes an architecture diagram, technology stack overview, and a link to a recorded video demonstration so the core functionality can be reviewed independently of the live application[cite: 2].
