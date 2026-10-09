"""One-time Windows Hermes onboarding and browser connection center."""
import pathlib
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[1]

class HermesWizardTests(unittest.TestCase):
    def test_one_click_entry_point_exists(self):
        bat=(ROOT/'runner/conectar-hermes-windows.cmd').read_text()
        self.assertIn('connect-hermes-windows.ps1',bat)
        self.assertIn('-ExecutionPolicy Bypass -File',bat)
        self.assertIn('%~dp0connect-hermes-windows.ps1',bat)
        self.assertNotIn('Set-ExecutionPolicy',bat)
        self.assertNotIn('Scope LocalMachine',bat)
        root_launcher=(ROOT/'INICIAR-HERMES.cmd').read_text()
        self.assertIn('call "%~dp0runner\\conectar-hermes-windows.cmd"',root_launcher)
        self.assertNotIn('ExecutionPolicy Bypass',root_launcher)

    def test_only_browser_oauth_and_manual_model_select(self):
        ps=(ROOT/'runner/connect-hermes-windows.ps1').read_text()
        self.assertIn('hermes auth add openai-codex --browser',ps)
        self.assertIn('& hermes model',ps)
        self.assertIn("& (Join-Path $PSScriptRoot 'prepare-hermes-windows.ps1')",ps)
        self.assertNotIn('& powershell -NoProfile -File',ps)
        self.assertIn('& hermes tools',ps)
        self.assertNotIn('OPENAI_API_KEY',ps)
        self.assertNotIn('iex (irm',ps)
        self.assertNotIn('Invoke-Expression',ps)

    def test_connections_page_does_not_claim_connected(self):
        html=(ROOT/'web-live/index.html').read_text()
        self.assertIn('Hermes Agent — conectar pelo Windows',html)
        self.assertIn('nenhuma conexão foi comprovada',html)
        self.assertIn('INICIAR-HERMES.cmd',html)
