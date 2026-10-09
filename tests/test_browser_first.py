"""Browser-first UX contracts: no CLI requirement, no fake provider API."""
import pathlib
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[1]
class BrowserFirstTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.index=(ROOT/'web-live'/'index.html').read_text()
        cls.app=(ROOT/'web-live'/'app.js').read_text()
        cls.browser=(ROOT/'web-live'/'browser-mode.js').read_text()

    def test_public_browser_nav_and_auth_escape(self):
        self.assertIn('id="browser"',self.index)
        self.assertIn('data-page="browser"',self.index)
        self.assertIn('Modo navegador',self.index)
        self.assertIn("['browser','connections']",self.app)
        self.assertIn("loginScreen",self.app)
        self.assertIn("setPage('browser')",self.app)

    def test_official_links_only_and_no_provider_claims(self):
        self.assertIn('href="https://chatgpt.com/"',self.index)
        self.assertIn('href="https://claude.ai/new"',self.index)
        self.assertIn('não lê conversas nem envia mensagens automaticamente',self.index)
        for secret in ('OPENAI_API_KEY','ANTHROPIC_API_KEY','document.cookie','Bearer ', 'fetch('):
            self.assertNotIn(secret,self.browser)

    def test_no_unreviewed_persistence_or_auto_submission(self):
        self.assertNotIn('localStorage',self.browser)
        self.assertNotIn('sessionStorage',self.browser)
        self.assertIn('navigator.clipboard',self.browser)
        self.assertIn('readonly',self.index)
        self.assertIn("browserAnswer",self.browser)

    def test_auth_still_separate(self):
        self.assertIn('loginForm',self.index)
        self.assertIn('signInWithPassword',self.app)
