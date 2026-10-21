Orquestra — PostgreSQL disposable validation (2026-10-21)

This workflow spins up a temporary PostgreSQL 17-alpine Docker container, synthesizes auth.users and the anon/authenticated/service_role roles, runs original SQL 008 and validates role permissions, two-user RLS, atomic message submission, replay idempotency, concurrency, rate-limiting and safe rejection of repeat migration. It never connects to Chatbot/CRM, never runs production SQL and destroys the entire container after testing.

Run: bash tests/chat-db/verify_postgres.sh (requires Docker). Workflow: .github/workflows/chat-database-ci.yml.

A green workflow proves PostgreSQL compatibility only; it is not a deployed Edge Function or a live OAuth/chat test. Production migration still needs backup, security review, two-identity verification on a controlled environment, and explicit release gate. Nothing here starts model inference or changes Argoplace/CRM.