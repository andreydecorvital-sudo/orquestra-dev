"""Crash-safe, local receipt journal for Orquestra code missions.

Records task identity BEFORE invoking an external coding CLI. If the worker
crashes after execution but before Supabase acknowledges completion, retries
reuse only a verified saved receipt. A half-finished task is NOT replayed
blindly: its external effects cannot yet be reconciled automatically.

This is stage-one durable delivery, not a resumable worktree/goal engine.
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import tempfile
from typing import Any


class MissionJournalBlocked(RuntimeError):
    """A task requires reconciliation rather than an unsafe replay."""


def fingerprint(task: dict[str, Any], node_id: str) -> str:
    fields = {name: task.get(name) for name in
              ("id", "project_id", "kind", "title", "instructions")}
    fields["node_id"] = node_id
    if not isinstance(fields["id"], str) or not 1 <= len(fields["id"]) <= 180:
        raise MissionJournalBlocked("ID de missão inválido")
    try:
        raw = json.dumps(fields, sort_keys=True, ensure_ascii=True,
                         separators=(",", ":"), allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise MissionJournalBlocked("Dados de missão inválidos") from exc
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class MissionJournal:
    def __init__(self, *, root: pathlib.Path, artifacts_root: pathlib.Path, node_id: str):
        self.root = root.expanduser().resolve()
        self.artifacts_root = artifacts_root.expanduser().resolve()
        if not node_id:
            raise ValueError("node_id obrigatório")
        self.node_id = node_id

    def _file(self, task: dict[str, Any]) -> pathlib.Path:
        # The remote ID never becomes a filename or path segment.
        digest = hashlib.sha256(str(task.get("id", "")).encode("utf-8")).hexdigest()
        return self.root / (digest + ".json")

    def _load(self, task: dict[str, Any]) -> dict[str, Any] | None:
        path = self._file(task)
        if not path.exists():
            return None
        if path.is_symlink() or not path.is_file() or path.stat().st_size > 20000:
            raise MissionJournalBlocked("Journal não é um arquivo regular válido")
        try:
            obj = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise MissionJournalBlocked("Journal corrompido; reconciliação obrigatória") from exc
        if not isinstance(obj, dict) or obj.get("fingerprint") != fingerprint(task, self.node_id):
            raise MissionJournalBlocked("A missão não corresponde ao journal persistido")
        return obj

    def _atomic_replace(self, path: pathlib.Path, data: dict[str, Any]) -> None:
        self.root.mkdir(mode=0o700, parents=True, exist_ok=True)
        content = json.dumps(data, sort_keys=True, ensure_ascii=True)
        tmp = None
        try:
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8",
                    dir=self.root, prefix=".journal-", suffix=".tmp",
                    delete=False) as stream:
                tmp = pathlib.Path(stream.name)
                os.chmod(tmp, 0o600)
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(tmp, path)
        finally:
            if tmp and tmp.exists():
                tmp.unlink()

    def begin(self, task: dict[str, Any]) -> str | None:
        """Return cached proof, or claim a new task. Never re-run uncertainty."""
        known = self._load(task)
        if known is not None:
            if known.get("status") != "ready":
                raise MissionJournalBlocked("Execução anterior sem recibo; reconciliar patch antes de repetir")
            proof = known.get("artifact")
            if not isinstance(proof, dict):
                raise MissionJournalBlocked("Recibo não possui prova do patch persistido")
            self._verify_artifact(proof)
            output = known.get("output")
            if not isinstance(output, str) or not output or len(output) > 18000:
                raise MissionJournalBlocked("Recibo de entrega inválido")
            return output

        self.root.mkdir(mode=0o700, parents=True, exist_ok=True)
        path = self._file(task)
        # Exclusive create: never replace a concurrent worker's reservation.
        try:
            with path.open("x", encoding="utf-8") as stream:
                os.chmod(path, 0o600)
                json.dump({"version": 1, "status": "running",
                           "fingerprint": fingerprint(task, self.node_id)},
                          stream, sort_keys=True)
                stream.flush()
                os.fsync(stream.fileno())
        except FileExistsError as exc:
            raise MissionJournalBlocked("Outra tentativa já reservou esta missão") from exc
        return None

    def _verify_artifact(self, proof: dict[str, Any]) -> None:
        raw_path = proof.get("path")
        digest = proof.get("sha256")
        if not isinstance(raw_path, str) or not isinstance(digest, str):
            raise MissionJournalBlocked("Evidência local inválida")
        path = pathlib.Path(raw_path)
        if not path.is_absolute() or path.is_symlink():
            raise MissionJournalBlocked("Caminho de evidência inválido")
        path = path.resolve()
        if not path.is_relative_to(self.artifacts_root) or path.suffix != ".patch":
            raise MissionJournalBlocked("Patch fora do diretório autorizado")
        if not path.is_file() or path.stat().st_size > 10_000_000:
            raise MissionJournalBlocked("Patch indisponível para reconciliação")
        if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise MissionJournalBlocked("Integridade do patch divergente")

    def complete(self, task: dict[str, Any], result: dict[str, Any], output: str) -> None:
        """Save a LOCAL verified artifact before acknowledging task completion."""
        known = self._load(task)
        if not known or known.get("status") != "running":
            raise MissionJournalBlocked("Missão não foi reservada para execução")
        if result.get("status") != "review_required":
            raise MissionJournalBlocked("Execução não produziu status de revisão")
        raw = result.get("artifact_path")
        if not isinstance(raw, str):
            raise MissionJournalBlocked("Execução não produziu patch persistido")
        path = pathlib.Path(raw).resolve()
        if not path.is_relative_to(self.artifacts_root):
            raise MissionJournalBlocked("Patch fora do armazenamento autorizado")
        if not path.is_file() or path.is_symlink():
            raise MissionJournalBlocked("Patch ausente ou simbólico")
        if not isinstance(output, str) or not output or len(output) > 18000:
            raise MissionJournalBlocked("Resumo inválido")
        proof = {"path": str(path),
                 "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
        self._verify_artifact(proof)
        self._atomic_replace(self._file(task), {
            "version": 1, "status": "ready",
            "fingerprint": fingerprint(task, self.node_id),
            "artifact": proof, "output": output,
        })
