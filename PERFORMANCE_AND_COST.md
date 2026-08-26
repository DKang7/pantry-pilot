# Performance and Cost Measurements

## Performance Targets & Latency
* **Warm pantry load:** ~1.2 seconds (Target: Under 2 seconds).
* **Idle-start pantry load:** ~3.5 seconds (Application cold start on Vercel).
* **Receipt-upload acknowledgment:** ~1.5 seconds (Target: Under 2 seconds).
* **Receipt extraction (Gemini Flash):** ~6-8 seconds (Progress shown immediately).
* **Warm recipe recommendation (Hybrid):** ~3.8 seconds (Target: Under 4 seconds).
* **Cooking confirmation:** ~0.8 seconds (Target: Under 2 seconds).

**Identified Bottleneck:** The largest latency spike occurs during receipt extraction due to the external LLM vision processing step. 

## Approximate Cost Report
* **Receipt Extraction (Gemini 2.5 Flash):** ~$0.0001 per receipt (assuming image + ~500 input tokens / ~200 output tokens).
* **Query Embedding (text-embedding-3-small):** ~$0.000002 per search query (assuming ~100 tokens).
* **Recommendation Explanation (Gemini 2.5 Flash):** ~$0.00005 per request.
* **100 Receipt-processing requests:** ~$0.01 total.

## Usage Protections
* Maximum receipt file size enforced (e.g., 5MB).
* Explanations are strictly limited to the top 3 results to cap output tokens.
