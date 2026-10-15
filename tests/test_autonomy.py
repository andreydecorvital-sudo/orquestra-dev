"""Autonomous progress without broad production privileges."""
import unittest

from orchestration.autonomy import decide_action
from orchestration.mission_loop import MissionQualityExhausted, repair_failed_quality
from orchestration.quality import QualityError


class ApprovalPolicyTests(unittest.TestCase):
    def test_obvious_safe_work_does_not_ask(self):
        for action in ("read_repository", "read_project_context", "plan_mission",
                       "choose_minor_default", "edit_isolated_worktree",
                       "run_allowlisted_checks", "repair_isolated_worktree",
                       "save_local_patch", "produce_report"):
            with self.subTest(action=action):
                self.assertTrue(decide_action(action).may_execute)

    def test_consequential_actions_require_approval(self):
        for action in ("deploy_production", "merge_pull_request", "modify_live_database",
                       "change_live_prices", "publish_live_listing", "issue_invoice",
                       "print_shipping_labels", "send_external_message", "spend_money"):
            with self.subTest(action=action):
                self.assertEqual(decide_action(action).status, "approval_required")

    def test_unknown_and_unauthorized_fail_closed(self):
        self.assertEqual(decide_action("run_any_shell_command").status, "blocked")
        self.assertEqual(decide_action("read_repository", authorized_project=False).status, "blocked")
        self.assertEqual(decide_action("repair_isolated_worktree", isolated_environment=False).status,
                         "approval_required")
        self.assertEqual(decide_action("save_local_patch", elevated_risk=True).status,
                         "approval_required")


class MissionLoopTests(unittest.TestCase):
    def test_success_does_not_call_repair(self):
        events = []
        result = repair_failed_quality(verify=lambda: {"ok": True},
            repair=lambda *_: events.append("repair"),
            checkpoint=lambda: events.append("checkpoint"))
        self.assertEqual(result["repairs"], 0)
        self.assertEqual(events, [])

    def test_repairs_until_verified(self):
        state = {"errors": 2, "checkpoint": 0}
        def verify():
            if state["errors"]:
                raise QualityError("invalid syntax")
            return {"tests": "passed"}
        def repair(reason, attempt):
            self.assertEqual(reason, "invalid syntax")
            self.assertLessEqual(attempt, 2)
            state["errors"] -= 1
        def checkpoint():
            state["checkpoint"] += 1
        result = repair_failed_quality(verify=verify, repair=repair,
                                       checkpoint=checkpoint, max_repairs=2)
        self.assertEqual(result["repairs"], 2)
        self.assertEqual(state["checkpoint"], 2)
        self.assertEqual(result["quality"]["tests"], "passed")

    def test_exhaustion_never_claims_success(self):
        changes = []
        with self.assertRaises(MissionQualityExhausted):
            repair_failed_quality(verify=lambda: (_ for _ in ()).throw(QualityError("still invalid")),
                repair=lambda reason, attempt: changes.append(attempt),
                checkpoint=lambda: changes.append("saved"), max_repairs=2)
        self.assertEqual(changes, [1, "saved", 2, "saved"])

    def test_partial_work_is_saved_on_repair_failure(self):
        events = []
        def broken_repair(reason, attempt):
            events.append("repair")
            raise RuntimeError("CLI failed")
        with self.assertRaisesRegex(RuntimeError, "CLI failed"):
            repair_failed_quality(verify=lambda: (_ for _ in ()).throw(QualityError("bad")),
                repair=broken_repair, checkpoint=lambda: events.append("saved"))
        self.assertEqual(events, ["repair", "saved"])

    def test_rejects_bad_budget(self):
        for value in (True, -1, 6, 1.5):
            with self.subTest(value=value), self.assertRaises(ValueError):
                repair_failed_quality(verify=lambda: {}, repair=lambda *_: None,
                                      checkpoint=lambda: None, max_repairs=value)


if __name__ == "__main__":
    unittest.main()
