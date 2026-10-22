"""Fail-closed authorization for shared Chatbot/CRM Supabase Auth."""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
API = (ROOT / "supabase/functions/orq-chat/index.ts").read_text(encoding="utf-8")
UI = (ROOT / "web-live/chat.js").read_text(encoding="utf-8")


class SharedAuthAccessTests(unittest.TestCase):
    def test_strict_owner_allowlist_after_verified_login(self):
        auth = API.index("admin.auth.getUser(token)")
        owner = API.index("const owner = verified.user.id;")
        gate = API.index(".from('orq_chat_allowed_owners')")
        block = API.index("if (!permission) return reply")
        action = API.index("const action = body.action;")
        self.assertTrue(auth < owner < gate < block < action)
        self.assertIn("if (permissionError)", API)
        self.assertIn("owners.length > 0 && !owners.includes(owner.toLowerCase())", API)
        self.assertIn("orquestra_not_configured", API)
        self.assertIn("orquestra_access_denied", API)
        self.assertIn("403", API)
        self.assertIn("503", API)

    def test_allowlist_cannot_be_set_by_browser_or_request_body(self):
        self.assertNotIn("ORQ_CHAT_ALLOWED_OWNER_IDS", UI)
        self.assertNotIn("sessionStorage.getItem('ORQ_CHAT_ALLOWED_OWNER_IDS')", API)
        self.assertNotRegex(API, r"body\.allowed_owners|request\.headers\.get\(['\"]x-orq-owner")
        self.assertIn("UUID.test(value)", API)
        self.assertIn("owners.includes(owner.toLowerCase())", API)
        self.assertIn("const owner = verified.user.id;", API)

    def test_no_fake_success_from_check_only(self):
        self.assertIn("inference: 'not_connected'", API)
        self.assertIn("orq_chat_submit", API)
        self.assertIn("admin.from('orq_chat_threads')", API)
        self.assertNotIn("console.log(body)", API)


if __name__ == '__main__':
    unittest.main()
