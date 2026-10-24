"""Static regressions for Chatbot-shared Orquestra UI, no Supabase writes."""
import pathlib
import re
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
JS = (ROOT / "web-live/app.js").read_text(encoding="utf-8")
HTML = (ROOT / "web-live/index.html").read_text(encoding="utf-8")
CONFIG = (ROOT / "web-live/config.js").read_text(encoding="utf-8")
CHATBOT_REF = "ydyzjpcmavqffdazteib"
PAUSED_REF = "kekxcvcgyexcbleifffq"


class SharedChatbotDashboardTests(unittest.TestCase):
    def test_public_config_points_to_chatbot(self):
        self.assertIn("https://" + CHATBOT_REF + ".supabase.co", CONFIG)
        self.assertIn("sb_publishable_", CONFIG)
        self.assertNotIn(PAUSED_REF, CONFIG)
        self.assertNotIn("sb_secret_", CONFIG)
        self.assertNotIn("service_role", CONFIG.lower().replace("never put service_role", ""))

    def test_auth_onboarding_uses_chatbot_not_paused_database(self):
        self.assertNotIn(PAUSED_REF, HTML)
        self.assertIn("/project/" + CHATBOT_REF + "/auth/users", HTML)
        self.assertIn("compartilhado com o CRM", HTML)

    def test_authenticated_state_is_not_automatically_live(self):
        self.assertIn("mode=auth?.user?'pending':'auth'", JS)
        self.assertIn("if(event==='SIGNED_IN'&&session){mode='pending'", JS)
        self.assertIn("if(mode==='pending'){mode='live';updateMode();setPage('home')}", JS)
        self.assertIn("if(projects.error||nodes.error||tasks.error)throw", JS)
        self.assertIn("}catch(error){mode='pending'", JS)
        self.assertIn("const active=mode==='live'", JS)
        self.assertIn("Missões e cadastro bloqueados", JS)

    def test_schema_pending_never_enables_queue(self):
        self.assertIn("$('queueButton').disabled=!active", JS)
        self.assertIn("if(mode!=='live'||!client)", JS)
        self.assertRegex(JS, r"setInterval\(\(\)=>\{if\(\['live','pending'\]")
        self.assertIn("},60000)", JS)


if __name__ == "__main__":
    unittest.main()
