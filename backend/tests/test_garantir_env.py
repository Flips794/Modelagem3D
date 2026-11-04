"""Testa scripts/garantir_env_backend.sh com um `docker` falso.

Roda no host: python3 -m unittest backend/tests/test_garantir_env.py
"""
from __future__ import annotations

import os
import shutil
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "garantir_env_backend.sh"
EXAMPLE = REPO_ROOT / "backend" / ".env.example"

FAKE_DOCKER = """#!/usr/bin/env bash
# docker falso: responde a inspect do container e a listagem de volumes.
if [[ "$1" == "inspect" ]]; then
  if [[ -n "${FAKE_CONTAINER_PASSWORD:-}" ]]; then
    printf 'PATH=/usr/bin\\nPOSTGRES_PASSWORD=%s\\nPOSTGRES_DB=modelagem3d_db\\n' "$FAKE_CONTAINER_PASSWORD"
    exit 0
  fi
  echo "Error: No such object" >&2; exit 1
fi
if [[ "$1" == "volume" && "$2" == "ls" ]]; then
  printf '%s\\n' ${FAKE_VOLUMES:-}
  exit 0
fi
exit 0
"""


@unittest.skipUnless(shutil.which("bash") and (REPO_ROOT / "backend").is_dir(),
                     "requer bash e a raiz do repositório (roda no host)")
class GarantirEnvBackend(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        (self.tmp / "backend").mkdir()
        shutil.copy(EXAMPLE, self.tmp / "backend" / ".env.example")
        bindir = self.tmp / "bin"
        bindir.mkdir()
        fake = bindir / "docker"
        fake.write_text(FAKE_DOCKER)
        fake.chmod(fake.stat().st_mode | stat.S_IEXEC)
        self.env = {**os.environ, "PATH": f"{bindir}:{os.environ['PATH']}"}

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def run_script(self, **extra):
        return subprocess.run(["bash", str(SCRIPT), str(self.tmp)], env={**self.env, **extra},
                              capture_output=True, text=True)

    def env_file(self) -> Path:
        return self.tmp / "backend" / ".env"

    def read_env(self) -> dict[str, str]:
        pairs = {}
        for line in self.env_file().read_text().splitlines():
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                pairs[key] = value
        return pairs

    def test_existing_env_is_untouched(self):
        self.env_file().write_text("POSTGRES_PASSWORD=minha\n")
        result = self.run_script(FAKE_CONTAINER_PASSWORD="outra")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.env_file().read_text(), "POSTGRES_PASSWORD=minha\n")

    def test_reuses_password_of_existing_container(self):
        result = self.run_script(FAKE_CONTAINER_PASSWORD="senha_atual_123")
        self.assertEqual(result.returncode, 0, result.stderr)
        env = self.read_env()
        self.assertEqual(env["POSTGRES_PASSWORD"], "senha_atual_123")
        self.assertIn(":senha_atual_123@", env["DATABASE_URL"])
        self.assertNotIn("CHANGE_ME", self.env_file().read_text())
        self.assertEqual(stat.S_IMODE(self.env_file().stat().st_mode), 0o600)

    def test_fresh_install_generates_random_password(self):
        result = self.run_script()
        self.assertEqual(result.returncode, 0, result.stderr)
        password = self.read_env()["POSTGRES_PASSWORD"]
        self.assertGreaterEqual(len(password), 24)
        self.assertNotEqual(password, "CHANGE_ME")
        self.assertRegex(password, r"^[A-Za-z0-9]+$")

    def test_volume_without_container_aborts(self):
        result = self.run_script(FAKE_VOLUMES="backend_modelagem3d_pgdata")
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.env_file().exists())
        self.assertIn("backend/.env", result.stderr)


if __name__ == "__main__":
    unittest.main()
