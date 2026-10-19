import json
import pathlib
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[1]

class SharedAIGatewayBoundaryTests(unittest.TestCase):
    def test_research_alias_is_catalogued_but_not_enabled(self):
        contract=json.loads((ROOT/"docs/shared-ai-gateway-contract.json").read_text(encoding="utf-8"))
        gateway=contract["ai_gateway"]
        self.assertEqual(gateway["research_alias"],"orquestra-research")
        self.assertEqual(set(gateway["providers"]),{"gemini","openai","claude","groq","grok"})
        self.assertFalse(gateway["enabled"])
        self.assertFalse(gateway["paid_provider_fallback_for_cli"])
        self.assertFalse(gateway["execution_authority"])
        self.assertTrue(gateway["requires_separate_billing_approval"])
        self.assertTrue(contract["existing_executor"]["unchanged"])

if __name__=="__main__":
    unittest.main()
