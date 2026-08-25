# Environment Matrix

* **Local Development:** Uses local `.env` variables, runs on `localhost:8000`, destructive tests allowed.
* **Automated Test:** Uses a separate isolated Supabase test project; mock AI providers enabled.
* **Preview Deployment:** Hosted on Vercel preview URLs, uses staging database, real user data not allowed.
* **Production:** Hosted on main Vercel domain, live Supabase database, live AI providers. Automated tests and destructive scripts must not run against production.
