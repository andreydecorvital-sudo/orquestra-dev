"""Contract tests for secure onboarding and local pairing assistant."""
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]

class OnboardingTests(unittest.TestCase):
    def test_private_account_created_in_supabase_dashboard(self):
        html = (ROOT/'web-live'/'index.html').read_text(encoding='utf-8')
        self.assertIn('Authentication → Users', html)
        self.assertIn('Create new user', html)
        self.assertNotIn('signUp(', (ROOT/'web-live'/'app.js').read_text(encoding='utf-8'))

    def test_pairing_download_is_local_and_not_executing(self):
        js = (ROOT/'web-live'/'app.js').read_text(encoding='utf-8')
        for expected in ("new Blob(", "URL.createObjectURL(", "allow_execution:false",
                         "orquestra-agent-worker.json", "[projectId]", "localPath"):
            self.assertIn(expected, js)
        self.assertNotIn('OPENAI_API_KEY', js)
        self.assertNotIn('ANTHROPIC_API_KEY', js)

    def test_windows_setup_restricts_credentials(self):
        ps = (ROOT/'runner'/'setup-windows.ps1').read_text(encoding='utf-8')
        for expected in ("'SYSTEM:(F)'", "'/inheritance:r'",
                         "allow_execution=$false", "Get-Command icacls.exe",
                         "WriteAllText", "node_secret", "kekxcvcgyexcbleifffq"):
            self.assertIn(expected, ps)
        self.assertNotIn('api.openai.com', ps)
        self.assertNotIn('api.anthropic.com', ps)

    def test_readme_is_explicit_about_no_24h_running(self):
        doc = (ROOT/'docs'/'PRIMEIRO-ACESSO.md').read_text(encoding='utf-8')
        self.assertIn('Sem worker ligado', doc)
        self.assertIn('24/7', doc)
