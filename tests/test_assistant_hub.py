"""Tests for conversational assistance distinct from the mission queue."""
import unittest

from orchestration.assistant_hub import (
    AssistantRequest, ROLE_DESCRIPTIONS, SENSITIVE_ACTIONS,
    plan_assistance, may_perform_external_action,
)

CONNECTED = frozenset({"openai-codex"})
ASSIGNMENTS = {
    "assistant": "openai-codex", "engineering": "openai-codex",
    "research": "openai-codex", "commerce": "openai-codex",
    "marketing": "openai-codex", "design": "claude-oauth",
    "review": "claude-oauth",
}


class AssistantHubTests(unittest.TestCase):
    def plan(self, intent="general", action="answer", **kwargs):
        return plan_assistance(
            AssistantRequest(intent=intent, action=action, **kwargs),
            role_providers=ASSIGNMENTS, connected_providers=CONNECTED,
        )

    def test_ordinary_chat_requires_no_git_project(self):
        plan = self.plan()
        self.assertEqual(plan.mode, "conversation")
        self.assertEqual(plan.status, "planned")
        self.assertEqual(tuple(s.role for s in plan.steps), ("assistant",))
        self.assertFalse(plan.approval_required)
        self.assertFalse(plan.executor_authorized)

    def test_no_provider_means_blocked_not_fake_online(self):
        plan = plan_assistance(AssistantRequest(), role_providers={},
                               connected_providers=frozenset())
        self.assertEqual(plan.status, "blocked")

    def test_distinct_specialties(self):
        self.assertEqual(len(ROLE_DESCRIPTIONS), 7)
        for intent in ("research", "engineering", "design", "marketing",
                       "commerce", "review"):
            with self.subTest(intent=intent):
                self.assertEqual(self.plan(intent).steps[0].role, intent)

    def test_missing_secondary_provider_blocks(self):
        plan = self.plan("design")
        self.assertEqual(plan.status, "blocked")
        self.assertIn("claude-oauth", plan.blockers[0])

    def test_multidisciplinary_checks_each_specialist(self):
        plan = self.plan("multidisciplinary")
        self.assertEqual(tuple(s.role for s in plan.steps),
                         ("research", "engineering", "design", "review"))
        self.assertEqual(plan.status, "blocked")

    def test_complex_work_requires_independent_review(self):
        plan = self.plan("research", complex_work=True)
        self.assertEqual([s.role for s in plan.steps], ["research", "review"])
        self.assertEqual(plan.status, "blocked")

    def test_edit_requires_isolation_and_project_permission(self):
        blocked = self.plan("engineering", "sandbox_edit", project_id="safe")
        self.assertEqual(blocked.status, "blocked")
        allowed = plan_assistance(
            AssistantRequest(intent="engineering", action="sandbox_edit", project_id="safe"),
            role_providers=ASSIGNMENTS, connected_providers=CONNECTED,
            authorized_projects=frozenset({"safe"}), sandbox_ready=True)
        self.assertEqual(allowed.status, "planned")
        self.assertFalse(allowed.executor_authorized)

    def test_external_actions_require_human_gate_even_if_provider_connected(self):
        plan = self.plan("commerce", "external_action")
        self.assertTrue(plan.approval_required)
        self.assertEqual(plan.status, "blocked")
        for op in SENSITIVE_ACTIONS:
            self.assertFalse(may_perform_external_action(op))

    def test_unknown_intents_and_actions_fail_closed(self):
        for bad in (AssistantRequest(intent="unknown"), AssistantRequest(action="deploy"),
                    AssistantRequest(complex_work="yes")):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                plan_assistance(bad, role_providers=ASSIGNMENTS,
                                connected_providers=CONNECTED)

    def test_provider_inventory_must_be_immutable(self):
        with self.assertRaises(TypeError):
            plan_assistance(AssistantRequest(), role_providers=ASSIGNMENTS,
                            connected_providers={"openai-codex"})


if __name__ == "__main__":
    unittest.main()
