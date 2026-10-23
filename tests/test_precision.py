"""Regression tests for the zero-extra-provider-call precision preflight."""
from __future__ import annotations

import pathlib
import subprocess
import tempfile
import unittest
from unittest import mock

from orchestration.precision import (
    PrecisionError, inspect_before_code, precision_instructions,
)
from gateway.engine import execute_job


def git(root: pathlib.Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=root, capture_output=True, check=True)


def fixture(root: pathlib.Path) -> pathlib.Path:
    repo = root / "repo"
    repo.mkdir()
    git(repo, "init", "-q")
    git(repo, "config", "user.name", "Test")
    git(repo, "config", "user.email", "test@example.invalid")
    (repo / "AGENTS.md").write_text("# Instrucoes locais\n")
    folder = repo / "src" / "shopee"
    folder.mkdir(parents=True)
    (folder / "orders.py").write_text("def sincronizar():\n    return 1\n")
    git(repo, "add", ".")
    git(repo, "commit", "-qm", "initial")
    return repo


class PrecisionPreflightTests(unittest.TestCase):
    def test_read_only_evidence_and_relevant_paths(self):
        with tempfile.TemporaryDirectory() as folder:
            repo = fixture(pathlib.Path(folder))
            baseline = subprocess.run(["git", "status", "--porcelain"],
                cwd=repo, capture_output=True, text=True, check=True).stdout
            ctx = inspect_before_code(repo, "Corrigir bug da Shopee em orders")
            self.assertEqual(len(ctx["base_sha"]), 40)
            self.assertIn("AGENTS.md", ctx["project_instructions"])
            self.assertIn("src/shopee/orders.py", ctx["candidate_paths"])
            self.assertEqual(ctx["extra_model_calls"], 0)
            after = subprocess.run(["git", "status", "--porcelain"],
                cwd=repo, capture_output=True, text=True, check=True).stdout
            self.assertEqual(after, baseline)

    def test_missing_git_blocks_preflight(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(PrecisionError):
                inspect_before_code(pathlib.Path(folder), "Corrigir bug da Shopee")

    def test_prompt_requires_proof_before_code(self):
        with tempfile.TemporaryDirectory() as folder:
            repo = fixture(pathlib.Path(folder))
            ctx = inspect_before_code(repo, "Corrigir bug na Shopee")
            prompt = precision_instructions("Corrigir bug na Shopee", ctx)
            self.assertIn("ANTES DE CODAR", prompt)
            self.assertIn("NAO invente patch", prompt)
            self.assertIn("src/shopee/orders.py", prompt)
            self.assertIn("NAO sao prova da causa", prompt)

    def test_engine_runs_precision_first_without_extra_cli(self):
        with tempfile.TemporaryDirectory() as folder:
            root = pathlib.Path(folder)
            repo = fixture(root)
            home = root / "home"
            home.mkdir()
            calls = []

            def fake_cli(provider, prompt, cwd):
                calls.append((provider, prompt))
                (cwd / "src" / "shopee" / "orders.py").write_text(
                    "def sincronizar():\n    return 2\n")
                return {"output": "patch pronto", "ok": True}

            with (mock.patch("gateway.engine.pathlib.Path.home", return_value=home),
                  mock.patch("gateway.engine.billing_keys_present", return_value=[])):
                result = execute_job(
                    {"projects": {"testing": str(repo)}, "allow_execution": True},
                    {"project": "testing", "provider": "codex", "type": "code",
                     "prompt": "Corrigir falha de sincronizacao na Shopee"},
                    cli=fake_cli,
                )
            self.assertEqual(len(calls), 1)
            self.assertEqual(calls[0][0], "codex")
            self.assertIn("PROTOCOLO PRECISION ENGINEERING", calls[0][1])
            self.assertIn("ANTES DE CODAR", calls[0][1])
            self.assertEqual(result["quality"]["precision_preflight"], "read_only_completed")
            self.assertEqual(result["quality"]["tests"], "not_run")
            self.assertEqual(result["stages"][0]["step"], "precision_preflight")
            self.assertEqual((repo / "src" / "shopee" / "orders.py").read_text(),
                             "def sincronizar():\n    return 1\n")
            self.assertTrue(list((home / ".orquestra" / "artifacts").glob("*.patch")))


if __name__ == "__main__":
    unittest.main()
