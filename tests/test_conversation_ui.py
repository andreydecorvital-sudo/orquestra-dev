"""Regression checks for conversation-first UI and preserved diagnostic screen."""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web-live"
HTML = (WEB / "chat.html").read_text(encoding="utf-8")
JS = (WEB / "chat.js").read_text(encoding="utf-8")
CSS = (WEB / "chat.css").read_text(encoding="utf-8")
API = (ROOT / "supabase/functions/orq-chat/index.ts").read_text(encoding="utf-8")
MISSIONS = (WEB / "missions.html").read_text(encoding="utf-8")
MISSION_JS = (WEB / "missions.js").read_text(encoding="utf-8")
DASHBOARD = (WEB / "index.html").read_text(encoding="utf-8")


class ConversationUIContractTests(unittest.TestCase):
    def test_conversation_is_primary_and_legacy_available(self):
        self.assertIn("<title>Conversas · Orquestra</title>", HTML)
        for token in ('href="/chat.css"', 'src="/chat.js"',
                      'id="threadList"', 'id="messageList"',
                      'id="composer"', 'href="/missions.html"',
                      'href="/"', 'lang="pt-BR"'):
            self.assertIn(token, HTML)
        self.assertIn('href="/chat.html"', DASHBOARD)

    def test_dom_bindings_are_valid(self):
        ids = set(re.findall(r'id="([a-zA-Z][a-zA-Z0-9_-]*)"', HTML))
        lookups = set(re.findall(r"\$\('([a-zA-Z][a-zA-Z0-9_-]*)'\)", JS))
        self.assertFalse(lookups - ids, lookups - ids)

    def test_real_auth_and_idempotent_thread_creation(self):
        for token in ('state.client.auth.getUser()', 'state.client.auth.getSession()',
                      'state.client.auth.signInWithPassword', 'storage: sessionStorage'):
            self.assertIn(token, JS)
        for token in ('admin.auth.getUser(token)', ".eq('owner_id', owner)",
                      'const threadId = body.thread_id;',
                      "error.code !== '23505'", 'existing.title !== title'):
            self.assertIn(token, API)

    def test_fail_closed_and_no_fake_inference(self):
        for token in ("action: 'list_threads'", "action: 'create_thread'",
                      "action: 'send'", "action: 'read_thread'",
                      'await loadThreads(); // verifies Edge Function AND database',
                      "state.api === 'ready'",
                      'threadId: state.threadId || crypto.randomUUID()',
                      'client_request_id: pending.requestId',
                      'state.pending = null;', "BLOCKERS[turn.blocker_code]",
                      'Nenhuma IA será simulada', "element.textContent = content"):
            self.assertIn(token, JS)
        self.assertNotIn("innerHTML", JS)
        for forbidden in ('OPENAI_API_KEY', 'ANTHROPIC_API_KEY',
                          'SUPABASE_SERVICE_ROLE_KEY', 'sb_secret_',
                          'localStorage', 'document.cookie', 'window.open('):
            self.assertNotIn(forbidden, JS)

    def test_old_diagnose_flow_preserved(self):
        for token in ('href="/missions.css"', 'src="/missions.js"',
                      'href="/chat.html"'):
            self.assertIn(token, MISSIONS)
        self.assertIn("kind:'diagnose'", MISSION_JS)
        self.assertIn("state.client.from('orq_tasks')", MISSION_JS)
        self.assertIn('@media(max-width:720px)', CSS)
        self.assertIn('prefers-reduced-motion:reduce', CSS)


if __name__ == '__main__':
    unittest.main()
