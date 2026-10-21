"""Activation preflight: backup export and restricted CRM tenant access."""
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
SCRIPT=(ROOT/"scripts/backup-chatbot-windows.ps1").read_text(encoding="utf-8")
DOC=(ROOT/"docs/CHATBOT_ACTIVATION_RUNBOOK.md").read_text(encoding="utf-8")
API=(ROOT/"supabase/functions/orq-chat/index.ts").read_text(encoding="utf-8")

class ActivationPreflightTests(unittest.TestCase):
    def test_backup_covers_public_and_managed_metadata_and_data(self):
        for expected in ("public-schema.sql","public-data.sql",
                         "managed-schema.sql","managed-data.sql",
                         "--data-only","auth,storage","Get-FileHash",
                         "supabase @commandArgs","nao aplique migracao"):
            self.assertIn(expected,SCRIPT)
        self.assertNotIn("SUPABASE_DB_PASSWORD=",SCRIPT)
        self.assertNotIn("db reset",SCRIPT)
        self.assertNotIn("db push",SCRIPT)

    def test_shared_auth_fails_closed_without_allowlist(self):
        self.assertIn("ORQ_CHAT_ALLOWED_OWNER_IDS",API)
        self.assertIn("owners.length === 0",API)
        self.assertIn("orquestra_access_denied",API)
        self.assertIn("origin && !allowedOrigins.has(origin)",API)
        self.assertIn("orquestra-dev-749aiiuwe-vitaldecor.vercel.app",API)
        self.assertIn("ORQ_ALLOWED_ORIGINS",DOC)

if __name__=="__main__":
    unittest.main()
