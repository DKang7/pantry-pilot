# Performance and Cost Measurements

## Performance Targets & Latency
* **Warm pantry load:** ~1.2 seconds (Target: Under 2 seconds).
* **Idle-start pantry load:** ~3.5 seconds (Application cold start on Vercel).
* **Receipt-upload acknowledgment:** ~1.5 seconds (Target: Under 2 seconds)[cite: 2].
* **Receipt extraction (Gemini Flash):** ~6-8 seconds (Progress shown immediately)[cite: 2].
* **Warm recipe recommendation (Hybrid):** ~3.8 seconds (Target: Under 4 seconds)[cite: 2].
* **Cooking confirmation:** ~0.8 seconds (Target: Under 2 seconds)[cite: 2].

**Identified Bottleneck:** The largest latency spike occurs during receipt extraction due to the external LLM vision processing step[cite: 2]. 

## Approximate Cost Report
* **Receipt Extraction (Gemini 2.5 Flash):** ~$0.0001 per receipt (assuming image + ~500 input tokens / ~200 output tokens)[cite: 2].
* **Query Embedding (text-embedding-3-small):** ~$0.000002 per search query (assuming ~100 tokens)[cite: 2].
* **Recommendation Explanation (Gemini 2.5 Flash):** ~$0.00005 per request[cite: 2].
* **100 Receipt-processing requests:** ~$0.01 total[cite: 2].

## Usage Protections
* Maximum receipt file size enforced (e.g., 5MB)[cite: 2].
* Explanations are strictly limited to the top 3 results to cap output tokens[cite: 2].
