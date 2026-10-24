"""Static regression gates for the Chatbot shared-CRM bootstrap.

This is a proposed migration: tests DO NOT apply it to any database.
"""
from pathlib import Path
import re
import unittest

SQL = (Path(__file__).resolve().parents[1] / "sql" /
       "006_chatbot_shared_bootstrap_REVIEW_ONLY.sql").read_text(encoding="utf-8")


class ChatbotSharedBootstrapTests(unittest.TestCase):
    def test_atomic_and_refuses_existing_orq_objects(self):
        self.assertRegex(SQL, r"(?im)^BEGIN;")
        self.assertRegex(SQL, r"(?im)^COMMIT;")
        self.assertIn("RAISE EXCEPTION 'BLOCKED: existing orq_ objects", SQL)
        self.assertIn("pg_catalog.pg_class", SQL)
        self.assertIn("pg_catalog.pg_proc", SQL)
        self.assertIn("pg_catalog.pg_policies", SQL)
        self.assertIn("auth.users", SQL)

    def test_creates_only_orquestra_tables(self):
        tables = re.findall(
            r"(?i)create\s+table\s+(?:if\s+not\s+exists\s+)?public\.(\w+)", SQL
        )
        self.assertEqual(set(tables), {
            "orq_projects", "orq_nodes", "orq_tasks", "orq_task_events"
        })
        self.assertEqual(len(tables), 4)

    def test_no_global_schema_or_extension_changes(self):
        executable = "\n".join(
            line for line in SQL.splitlines()
            if not line.strip().startswith("--")
        )
        for pattern in (
            r"\bcreate\s+extension\b",
            r"\balter\s+default\s+privileges\b",
            r"\balter\s+schema\b",
            r"\bdrop\s+schema\b",
            r"\btruncate\b",
            r"\bdrop\s+table\b",
            r"\brevoke\s+.+\bon\s+schema\b",
            r"\bgrant\s+.+\bon\s+schema\b",
        ):
            self.assertNotRegex(executable, "(?i)" + pattern)
        modified_tables = re.findall(
            r"(?i)\balter\s+table\s+(?:if\s+exists\s+)?(?:public\.)?(\w+)",
            executable,
        )
        self.assertTrue(modified_tables)
        self.assertTrue(all(t.startswith("orq_") for t in modified_tables))

    def test_rls_and_device_secret_privilege(self):
        for table in ("orq_projects", "orq_nodes", "orq_tasks", "orq_task_events"):
            self.assertIn(f"alter table public.{table} enable row level security", SQL.lower())
        self.assertIn("revoke select on table public.orq_nodes from authenticated", SQL.lower())
        self.assertIn("grant select(id,owner_id,name,last_seen_at,revoked_at,capabilities,created_at)", SQL.lower())
        self.assertNotRegex(SQL, r"(?i)grant\s+select\(.*secret_hash")

    def test_rpc_attempt_fence_is_final(self):
        self.assertIn("p_attempt integer", SQL)
        self.assertIn("t.attempts=p_attempt", SQL)
        self.assertIn("grant execute on function public.orq_finish_task(uuid,uuid,integer,boolean,text)", SQL.lower())
        self.assertIn("revoke all on function public.orq_finish_task(uuid,uuid,integer,boolean,text)", SQL.lower())


if __name__ == "__main__":
    unittest.main()
