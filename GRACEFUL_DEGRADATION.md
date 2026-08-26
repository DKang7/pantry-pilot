# Graceful Degradation Matrix

| Failed Component | Expected Behavior |
| :--- | :--- |
| **Receipt Extraction** | Show retry and manual-entry options. |
| **Embedding Provider** | Use deterministic recipe matching. |
| **Vector Search** | Use deterministic recipe matching. |
| **LLM Explanation** | Use deterministic explanation. |
| **Supabase Storage** | Block receipt upload safely. |
| **Supabase Database** | Show temporary service error; do not show an incorrect empty pantry. |
| **Recipe Data** | Explain that recommendations are unavailable. |
