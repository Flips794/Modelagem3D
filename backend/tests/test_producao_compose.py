"""Tarefa 13: compose de produção, backup/restauração e segredos fora do git.

Roda no host (precisa do docker compose e da raiz do repositório):
    python3 -m unittest backend/tests/test_producao_compose.py
"""
from __future__ import annotations

import json
import os
import shutil
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
BASE = REPO_ROOT / "backend" / "docker-compose.yml"
PROD = REPO_ROOT / "backend" / "docker-compose.prod.yml"
PROD_EXAMPLE = REPO_ROOT / "backend" / ".env.production.example"
CADDYFILE = REPO_ROOT / "frontend" / "deploy" / "Caddyfile"
SCRIPTS = REPO_ROOT / "scripts"
FAKE_PASSWORD = "senha-falsa-de-teste"  # nunca usada fora deste teste
# No container de testes só backend/ está montado: estes testes rodam no host.
ON_HOST = (SCRIPTS / "garantir_env_backend.sh").exists()

ENV_TEXT = f"""POSTGRES_PASSWORD={FAKE_PASSWORD}
SITE_ADDRESS=:80
HTTP_PORT=8088
HTTPS_PORT=8443
BACKEND_CORS_ORIGINS=[]
UVICORN_WORKERS=1
"""


def _compose_available() -> bool:
    if shutil.which("docker") is None:
        return False
    return subprocess.run(["docker", "compose", "version"], capture_output=True).returncode == 0


def render(env_text: str = ENV_TEXT) -> subprocess.CompletedProcess:
    # Docker via snap não lê o /tmp do host: arquivo temporário em .runtime/ (ignorado pelo git).
    runtime = REPO_ROOT / ".runtime"
    runtime.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(dir=runtime) as tmp:
        env_file = Path(tmp) / "env"
        env_file.write_text(env_text)
        return subprocess.run(
            ["docker", "compose", "-p", "m3d_teste", "-f", str(BASE), "-f", str(PROD),
             "--env-file", str(env_file), "config", "--format", "json"],
            capture_output=True, text=True, cwd=REPO_ROOT,
        )


