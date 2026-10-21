"""Contract checks for review-only, owner-isolated conversational storage."""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
SQL = (ROOT / "sql" / "008_orquestra_chat_persistence_REVIEW_ONLY.sql").read_text(encoding="utf-8")
API = (ROOT / "supabase" / "functions" / "orq-chat" / "index.ts").read_text(encoding="utf-8")


class ChatPersistenceContractTests(unittest.TestCase):
    def test_migration_requires_explicit_review_and_fails_on_collision(self):
        self.assertIn("REVIEW ONLY", SQL)
        self.assertIn("BEGIN;", SQL)
        self.assertIn("COMMIT;", SQL)
        self.assertIn("BLOCKED: chat objects already exist", SQL)
        self.assertIn("public.orq_nodes", SQL)

    def test_only_orquestra_objects_are_mutated(self):
        ddl = re.findall(
            r"\b(?:CREATE|ALTER|REVOKE|GRANT|UPDATE|INSERT)\s+(?:TABLE\s+|ON\s+TABLE\s+|POLICY\s+\w+\s+ON\s+|FUNCTION\s+)?(?:public\.)?([a-z][a-z_0-9]*)",
            SQL, flags=re.IGNORECASE,
        )
        self.assertNotIn("contacts", ddl)
        for marker in ("orq_chat_threads", "orq_chat_messages", "orq_chat_turns", "orq_chat_submit"):
            self.assertIn(marker, SQL)

    def test_owner_isolation_and_no_client_mutations(self):
        self.assertEqual(SQL.count("ENABLE ROW LEVEL SECURITY"), 3)
        self.assertEqual(SQL.count("FOR SELECT TO authenticated"), 3)
        self.assertGreaterEqual(SQL.count("owner_id = (SELECT auth.uid())"), 3)
        self.assertIn("FROM PUBLIC, anon, authenticated", SQL)
        self.assertIn("TO service_role", SQL)
        self.assertIn("FOREIGN KEY (thread_id, owner_id)", SQL)
        self.assertIn("FOREIGN KEY (message_id, owner_id)", SQL)
        self.assertIn("REVOKE ALL ON FUNCTION public.orq_chat_submit", SQL)

    def test_idempotency_rate_limit_atomicity(self):
        self.assertIn("UNIQUE (owner_id, client_request_id)", SQL)
        self.assertIn("pg_advisory_xact_lock", SQL)
        self.assertIn("ORQ_CHAT_IDEMPOTENCY_CONFLICT", SQL)
        self.assertIn("ORQ_CHAT_RATE_LIMIT", SQL)
        self.assertIn("interval '1 minute'", SQL)
        self.assertIn("interval '1 day'", SQL)

    def test_no_fabricated_ai_answer_or_paid_fallback(self):
        self.assertIn("'provider_not_connected'", SQL)
        self.assertIn("inference: 'not_connected'", API)
        self.assertIn("admin.auth.getUser(token)", API)
        self.assertIn(".eq('owner_id', owner)", API)
        self.assertIn("orq_chat_submit", API)
        self.assertIn("new URL(request.url).pathname.endsWith('/health')", API)
        self.assertNotIn("OPENAI_API_KEY", API)
        self.assertNotIn("ANTHROPIC_API_KEY", API)
        self.assertNotIn("fetch('https://api.openai.com", API)
        self.assertNotIn("window.localStorage", API)
        self.assertNotIn("console.log(body)", API)


if __name__ == "__main__":
    unittest.main()
