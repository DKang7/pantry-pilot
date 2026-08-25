# Backup, Restore, and Retention Procedures

## Database Backup Procedure
* **Included:** Database schema, migration history, recipe data, ingredient aliases.
* **Excluded:** Production user data is explicitly excluded from source control (Git). 
* **Storage:** Automated daily Supabase physical backups with point-in-time recovery.

## Restore Drill Verification
* Restored into an isolated local Supabase test environment[cite: 2].
* Verified tables, migrations, and database functions exist[cite: 2].
* Confirmed Row Level Security (RLS) policies remain active and cross-user access remains denied[cite: 2].

## Storage Backup and Retention
* **Failed or Abandoned Receipts:** Eligible for deletion after 7 days[cite: 2].
* **Approved Receipts:** Original receipt images are retained until the user deletes them, preserving approved inventory history[cite: 2].
