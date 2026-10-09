"""Deterministic offline checks for an agent-produced Git worktree.

Never runs project tests, installs packages, reads browser cookies, or calls
provider APIs. These results are NOT a full security or integration audit.
"""
from __future__ import annotations

import ast
import pathlib
import shutil
import subprocess


class QualityError(RuntimeError):
    """A deterministic quality gate failed; no raw tool logs are returned."""


RISK_PATHS = (
    '.github/workflows/', '.env', '.env.', 'supabase/migrations/',
    'database/migrations/', 'prisma/migrations/', 'vercel.json',
    'package-lock.json', 'pnpm-lock.yaml', 'yarn.lock',
)


def inspect_worktree(worktree: pathlib.Path) -> dict[str, object]:
    """Validate a worktree with git intent-to-add already applied."""
    check = subprocess.run(['git', 'diff', '--check', 'HEAD'], cwd=worktree,
                           capture_output=True, timeout=25, shell=False)
    if check.returncode:
        raise QualityError('Git diff --check falhou (whitespace/conflito)')
    listed = subprocess.run(['git', 'diff', '--name-only', '-z', 'HEAD'],
                            cwd=worktree, capture_output=True, timeout=25,
                            shell=False)
    if listed.returncode:
        raise QualityError('Não foi possível listar os arquivos alterados')
    names = [s.decode('utf-8', errors='replace')
             for s in listed.stdout.split(b'\0') if s]
    parsed_py = 0
    checked_js = 0
    js_available = bool(shutil.which('node'))
    risk_flags: list[str] = []
    for name in names:
        normalized = name.lower().replace('\\', '/')
        if any(normalized == p or normalized.startswith(p) for p in RISK_PATHS):
            risk_flags.append(name)
        path = worktree / name
        if path.is_symlink():
            raise QualityError('Link simbólico alterado exige revisão manual: ' + name[:120])
        if not path.resolve(strict=False).is_relative_to(worktree.resolve()):
            raise QualityError('Caminho alterado fora do worktree autorizado')
        if not path.is_file():
            continue  # Deleted file, no syntax to parse.
        if path.suffix.lower() == '.py':
            if path.stat().st_size > 2_000_000:
                raise QualityError('Arquivo Python muito grande para verificação sintática')
            try:
                ast.parse(path.read_text(encoding='utf-8-sig'), filename=name)
            except (SyntaxError, UnicodeError, ValueError):
                raise QualityError('Sintaxe Python inválida: ' + name[:120]) from None
            parsed_py += 1
        if path.suffix.lower() in {'.js', '.cjs', '.mjs'} and js_available:
            try:
                scan = subprocess.run(['node', '--check', str(path)],
                                      cwd=worktree, capture_output=True,
                                      timeout=20, shell=False)
            except (OSError, subprocess.TimeoutExpired):
                raise QualityError('Não foi possível validar sintaxe JavaScript') from None
            if scan.returncode:
                raise QualityError('Sintaxe JavaScript inválida: ' + name[:120])
            checked_js += 1
    return {
        'whitespace': 'passed',
        'python_syntax_files': parsed_py,
        'javascript_syntax_files': checked_js,
        'javascript_checker': 'available' if js_available else 'unavailable',
        'changed_files': len(names),
        'risk_flags': risk_flags[:25],
        'tests': 'not_run',
        'security_audit': 'not_run',
        'human_approval_required': True,
    }
