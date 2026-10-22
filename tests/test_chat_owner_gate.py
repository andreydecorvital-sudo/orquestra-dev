"""Checks for Orquestra-only owner grants on shared Chatbot Auth."""
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
SQL=(ROOT/"sql/009_orquestra_chat_owner_gate.sql").read_text(encoding="utf-8")
API=(ROOT/"supabase/functions/orq-chat/index.ts").read_text(encoding="utf-8")
CI=(ROOT/"tests/chat-db/verify_postgres.sh").read_text(encoding="utf-8")

class OwnerGateContract(unittest.TestCase):
    def test_grants_protect_shared_auth(self):
        for marker in (
            "CREATE TABLE public.orq_chat_allowed_owners",
            "REFERENCES auth.users(id)",
            "ENABLE ROW LEVEL SECURITY",
            "REVOKE ALL ON TABLE public.orq_chat_allowed_owners",
            "FROM PUBLIC, anon, authenticated",
            "TO service_role",
            "COUNT(DISTINCT owner_id)",
            "ORQ_CHAT_GATE_AMBIGUOUS_OWNER",
            "JOIN auth.users",
            "SELECT DISTINCT p.owner_id",
            "ORQ_CHAT_GATE_BAD_SEED",
            "BEGIN;", "COMMIT;"
        ):
            self.assertIn(marker,SQL)
        self.assertNotIn("ALTER TABLE public.orq_projects",SQL)
        self.assertNotIn("CREATE POLICY",SQL)
        self.assertNotIn("UPDATE public.",SQL)
        self.assertNotIn("DELETE FROM public.",SQL)

    def test_api_requires_db_grant_even_when_env_is_configured(self):
        x=API.index("admin.auth.getUser(token)")
        g=API.index(".from('orq_chat_allowed_owners')")
        denial=API.index("if (!permission) return reply")
        env=API.index("Deno.env.get('ORQ_CHAT_ALLOWED_OWNER_IDS')")
        action=API.index("const action = body.action")
        self.assertTrue(x<g<denial<env<action)
        self.assertIn("orquestra_not_configured",API)
        self.assertIn("orquestra_access_denied",API)
        self.assertIn("owners.length > 0 && !owners.includes(owner.toLowerCase())",API)

    def test_disposable_database_tests_seed_only_existing_owner(self):
        self.assertIn("run_sql < sql/009_orquestra_chat_owner_gate.sql",CI)
        self.assertIn("has_table_privilege('authenticated','public.orq_chat_allowed_owners','INSERT')",CI)
        self.assertIn("has_table_privilege('authenticated','public.orq_chat_allowed_owners','SELECT')",CI)


if __name__ == "__main__":
    unittest.main()
