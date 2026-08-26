# Production Alert Definitions

We monitor a small set of high-value alerts to avoid alert fatigue:

1. **Repeated Production Exceptions:** Triggered if unhandled server exceptions exceed 5 per minute.
2. **Receipt-Extraction Failure Rate:** Triggered if the failure rate exceeds a 15% threshold.
3. **Database Health Check Fails:** Triggered immediately if the `/api/health/dependencies` database check returns 'degraded'.
4. **Cooking Transaction Failures:** Triggered if atomic database transactions fail, indicating potential concurrency or RLS issues.
5. **Recommendation Fallback Usage Increases:** Triggered if deterministic fallback usage spikes, indicating AI provider issues.
6. **AI-Provider Quota Approaching Limit:** Triggered when OpenAI/Gemini budget reaches 85%.
