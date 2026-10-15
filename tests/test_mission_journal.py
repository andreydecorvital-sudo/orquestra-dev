"""Recovery tests: never claim an unfinished mission is completed."""
import pathlib
import tempfile
import unittest

from orchestration.mission_journal import MissionJournal, MissionJournalBlocked
from runner.agent_worker import deliver_task

TASK = {"id": "mission-uuid-01", "project_id": "remote-01", "kind": "codex",
        "title": "Corrigir tela", "instructions": "Aplicar correção local validada",
        "attempt": 1}
CONFIG = {"node_id": "authorized-node", "projects": {}, "allow_execution": True}


class MissionReceiptTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = pathlib.Path(self.temp.name)
        self.artifacts = self.root / "artifacts"
        self.artifacts.mkdir()
        self.journal = MissionJournal(root=self.root / "receipts",
                                      artifacts_root=self.artifacts,
                                      node_id=CONFIG["node_id"])
        self.patch = self.artifacts / "generated.patch"
        self.patch.write_text("diff --git a/README.md b/README.md\n", encoding="utf-8")

    def result(self):
        return {"status": "review_required", "provider": "codex",
                "artifact_path": str(self.patch),
                "quality": {"tests": "not_run", "autonomous_repairs": 1},
                "stages": [{"role": "codex", "step": "implement"}]}

    def test_saved_patch_survives_new_journal_instance(self):
        self.assertIsNone(self.journal.begin(TASK))
        self.journal.complete(TASK, self.result(), "Patch revisável")
        reloaded = MissionJournal(root=self.root / "receipts",
                                  artifacts_root=self.artifacts,
                                  node_id=CONFIG["node_id"])
        self.assertEqual(reloaded.begin({**TASK, "attempt": 2}), "Patch revisável")

    def test_repeated_claim_without_completion_is_not_replayed(self):
        self.assertIsNone(self.journal.begin(TASK))
        with self.assertRaisesRegex(MissionJournalBlocked, "sem recibo"):
            self.journal.begin({**TASK, "attempt": 2})

    def test_mutated_instructions_cannot_reuse_receipt(self):
        self.journal.begin(TASK)
        self.journal.complete(TASK, self.result(), "Patch revisável")
        with self.assertRaisesRegex(MissionJournalBlocked, "não corresponde"):
            self.journal.begin({**TASK, "instructions": "Alterar outra coisa"})

    def test_tampered_patch_is_blocked(self):
        self.journal.begin(TASK)
        self.journal.complete(TASK, self.result(), "Patch revisável")
        self.patch.write_text("modified", encoding="utf-8")
        with self.assertRaisesRegex(MissionJournalBlocked, "Integridade"):
            self.journal.begin({**TASK, "attempt": 3})

    def test_proof_must_be_inside_allowlisted_directory(self):
        other = self.root / "other.patch"
        other.write_text("unsafe")
        self.journal.begin(TASK)
        with self.assertRaisesRegex(MissionJournalBlocked, "fora"):
            self.journal.complete(TASK, {**self.result(), "artifact_path": str(other)}, "Resumo")

    def test_node_identity_is_part_of_receipt(self):
        self.journal.begin(TASK)
        self.journal.complete(TASK, self.result(), "Resumo")
        other = MissionJournal(root=self.root / "receipts",
                               artifacts_root=self.artifacts, node_id="different-node")
        with self.assertRaisesRegex(MissionJournalBlocked, "não corresponde"):
            other.begin(TASK)

    def test_worker_reuses_verified_receipt_without_second_cli_call(self):
        calls = []
        def fake_execute(cfg, task):
            calls.append(task["attempt"])
            return self.result()
        output1 = deliver_task(CONFIG, TASK, execute=fake_execute, journal=self.journal)
        output2 = deliver_task(CONFIG, {**TASK, "attempt": 2},
                               execute=fake_execute, journal=self.journal)
        self.assertEqual(output1, output2)
        self.assertEqual(calls, [1])
        self.assertIn("Patch preparado", output1)
        self.assertIn("Testes do projeto: not_run", output1)

    def test_crash_prior_to_local_result_does_not_invoke_again(self):
        calls = []
        def crash(cfg, task):
            calls.append("CLI")
            raise OSError("timeout after side effect")
        with self.assertRaises(OSError):
            deliver_task(CONFIG, TASK, execute=crash, journal=self.journal)
        with self.assertRaises(MissionJournalBlocked):
            deliver_task(CONFIG, {**TASK, "attempt": 2},
                         execute=crash, journal=self.journal)
        self.assertEqual(calls, ["CLI"])

    def test_corrupted_receipt_requires_reconciliation(self):
        self.journal.begin(TASK)
        path = self.journal._file(TASK)
        path.write_text("{broken json", encoding="utf-8")
        with self.assertRaisesRegex(MissionJournalBlocked, "corrompido"):
            self.journal.begin(TASK)


if __name__ == "__main__":
    unittest.main()
