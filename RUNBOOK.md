# PantryPilot Operational Runbook

## Application Overview
* **Production URL:** [Your Vercel URL]
* **Health Endpoints:** `/api/health`, `/api/health/dependencies`
* **Current Release:** v0.1.0-beta.1

## Common Incidents & Mitigations

### 1. LLM Provider Failure
* **Symptoms:** Explanation generation times out or returns 500 errors[cite: 2].
* **Mitigation:** The application automatically falls back to deterministic explanations[cite: 2].
* **Recovery:** Toggle `ENABLE_LLM_EXPLANATIONS=false` if failure is prolonged[cite: 2].

### 2. Receipt Provider Failure
* **Symptoms:** Uploads hang, returning a timeout or invalid response[cite: 2].
* **Mitigation:** Receipt status becomes 'failed'; UI offers retry or manual entry[cite: 2]. No phantom pantry items are created[cite: 2].

### 3. Supabase Database Failure
* **Symptoms:** `/api/health/dependencies` reports 'degraded'[cite: 2].
* **Mitigation:** UI displays a temporary-service error message instead of showing an incorrect empty pantry[cite: 2]. State-changing buttons disable to prevent data corruption[cite: 2].

### 4. AI Quota or Rate Limit Reached
* **Symptoms:** 429 Too Many Requests from external AI providers[cite: 2].
* **Mitigation:** Expensive retries are bounded; deterministic fallbacks activate automatically[cite: 2]. 

## Recovery Checklist
- [x] Confirm incident[cite: 2]
- [x] Identify affected component[cite: 2]
- [x] Disable optional failing feature via flags if necessary[cite: 2]
- [x] Verify no data corruption[cite: 2]
- [x] Run smoke tests[cite: 2]

## Release Decision
**Ready for controlled beta.** All operational blockers have been resolved, fallbacks gracefully degrade, and the data is backed up[cite: 2].
