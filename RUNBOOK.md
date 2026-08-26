# PantryPilot Operational Runbook

## Application Overview
* **Production URL:** [Your Vercel URL]
* **Health Endpoints:** `/api/health`, `/api/health/dependencies`
* **Current Release:** v0.1.0-beta.1

## Common Incidents & Mitigations

### 1. LLM Provider Failure
* **Symptoms:** Explanation generation times out or returns 500 errors.
* **Mitigation:** The application automatically falls back to deterministic explanations.
* **Recovery:** Toggle `ENABLE_LLM_EXPLANATIONS=false` if failure is prolonged.

### 2. Receipt Provider Failure
* **Symptoms:** Uploads hang, returning a timeout or invalid response.
* **Mitigation:** Receipt status becomes 'failed'; UI offers retry or manual entry. No phantom pantry items are created.

### 3. Supabase Database Failure
* **Symptoms:** `/api/health/dependencies` reports 'degraded'.
* **Mitigation:** UI displays a temporary-service error message instead of showing an incorrect empty pantry. State-changing buttons disable to prevent data corruption.

### 4. AI Quota or Rate Limit Reached
* **Symptoms:** 429 Too Many Requests from external AI providers.
* **Mitigation:** Expensive retries are bounded; deterministic fallbacks activate automatically. 

## Recovery Checklist
- [x] Confirm incident
- [x] Identify affected component
- [x] Disable optional failing feature via flags if necessary
- [x] Verify no data corruption
- [x] Run smoke tests

## Release Decision
**Ready for controlled beta.** All operational blockers have been resolved, fallbacks gracefully degrade, and the data is backed up.