@unittest.skipUnless(ON_HOST and _compose_available(), "requer docker compose e a raiz do repositório")
class ProductionCompose(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        result = render()
        if result.returncode != 0:
            raise AssertionError(result.stderr)
        cls.config = json.loads(result.stdout)
        cls.services = cls.config["services"]

    def test_only_the_edge_is_published(self):
        self.assertEqual(set(self.services), {"postgres", "backend", "frontend"})
        self.assertFalse(self.services["postgres"].get("ports"))
        self.assertFalse(self.services["backend"].get("ports"))
        published = {(p["published"], p["target"]) for p in self.services["frontend"]["ports"]}
        self.assertIn(("8088", 80), published)
        self.assertIn(("8443", 443), published)

    def test_postgres_keeps_data_in_a_named_volume(self):
        mounts = self.services["postgres"]["volumes"]
        data = [m for m in mounts if m["target"] == "/var/lib/postgresql/data"]
        self.assertEqual(data[0]["type"], "volume")
        self.assertIn(data[0]["source"], self.config["volumes"])
        # Nome fixo do container colidiria com a pilha de desenvolvimento.
        self.assertNotIn("container_name", self.services["postgres"])

    def test_backend_runs_in_production_mode(self):
        env = self.services["backend"]["environment"]
        self.assertEqual(env["APP_ENV"], "production")
        self.assertEqual(env["BACKEND_CORS_ORIGINS"], "[]")
        self.assertEqual(env["UVICORN_WORKERS"], "1")
        self.assertIn(FAKE_PASSWORD, env["DATABASE_URL"])   # só vem do arquivo de ambiente

    def test_frontend_is_the_caddy_edge_with_relative_api(self):
        front = self.services["frontend"]
        self.assertEqual(front["build"]["target"], "prod")
        self.assertEqual(front["build"]["args"]["VITE_API_URL"], "/api/v1")
        self.assertEqual(front["environment"]["SITE_ADDRESS"], ":80")
        targets = {m["target"] for m in front["volumes"]}
        self.assertTrue({"/data", "/config"} <= targets)   # certificados TLS persistem
        self.assertNotIn("node", " ".join(front["healthcheck"]["test"]))

    def test_every_service_has_limits_restart_logs_and_hardening(self):
        for name, service in self.services.items():
            with self.subTest(service=name):
                limits = service["deploy"]["resources"]["limits"]
                self.assertGreater(float(limits["cpus"]), 0)
                self.assertGreater(int(limits["memory"]), 0)
                self.assertEqual(service["restart"], "unless-stopped")
                self.assertIn("no-new-privileges:true", service.get("security_opt", []))
                self.assertEqual(service["logging"]["options"]["max-size"], "10m")
                self.assertIn("healthcheck", service)

    def test_backend_and_edge_are_read_only_and_backend_not_root(self):
        backend = self.services["backend"]
        self.assertTrue(backend["read_only"])
        self.assertNotIn(backend["user"].split(":")[0], {"0", "root"})
        self.assertTrue(self.services["frontend"]["read_only"])
        self.assertEqual(self.services["frontend"]["cap_drop"], ["ALL"])

    def test_missing_password_or_site_address_fails_fast(self):
        no_password = "\n".join(l for l in ENV_TEXT.splitlines() if not l.startswith("POSTGRES_PASSWORD"))
        self.assertNotEqual(render(no_password).returncode, 0)
        no_site = "\n".join(l for l in ENV_TEXT.splitlines() if not l.startswith("SITE_ADDRESS"))
        self.assertNotEqual(render(no_site).returncode, 0)


@unittest.skipUnless(ON_HOST, "requer a raiz do repositório")
class ProductionFilesAndSecrets(unittest.TestCase):
    def test_production_env_example_has_only_placeholders(self):
        text = PROD_EXAMPLE.read_text(encoding="utf-8")
        for key in ("POSTGRES_PASSWORD=CHANGE_ME", "SITE_ADDRESS=", "BACKEND_CORS_ORIGINS=", "UVICORN_WORKERS=",
                    "HTTP_PORT=", "HTTPS_PORT="):
            self.assertIn(key, text)

    @unittest.skipUnless(shutil.which("git") and (REPO_ROOT / ".git").exists(), "requer git")
    def test_real_env_files_are_ignored_by_git(self):
        for path in ("backend/.env", "backend/.env.production", "backend/.env.fumaca", ".env.production"):
            with self.subTest(path=path):
                rc = subprocess.run(["git", "check-ignore", "-q", path], cwd=REPO_ROOT).returncode
                self.assertEqual(rc, 0, f"{path} não está no .gitignore")
        for path in ("backend/.env.example", "backend/.env.production.example"):
            rc = subprocess.run(["git", "check-ignore", "-q", path], cwd=REPO_ROOT).returncode
            self.assertEqual(rc, 1, f"{path} deveria ser versionado")

    def test_real_env_files_never_enter_docker_images(self):
        # backend/.env.production fica dentro do contexto do build: COPY . . o levaria para a imagem.
        for ignore in (REPO_ROOT / "backend" / ".dockerignore", REPO_ROOT / "frontend" / ".dockerignore"):
            with self.subTest(file=str(ignore)):
                patterns = ignore.read_text(encoding="utf-8").split()
                self.assertIn(".env", patterns)
                self.assertIn(".env.*", patterns)

    def test_caddy_has_internal_healthcheck_endpoint(self):
        text = CADDYFILE.read_text(encoding="utf-8")
        self.assertIn("/healthz", text)
        self.assertIn("bind 127.0.0.1", text)

    def test_scripts_are_valid_bash(self):
        for name in ("backup_producao.sh", "restaurar_producao.sh", "fumaca_producao.sh"):
            with self.subTest(script=name):
                path = SCRIPTS / name
                self.assertTrue(path.exists())
                self.assertEqual(subprocess.run(["bash", "-n", str(path)]).returncode, 0)

    def test_local_compat_file_only_relaxes_no_new_privileges(self):
        text = (REPO_ROOT / "backend" / "docker-compose.compat-local.yml").read_text(encoding="utf-8")
        body = [l.strip() for l in text.splitlines() if l.strip() and not l.lstrip().startswith("#")]
        self.assertEqual(body, ["services:", "postgres:", "security_opt: !reset []", "backend:",
                                "security_opt: !reset []", "frontend:", "security_opt: !reset []"])
        self.assertNotIn("compat-local", PROD.read_text(encoding="utf-8"))
        self.assertNotIn("compat-local", (SCRIPTS / "backup_producao.sh").read_text(encoding="utf-8"))

    def test_smoke_only_ever_removes_its_own_project(self):
        text = (SCRIPTS / "fumaca_producao.sh").read_text(encoding="utf-8")
        self.assertIn('readonly PROJECT="m3d_fumaca"', text)
        for line in text.splitlines():
            if "down" in line and "-v" in line:
                self.assertIn("compose_fumaca", line)   # função que fixa -p "$PROJECT"


FAKE_DOCKER = """#!/usr/bin/env bash
# docker falso: registra a chamada; pg_dump escreve bytes; FAKE_FAIL=1 simula falha.
echo "$*" >> "$FAKE_LOG"
if [[ "${FAKE_FAIL:-0}" == 1 ]]; then echo "falha simulada" >&2; exit 1; fi
if [[ "$*" == *pg_dump* ]]; then printf 'PGDMP-falso'; fi
exit 0
"""


@unittest.skipUnless(ON_HOST, "requer a raiz do repositório")
class BackupAndRestoreScripts(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="m3d backup "))   # espaço no caminho, como no projeto
        bin_dir = self.tmp / "bin"
        bin_dir.mkdir()
        docker = bin_dir / "docker"
        docker.write_text(FAKE_DOCKER)
        docker.chmod(docker.stat().st_mode | stat.S_IEXEC)
        self.log = self.tmp / "docker.log"
        self.backups = self.tmp / "cópias de segurança"
        self.env = {**os.environ, "PATH": f"{bin_dir}:{os.environ['PATH']}", "FAKE_LOG": str(self.log),
                    "BACKUP_DIR": str(self.backups), "ENV_FILE": str(self.tmp / "env"), "COMPOSE_PROJECT": "m3d_teste"}
        (self.tmp / "env").write_text(ENV_TEXT)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def run_script(self, name, *args, stdin="", **extra_env):
        return subprocess.run(["bash", str(SCRIPTS / name), *args], input=stdin, capture_output=True, text=True,
                              env={**self.env, **extra_env}, cwd=REPO_ROOT)

    def dumps(self):
        return sorted(p.name for p in self.backups.glob("modelagem3d_*.dump"))

    def test_backup_writes_a_non_empty_dump_with_private_permissions(self):
        result = self.run_script("backup_producao.sh")
        self.assertEqual(result.returncode, 0, result.stderr)
        [name] = self.dumps()
        dump = self.backups / name
        self.assertEqual(dump.read_bytes(), b"PGDMP-falso")
        self.assertEqual(stat.S_IMODE(dump.stat().st_mode), 0o600)
        self.assertIn("-p m3d_teste", self.log.read_text())

    def test_backup_keeps_only_the_seven_newest(self):
        self.backups.mkdir()
        for day in range(1, 9):
            (self.backups / f"modelagem3d_202601{day:02d}_000000.dump").write_bytes(b"x")
        self.assertEqual(self.run_script("backup_producao.sh").returncode, 0)
        kept = self.dumps()
        self.assertEqual(len(kept), 7)
        self.assertNotIn("modelagem3d_20260101_000000.dump", kept)
        self.assertNotIn("modelagem3d_20260102_000000.dump", kept)

    def test_failed_backup_leaves_no_file_and_fails(self):
        result = self.run_script("backup_producao.sh", FAKE_FAIL="1")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(list(self.backups.glob("*")), [])

    def test_restore_refuses_without_explicit_confirmation(self):
        dump = self.tmp / "antigo.dump"
        dump.write_bytes(b"PGDMP-falso")
        result = self.run_script("restaurar_producao.sh", str(dump), stdin="sim\n")
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.log.exists() and "pg_restore" in self.log.read_text())

    def test_restore_rejects_missing_or_empty_file(self):
        empty = self.tmp / "vazio.dump"
        empty.write_bytes(b"")
        for path in (str(self.tmp / "nao_existe.dump"), str(empty)):
            result = self.run_script("restaurar_producao.sh", path, CONFIRMAR="RESTAURAR")
            self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.log.exists() and "pg_restore" in self.log.read_text())

    def test_restore_backs_up_current_data_first_then_restores(self):
        dump = self.tmp / "antigo.dump"
        dump.write_bytes(b"PGDMP-falso")
        result = self.run_script("restaurar_producao.sh", str(dump), CONFIRMAR="RESTAURAR")
        self.assertEqual(result.returncode, 0, result.stderr)
        calls = self.log.read_text().splitlines()
        first_dump = next(i for i, c in enumerate(calls) if "pg_dump" in c)
        restore = next(i for i, c in enumerate(calls) if "pg_restore" in c)
        self.assertLess(first_dump, restore)            # cópia de segurança antes de sobrescrever
        self.assertTrue(any("stop backend" in c for c in calls[:restore]))
        self.assertTrue(any("start backend" in c for c in calls[restore:]))
        # A cópia de segurança da restauração fica à parte da rotação diária.
        self.assertEqual(self.dumps(), [])
        self.assertEqual(len(list((self.backups / "antes_restauracao").glob("modelagem3d_*.dump"))), 1)

    def test_restoring_the_oldest_backup_does_not_delete_it(self):
        self.backups.mkdir()
        for day in range(1, 8):   # rotação cheia: 7 backups diários
            (self.backups / f"modelagem3d_202601{day:02d}_000000.dump").write_bytes(b"PGDMP-falso")
        oldest = self.backups / "modelagem3d_20260101_000000.dump"
        result = self.run_script("restaurar_producao.sh", str(oldest), CONFIRMAR="RESTAURAR")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(oldest.exists())
        self.assertEqual(len(self.dumps()), 7)


if __name__ == "__main__":
    unittest.main()
