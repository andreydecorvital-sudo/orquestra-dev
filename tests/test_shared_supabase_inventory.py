"""Guard shared-Supabase adoption: discovery SQL must stay strictly read-only."""
import pathlib
import re
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SQL_PATH = ROOT / "sql" / "000_shared_supabase_inventory.sql"


class SharedSupabaseInventoryTests(unittest.TestCase):
    def test_inventory_remains_read_only(self):
        sql = SQL_PATH.read_text(encoding="utf-8")
        lines = [line for line in sql.splitlines() if not line.lstrip().startswith("--")]
        executable = "\n".join(lines)
        forbidden = ("alter", "create", "drop", "truncate", "insert",
                     "update", "delete", "grant", "revoke", "execute",
                     "call", "copy", "do", "set", "vacuum")
        for verb in forbidden:
            self.assertIsNone(re.search(r"\b" + verb + r"\b", executable, re.IGNORECASE), verb)

    def test_inventory_looks_only_at_orquestra_names(self):
        s = SQL_PATH.read_text(encoding="utf-8")
        self.assertIn("pg_catalog.pg_class", s)
        self.assertIn("pg_catalog.pg_proc", s)
        self.assertIn("pg_catalog.pg_policies", s)
        self.assertEqual(s.count("like 'orq"), 3)
        self.assertIn("NO_ORQ_OBJECT_COLLISIONS", s)
        self.assertIn("REVIEW_EXISTING_ORQ_OBJECTS", s)

    def test_inventory_checks_auth_users(self):
        s = SQL_PATH.read_text(encoding="utf-8")
        self.assertIn("pg_catalog.to_regclass('auth.users')", s)
        self.assertNotIn("select * from auth.users", s.lower())


if __name__ == "__main__":
    unittest.main()
