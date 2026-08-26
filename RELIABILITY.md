# Reliability Controls & Recovery Paths

## Timeouts
* **Receipt Extraction:** Bounded to 15 seconds.
* **LLM Explanations:** Bounded to 10 seconds.
* **Supabase Operations:** Bounded to 5 seconds.

## Retry Policy
* **Permitted for:** Network interruptions, provider timeouts, temporary rate limiting.
* **Not permitted for:** Invalid file formats, schema validation failures, unauthorized requests.
* **Mechanism:** Maximum of 3 attempts with exponential backoff.

## Idempotency Validations
* **Receipt Approval:** Database constraints prevent duplicate pantry items if re-submitted.
* **Cooking Confirmation:** Handled securely via Postgres atomic RPC and unique idempotency keys.

## Feature Flags
Server-controlled flags exist to disable failing components safely without redeploying code:
* `ENABLE_RECEIPT_EXTRACTION`
* `ENABLE_SEMANTIC_RETRIEVAL`
* `ENABLE_LLM_EXPLANATIONS`
