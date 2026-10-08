"""Fast static validation of the UI and its security boundaries."""
import pathlib
import re
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[1]

class WebTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html=(ROOT/'web/index.html').read_text(encoding='utf-8')
        cls.js=(ROOT/'web/app.js').read_text(encoding='utf-8')
        cls.config=(ROOT/'web/config.js').read_text(encoding='utf-8')

    def test_every_queried_id_exists(self):
        ids=set(re.findall(r'id="([a-zA-Z0-9_-]+)"',self.html))
        queried=set(re.findall(r"\$\('#([a-zA-Z0-9_-]+)'\)",self.js))
        self.assertEqual(set(),queried-ids)

    def test_no_admin_keys_or_live_credentials(self):
        self.assertNotIn('SUPABASE_SERVICE_ROLE_KEY',self.js)
        self.assertNotIn('sk-proj-',self.js)
        self.assertNotIn('sb_secret_',self.config)
        self.assertNotIn('Bearer eyJ',self.js)

    def test_demo_is_explicitly_labelled(self):
        self.assertIn('DEMO MODE',self.html)
        self.assertIn('Nenhum agente está executando',self.html)
        self.assertIn('não será executada',self.js)

    def test_all_pages_have_section_and_nav(self):
        for name in ('overview','missions','create','projects','nodes','connections','settings'):
            self.assertRegex(self.html,rf'<section[^>]+id="{name}"')
            self.assertIn(f'data-target="{name}"',self.html)

if __name__=='__main__':
    unittest.main()
