"""Offline contract tests. No Hermes, Codex or GitHub credentials required."""
import pathlib
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from cli import orquestra as cli


class CliTests(unittest.TestCase):
    def test_repos_are_explicit_allowlist(self):
        self.assertEqual(set(cli.REPOSITORIES), {"argoplace", "origin"})

    def test_test_task_uses_scratch_and_named_profile(self):
        with patch.object(cli, "create_task") as task:
            cli.test_task()
            board, title, body, workspace = task.call_args.args
            self.assertEqual(board, "origin")
            self.assertEqual(workspace, "scratch")
            self.assertIn("Não modifique", body)

    def test_create_task_no_shell_and_hardened_defaults(self):
        with patch.object(cli, "ensure_profile_and_board"), patch.object(cli, "hermes") as call:
            call.return_value.stdout = "created"
            cli.create_task("origin", "Teste", "Analise", "scratch")
            args = call.call_args.args
            self.assertIn("--assignee", args)
            self.assertEqual(args[args.index("--assignee")+1], "nagi")
            self.assertIn("--workspace", args)
            self.assertEqual(args[args.index("--workspace")+1], "scratch")
            self.assertEqual(args[args.index("--max-retries")+1], "1")

    def test_investigate_invalid_prompt_no_git(self):
        with patch.object(cli, "call") as command:
            with self.assertRaises(cli.CliError):
                cli.investigation("origin", "")
            command.assert_not_called()

    def test_investigate_isolated_worktree(self):
        with tempfile.TemporaryDirectory() as d:
            repo = pathlib.Path(d) / "origin"
            repo.mkdir()
            (repo / ".git").mkdir()
            dest = pathlib.Path(d) / "sandbox" / "origin-000"
            with patch.object(cli,"project_directory",return_value=repo), \
                 patch.object(cli,"worktree_directory",return_value=dest), \
                 patch.object(cli,"check_executable"), \
                 patch.object(cli,"ensure_profile_and_board"), \
                 patch.object(cli,"call") as git, \
                 patch.object(cli,"create_task") as create:
                git.return_value.returncode=0
                cli.investigation("origin", "Mapear filas")
                command=git.call_args.args[0]
                self.assertEqual(command[:4],["git","-C",str(repo),"worktree"])
                self.assertEqual(command[4:],["add","--detach",str(dest),"HEAD"])
                self.assertEqual(create.call_args.args[3], f"dir:{dest}")
                self.assertIn("NÃO fazer push",create.call_args.args[2])

    def test_argv_treated_as_array_no_shell(self):
        with patch.object(cli.subprocess,"run") as runner:
            runner.return_value.returncode=0
            runner.return_value.stdout="ok"
            cli.call(["hermes","kanban","create","title; echo not-executed"])
            self.assertFalse(runner.call_args.kwargs["shell"])


    def test_gemini_nonzero_stops_no_fallback(self):
        with tempfile.TemporaryDirectory() as folder:
            repo = pathlib.Path(folder)
            (repo / "AGENTS.md").write_text("Read-only rules.", encoding="utf-8")
            with patch.object(cli, "check_executable"), \
                 patch.object(cli, "project_directory", return_value=repo), \
                 patch.object(cli.subprocess, "run") as process:
                process.return_value.returncode = 53
                process.return_value.stdout = ""
                with self.assertRaisesRegex(cli.CliError, "Gemini falhou"):
                    cli.gemini_plan("argoplace", "Verificar módulo")
                args = process.call_args.args[0]
                self.assertEqual(args[0], "gemini")
                self.assertIn("plan", args)
                self.assertFalse(process.call_args.kwargs["shell"])
                self.assertNotIn("GEMINI_API_KEY",process.call_args.kwargs["env"])

    def test_gemini_handoff_to_hermes_nagi(self):
        with tempfile.TemporaryDirectory() as folder:
            repo = pathlib.Path(folder) / "vitalhub"
            repo.mkdir()
            (repo / ".git").mkdir()
            target = pathlib.Path(folder) / "sandbox"
            with patch.object(cli,"project_directory",return_value=repo), \
                 patch.object(cli,"worktree_directory",return_value=target), \
                 patch.object(cli,"check_executable"), \
                 patch.object(cli,"ensure_profile_and_board"), \
                 patch.object(cli,"gemini_plan",return_value="Plano Gemini: revisar rotas"), \
                 patch.object(cli,"call") as git, \
                 patch.object(cli,"create_task") as created:
                git.return_value.returncode=0
                cli.investigation("argoplace", "Investigar expedição", use_gemini=True)
                body = created.call_args.args[2]
                self.assertIn("Plano Gemini: revisar rotas", body)
                self.assertIn("INVESTIGACAO APENAS", body)
                self.assertEqual(created.call_args.args[0], "argoplace")


if __name__ == '__main__': unittest.main()
