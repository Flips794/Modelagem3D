"""Impede credenciais em arquivos versionados.

Roda no host (precisa do git e da raiz do repositório):
    python3 -m unittest backend/tests/test_no_secrets.py
Dentro do container de testes não há git nem a raiz do projeto; o teste é pulado.
"""
from __future__ import annotations

import re
import shutil
import subprocess
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
ALLOWED_URL_PASSWORDS = {"CHANGE_ME", "validation", "v", "<redacted>"}
# O valor precisa começar como um valor (não pega padrões de sed como s/^POSTGRES_PASSWORD=//p).
PASSWORD_ASSIGNMENT = re.compile(r"\bPOSTGRES_PASSWORD\s*[:=]\s*([A-Za-z0-9_$<'\"`][^\s#]*)")
DB_URL_WITH_PASSWORD = re.compile(r"postgresql(?:\+psycopg)?://[^:/\s\"']+:([^@\s\"']+)@")
ENV_FILE_NAMES = {".env", ".env.local", ".env.production", ".env.fumaca"}
# Arquivos de teste que usam senhas falsas de propósito para exercitar o script.
FAKE_CREDENTIAL_FIXTURES = {"backend/tests/test_garantir_env.py"}


def _git_available() -> bool:
    return shutil.which("git") is not None and (REPO_ROOT / ".git").exists()


def _tracked_files() -> list[str]:
    out = subprocess.run(["git", "ls-files", "-z"], cwd=REPO_ROOT, check=True, capture_output=True).stdout
    return [p for p in out.decode("utf-8").split("\0") if p]


def _tracked_text(path: str) -> str | None:
    full = REPO_ROOT / path
    try:
        data = full.read_bytes()
    except OSError:
        return None
    if b"\0" in data[:4096]:
        return None
    return data.decode("utf-8", errors="replace")


@unittest.skipUnless(_git_available(), "requer git e a raiz do repositório")
class NoSecretsInTrackedFiles(unittest.TestCase):
    def test_no_real_env_file_is_tracked(self):
        tracked_env = [p for p in _tracked_files() if p.split("/")[-1] in ENV_FILE_NAMES]
        self.assertEqual(tracked_env, [])

    def test_postgres_password_assignments_are_placeholders(self):
        offenders = []
        for path in _tracked_files():
            text = _tracked_text(path)
            if text is None or path in FAKE_CREDENTIAL_FIXTURES:
                continue
            for line_no, line in enumerate(text.splitlines(), 1):
                for match in PASSWORD_ASSIGNMENT.finditer(line):
                    value = re.split(r"\\n|[\"'`)]", match.group(1))[0]
                    # ${VAR} vem do ambiente; $(comando) é gerado na execução (ex.: openssl rand).
                    if value in ALLOWED_URL_PASSWORDS or value.startswith(("${", "$(")):
                        continue
                    offenders.append(f"{path}:{line_no}")
        self.assertEqual(offenders, [])

    def test_database_urls_have_no_literal_password(self):
        offenders = []
        for path in _tracked_files():
            text = _tracked_text(path)
            if text is None:
                continue
            for line_no, line in enumerate(text.splitlines(), 1):
                for match in DB_URL_WITH_PASSWORD.finditer(line):
                    password = match.group(1)
                    if password in ALLOWED_URL_PASSWORDS or password.startswith("${"):
                        continue
                    offenders.append(f"{path}:{line_no}")
        self.assertEqual(offenders, [])


if __name__ == "__main__":
    unittest.main()
