# Graceful Degradation Matrix

| Failed Component | Expected Behavior |
| :--- | :--- |
| **Receipt Extraction** | Show retry and manual-entry options[cite: 2]. |
| **Embedding Provider** | Use deterministic recipe matching[cite: 2]. |
| **Vector Search** | Use deterministic recipe matching[cite: 2]. |
| **LLM Explanation** | Use deterministic explanation[cite: 2]. |
| **Supabase Storage** | Block receipt upload safely[cite: 2]. |
| **Supabase Database** | Show temporary service error; do not show an incorrect empty pantry[cite: 2]. |
| **Recipe Data** | Explain that recommendations are unavailable[cite: 2]. |
