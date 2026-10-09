"""Static protocol and privacy contract for the local Chrome bridge."""
import json
import pathlib
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[1]

class BrowserBridgeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest=json.loads((ROOT/'browser-bridge/manifest.json').read_text())
        cls.bg=(ROOT/'browser-bridge/background.js').read_text()
        cls.content=(ROOT/'browser-bridge/content.js').read_text()
        cls.ui=(ROOT/'web-live/connections.js').read_text()
        cls.html=(ROOT/'web-live/index.html').read_text()

    def test_minimal_permissions_and_scope(self):
        self.assertEqual(self.manifest['manifest_version'],3)
        self.assertEqual(self.manifest['permissions'],['tabs'])
        self.assertNotIn('host_permissions',self.manifest)
        self.assertEqual(self.manifest['content_scripts'][0]['matches'],
                         ['https://orquestra-dev-app.vercel.app/*'])
        self.assertFalse(self.manifest['content_scripts'][0]['all_frames'])
        for permission in ('cookies','webRequest','debugger','scripting','storage'):
            self.assertNotIn(permission,self.manifest['permissions'])

    def test_tab_state_not_auth_claim(self):
        self.assertIn("chatgptTabOpen",self.bg)
        self.assertIn("claudeTabOpen",self.bg)
        self.assertIn("sender.tab.url",self.bg)
        self.assertIn("Aba oficial detectada. Login não verificado.",self.ui)
        self.assertIn("Aba aberta",self.ui)
        self.assertNotIn("autenticado",self.ui.lower())
        self.assertIn('Conexões',self.html)

    def test_secure_origin_and_no_chat_scraping(self):
        self.assertIn("event.origin!==location.origin",self.content)
        self.assertIn("event.source!==window",self.content)
        self.assertIn("event.origin!==window.location.origin",self.ui)
        self.assertIn('pending.has(v.nonce)',self.ui)
        for source in (self.bg,self.content,self.ui):
            for forbidden in ('document.cookie','chrome.cookies','localStorage','sessionStorage',
                              'ANTHROPIC_API_KEY','OPENAI_API_KEY','chrome.tabs.executeScript'):
                self.assertNotIn(forbidden,source)

    def test_not_importing_untrusted_chat_content(self):
        self.assertNotIn('content_scripts',self.manifest['background'])
        self.assertNotIn('fetch(',self.bg)
        self.assertNotIn('fetch(',self.content)
        self.assertNotIn('chrome.tabs.sendMessage',self.bg)
