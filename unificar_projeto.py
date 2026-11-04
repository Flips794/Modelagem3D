#!/usr/bin/env python3
"""Consolida Modelagem3D em Modelagem3D new, no computador do usuário.

Uso: salve este arquivo dentro de Modelagem3D new e execute:
    python3 unificar_projeto.py

Não substitui o código ativo, não carrega modelos joblib e não remove volumes.
Gera backup do PostgreSQL antes de mover a pasta antiga. Arquivos diferentes
são preservados; somente cópias idênticas podem ser eliminadas.
"""

from __future__ import annotations

import argparse
import errno
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
from datetime import datetime
import uuid


OPAQUE_DIRS = {".git", "node_modules", ".venv", "venv", "__pycache__", "dist", ".cache"}
DOCS = ("CORRECOES_EXISTENTES.patch", "RELATORIO_RECUPERACAO.md", "manifesto_recuperacao.json")
OLD_FIXES = {"backend/fix_bond_inventory_scope.py", "backend/fix_v48_scope_recursion.py"}
DATA_EXTENSIONS = {".csv", ".tsv", ".xlsx", ".xls", ".parquet", ".jsonl", ".sdf", ".mol", ".mol2", ".pdb", ".cif", ".xyz"}


class UnificationError(RuntimeError):
    pass


def historical_code(rel: Path) -> bool:
    if str(rel) in OLD_FIXES:
        return True
    return any(
        extension + marker in rel.name
        for extension in (".py", ".ts", ".tsx", ".js", ".jsx", ".css")
        for marker in (".backup", ".misplaced_backup")
    )


def fingerprint(path: Path) -> tuple[str, tuple[int, int, int, int, int]]:
    """Hash only a regular file and refuse a file changed during reading."""
    before = path.lstat()
    if not stat.S_ISREG(before.st_mode):
        raise UnificationError(f"Esperava um arquivo regular: {path}")
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(path, flags)
    digest = hashlib.sha256()
    with os.fdopen(fd, "rb") as handle:
        opened = os.fstat(handle.fileno())
        if (opened.st_dev, opened.st_ino) != (before.st_dev, before.st_ino):
            raise UnificationError(f"Arquivo mudou durante a conferência: {path}")
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    after = path.lstat()
    keys = lambda value: (value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns, value.st_ctime_ns)
    if keys(before) != keys(after):
        raise UnificationError(f"Arquivo mudou durante a conferência: {path}")
    return digest.hexdigest(), keys(after)


def regular(path: Path) -> bool:
    try:
        return stat.S_ISREG(path.lstat().st_mode)
    except FileNotFoundError:
        return False


def iter_entries(root: Path, opaque: bool = True):
    for directory, dirs, files in os.walk(root, followlinks=False, onerror=lambda error: (_ for _ in ()).throw(error)):
        directory = Path(directory)
        for name in sorted(dirs + files):
            path = directory / name
            yield path
        dirs[:] = sorted(name for name in dirs if not (directory / name).is_symlink() and (not opaque or name not in OPAQUE_DIRS))


class Consolidator:
    def __init__(self, project: Path):
        self.project = project.resolve()
        self.old = self.project.parent / "Modelagem3D"
        if self.old == self.project:
            raise UnificationError("Execute na pasta Modelagem3D new, que contém a versão funcionando.")
        for rel in ("backend/docker-compose.yml", "frontend/package.json", "iniciar_linux.sh"):
            if not regular(self.project / rel):
                raise UnificationError(f"A pasta principal não parece ser o projeto recuperado: falta {rel}")
        if self.old.is_symlink():
            raise UnificationError("A pasta antiga é uma referência simbólica. Ela foi preservada; confira seu caminho real antes de consolidar.")
        self.directory = self.safe("documentacao/unificacao")
        self.state_path = self.directory / "estado.json"
        self.state = None
        self.relocations = {
            rel: f"documentacao/recuperacao/{rel}" for rel in DOCS
        }

    def safe(self, rel: str | Path) -> Path:
        rel = Path(rel)
        if rel.is_absolute() or ".." in rel.parts:
            raise UnificationError(f"Destino inválido: {rel}")
        path = self.project
        for part in rel.parts:
            path = path / part
            if path.is_symlink():
                raise UnificationError(f"Destino contém uma referência simbólica: {path}")
        return path

    def save_state(self):
        self.directory.mkdir(parents=True, exist_ok=True)
        temp = self.directory / f".estado_{uuid.uuid4().hex}.tmp"
        with temp.open("x", encoding="utf-8") as handle:
            os.chmod(temp, 0o600)
            json.dump(self.state, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, self.state_path)

    def write_text_atomic(self, path: Path, text: str):
        self.safe(path.relative_to(self.project))
        path.parent.mkdir(parents=True, exist_ok=True)
        temp = path.with_name(path.name + ".tmp_" + uuid.uuid4().hex)
        try:
            with temp.open("x", encoding="utf-8") as handle:
                if regular(path):
                    os.chmod(temp, stat.S_IMODE(path.stat().st_mode))
                handle.write(text)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp, path)
        finally:
            if temp.exists():
                temp.unlink()

    def event(self, kind: str, source: Path, destination: Path | None = None, **extra):
        item = {"acao": kind, "origem": str(source.relative_to(self.project))}
        if destination is not None:
            item["destino"] = str(destination.relative_to(self.project))
        item.update(extra)
        if source.exists() or source.is_symlink():
            metadata = source.lstat()
            item["metadados_originais"] = {
                "modo": oct(stat.S_IMODE(metadata.st_mode)), "uid": metadata.st_uid,
                "gid": metadata.st_gid, "mtime_ns": metadata.st_mtime_ns,
            }
        self.state["operacoes"].append(item)
        self.save_state()

    def backup_database(self) -> Path:
        if not shutil.which("docker"):
            raise UnificationError("Docker não encontrado. Nenhuma pasta antiga foi movida.")
        folder = self.safe("backups")
        folder.mkdir(parents=True, exist_ok=True)
        name = f"antes_unificacao_{self.state['id']}.dump"
        destination = folder / name
        partial = folder / (name + ".partial")
        remote = "/tmp/" + name
        compose = ["docker", "compose", "-f", str(self.project / "backend/docker-compose.yml")]
        execute = compose + ["exec", "-T", "--interactive=false", "postgres"]
        print("Salvando o banco atual antes da consolidação...", flush=True)
        subprocess.run(execute + ["pg_dump", "-U", "modelagem3d", "-d", "modelagem3d_db", "-Fc", "--file=" + remote], check=True)
        subprocess.run(execute + ["sh", "-c", 'pg_restore --list "$1" >/dev/null', "sh", remote], check=True)
        subprocess.run(compose + ["cp", "postgres:" + remote, str(partial)], check=True)
        if not regular(partial):
            raise UnificationError("O backup não foi copiado. A pasta antiga foi preservada.")
        with partial.open("rb") as handle:
            if handle.read(5) != b"PGDMP":
                raise UnificationError("Backup não reconhecido. A pasta antiga foi preservada.")
        if destination.exists():
            raise UnificationError(f"Backup já existente: {destination}")
        partial.rename(destination)
        subprocess.run(execute + ["rm", "-f", "--", remote], check=False)
        self.state["backup_banco"] = str(destination.relative_to(self.project))
        self.state["backup_sha256"] = fingerprint(destination)[0]
        self.save_state()
        return destination

    def collect_links(self):
        links = []
        for path in iter_entries(self.old, opaque=False):
            if not path.is_symlink():
                continue
            raw = os.readlink(path)
            target = Path(os.path.abspath(path.parent / raw))
            internal = target.is_relative_to(self.old)
            links.append({
                "path": str(path.relative_to(self.old)), "original": raw,
                "target": str(target.relative_to(self.old)) if internal else str(target),
                "internal": internal,
            })
        self.state["links"] = links
        self.save_state()

    def protected(self, rel: Path) -> bool:
        for link in self.state.get("links", []):
            if link["internal"]:
                target = Path(link["target"])
                if rel == target or target in rel.parents:
                    return True
        return False

    def adjust_links(self, archive: Path):
        for link in self.state.get("links", []):
            relative = Path(link["path"])
            if relative.is_absolute() or ".." in relative.parts:
                raise UnificationError("Referência inválida no registro de consolidação.")
            if link["internal"] and (Path(link["target"]).is_absolute() or ".." in Path(link["target"]).parts):
                raise UnificationError("Destino interno inválido no registro de consolidação.")
            path = archive / relative
            raw = link["original"]
            if not path.is_symlink():
                continue
            desired = str(archive / link["target"]) if link["internal"] and Path(raw).is_absolute() else (link["target"] if not link["internal"] and not Path(raw).is_absolute() else raw)
            current = os.readlink(path)
            if current == desired:
                continue
            if current != raw:
                raise UnificationError(f"Referência alterada durante a consolidação: {path}")
            temp = path.with_name(path.name + ".unificacao_" + uuid.uuid4().hex)
            os.symlink(desired, temp)
            os.replace(temp, path)
            self.event("referencia_preservada", path, original=raw, atual=desired)

    def transfer(self, source: Path, rel_destination: str | Path, keep_source: bool = False) -> Path:
        """No overwrite. Verify bytes before unlinking any source file."""
        destination = self.safe(rel_destination)
        digest, source_stat = fingerprint(source)
        base = destination
        index = 0
        while destination.exists():
            if regular(destination) and destination.stat().st_size == source_stat[2]:
                existing, _ = fingerprint(destination)
                if existing == digest:
                    if not keep_source:
                        # Recheck both copies immediately before removing a duplicate.
                        if fingerprint(source)[0] != fingerprint(destination)[0]:
                            raise UnificationError(f"Arquivo mudou: {source}")
                        self.event("duplicata_identica", source, destination, sha256=digest)
                        source.unlink()
                    return destination
            index += 1
            suffix = f"__anterior_{digest[:12]}" + (f"_{index}" if index > 1 else "")
            destination = self.safe(base.relative_to(self.project).with_name(base.stem + suffix + base.suffix))
        destination.parent.mkdir(parents=True, exist_ok=True)
        temp = destination.with_name(destination.name + ".partial_" + uuid.uuid4().hex)
        try:
            try:
                os.link(source, temp, follow_symlinks=False)
            except OSError as error:
                if error.errno not in {errno.EXDEV, errno.EPERM, errno.EACCES, errno.ENOTSUP, errno.EMLINK}:
                    raise
                with source.open("rb") as incoming, temp.open("xb") as outgoing:
                    shutil.copyfileobj(incoming, outgoing, 1024 * 1024)
                    outgoing.flush()
                    os.fsync(outgoing.fileno())
                shutil.copystat(source, temp, follow_symlinks=False)
            if fingerprint(temp)[0] != digest or fingerprint(source)[0] != digest:
                raise UnificationError(f"Cópia não conferiu: {source}")
            # Hard-link publication refuses a concurrently created destination.
            try:
                os.link(temp, destination, follow_symlinks=False)
                temp.unlink()
            except OSError as error:
                if error.errno not in {errno.EXDEV, errno.EPERM, errno.EACCES, errno.ENOTSUP, errno.EMLINK}:
                    raise
                created = None
                try:
                    with temp.open("rb") as incoming, destination.open("xb") as outgoing:
                        info = os.fstat(outgoing.fileno())
                        created = (info.st_dev, info.st_ino)
                        shutil.copyfileobj(incoming, outgoing, 1024 * 1024)
                        outgoing.flush()
                        os.fsync(outgoing.fileno())
                    shutil.copystat(temp, destination, follow_symlinks=False)
                    if fingerprint(destination)[0] != digest:
                        raise UnificationError(f"Cópia final não conferiu: {destination}")
                except BaseException:
                    if created and regular(destination):
                        info = destination.lstat()
                        if (info.st_dev, info.st_ino) == created:
                            destination.unlink()
                    raise
                temp.unlink()
            if fingerprint(source)[0] != fingerprint(destination)[0]:
                raise UnificationError(f"Arquivo mudou: {source}")
            self.event("copia_preservada" if keep_source else "transferido", source, destination, sha256=digest)
            if not keep_source:
                source.unlink()
            return destination
        finally:
            if temp.exists():
                temp.unlink()

    def tidy_active(self):
        for filename in DOCS:
            path = self.safe(filename)
            if regular(path):
                self.transfer(path, self.relocations[filename])
        for top in ("backend", "frontend"):
            for path in list(iter_entries(self.project / top)):
                if not regular(path) or "trained_models" in path.relative_to(self.project).parts:
                    continue
                rel = path.relative_to(self.project)
                if historical_code(rel):
                    target = Path("arquivo/codigo_historico") / rel
                    self.relocations[str(rel)] = str(target)
                    self.transfer(path, target)

    @staticmethod
    def recovered_destination(rel: Path) -> Path | None:
        if rel.name == ".env" or rel.name.startswith(".env.") and rel.name != ".env.example":
            return Path("configuracoes/recuperadas") / rel
        if "trained_models" in rel.parts:
            index = rel.parts.index("trained_models")
            return Path("dados/recuperados/modelos_ia") / Path(*rel.parts[index + 1:])
        if rel.suffix.lower() in {".joblib", ".pkl", ".pickle", ".onnx", ".h5", ".pt", ".pth"}:
            return Path("dados/recuperados/modelos_ia/outros") / rel
        if "backups" in rel.parts or rel.suffix.lower() in {".dump", ".backup", ".sql"}:
            # SQL source and migration files stay in their original archival tree.
            if "alembic" in rel.parts or "training" in rel.parts or rel.name == "reference_data_seed.sql":
                return None
            return Path("backups/recuperados") / rel
        if rel.suffix.lower() in DATA_EXTENSIONS:
            return Path("dados/recuperados/arquivos") / rel
        if rel.name.startswith("codigo_") and rel.suffix.lower() == ".txt":
            return Path("documentacao/exportacoes") / rel
        if rel.suffix.lower() in {".pdf", ".docx", ".pptx"}:
            return Path("documentacao/recuperados") / rel
        return None

    def consolidate_archive(self, archive: Path):
        for path in list(iter_entries(archive)):
            if not regular(path):
                continue
            rel = path.relative_to(archive)
            # .git, virtual environments and dependency caches remain intact as archives.
            if any(part in OPAQUE_DIRS for part in rel.parts):
                continue
            mapped = self.relocations.get(str(rel), str(rel))
            if historical_code(rel):
                mapped = str(Path("arquivo/codigo_historico") / rel)
            try:
                counterpart = self.safe(mapped)
            except UnificationError:
                counterpart = None
            protected = self.protected(rel)
            if counterpart is not None and regular(counterpart) and path.stat().st_size == counterpart.stat().st_size:
                if fingerprint(path)[0] == fingerprint(counterpart)[0]:
                    self.transfer(path, counterpart.relative_to(self.project), keep_source=protected)
                    continue
            destination = self.recovered_destination(rel)
            if destination is not None:
                self.transfer(path, destination, keep_source=protected)

    def finish_docs(self):
        readme = self.safe("LEIA-ME.md")
        if regular(readme):
            original_text = readme.read_text(encoding="utf-8-sig")
            text = original_text
            for filename in DOCS:
                text = text.replace(f"`{filename}`", f"`documentacao/recuperacao/{filename}`")
                text = text.replace(f"({filename})", f"(documentacao/recuperacao/{filename})")
            if "## Organização após a unificação" not in text:
                text += "\n\n## Organização após a unificação\n\nA versão ativa está em `backend` e `frontend`. Backups ficam em `backups`; documentos em `documentacao`; configurações antigas em `configuracoes/recuperadas`; dados e modelos antigos em `dados/recuperados`. Versões diferentes de código e ambientes antigos ficam em `arquivo`. Consulte `documentacao/unificacao/RELATORIO.md`. Modelos e configurações recuperados não foram ativados automaticamente.\n"
            if text != original_text:
                self.transfer(readme, "arquivo/documentos_antes_unificacao/LEIA-ME.md", keep_source=True)
                self.write_text_atomic(readme, text)
        ignore = self.safe(".gitignore")
        if not ignore.exists() or regular(ignore):
            original_text = ignore.read_text(encoding="utf-8") if ignore.exists() else ""
            text = original_text
            for rule in ("/arquivo/", "/configuracoes/recuperadas/", "/dados/recuperados/", "/backups/"):
                if rule not in text.splitlines():
                    text += "\n" + rule
            text = text.rstrip() + "\n"
            if text != original_text:
                if regular(ignore):
                    self.transfer(ignore, "arquivo/documentos_antes_unificacao/.gitignore", keep_source=True)
                self.write_text_atomic(ignore, text)
        report = self.safe("documentacao/unificacao/RELATORIO.md")
        counts = {}
        for item in self.state["operacoes"]:
            counts[item["acao"]] = counts.get(item["acao"], 0) + 1
        lines = ["# Consolidação do Modelagem3D", "", f"Pasta principal: `{self.project}`", "", f"Backup do banco: `{self.state.get('backup_banco', 'não disponível')}`", "", "## Organização", "", "| Pasta | Conteúdo |", "| --- | --- |", "| backend e frontend | Versão atual em funcionamento |", "| backups | Cópias do banco e backups recuperados |", "| documentacao | Relatórios, exportações e documentação |", "| configuracoes/recuperadas | Configurações antigas preservadas, sem substituir as atuais |", "| dados/recuperados | Modelos e dados antigos, sem ativação automática |", "| arquivo | Código anterior diferente, metadados Git e ambientes antigos |", "", "## Operações verificadas", ""]
        lines.extend(f"- {kind}: {count}" for kind, count in sorted(counts.items()))
        lines += ["", "Somente arquivos com o mesmo SHA-256 foram deduplicados. Os detalhes de origem, destino e hashes estão em `estado.json`. Nenhum arquivo de configuração ou modelo recuperado foi carregado; os serviços e o volume Docker foram preservados. Referências a arquivos externos foram mantidas, sem copiar diretórios externos ao projeto.", ""]
        self.write_text_atomic(report, "\n".join(lines))

    def run(self):
        if self.state_path.exists():
            if not regular(self.state_path):
                raise UnificationError("O registro anterior não é um arquivo regular.")
            self.state = json.loads(self.state_path.read_text(encoding="utf-8"))
            if self.state.get("projeto") != str(self.project) or self.state.get("origem") != str(self.old):
                raise UnificationError("Já existe um registro de consolidação de outra origem. Ele foi preservado.")
            if self.state.get("status") == "concluido" and not self.old.exists():
                print("A consolidação já foi concluída. Nenhuma nova transferência foi necessária.")
                return
            if self.state.get("status") == "concluido":
                raise UnificationError("A pasta antiga reapareceu após uma consolidação concluída. Confira seu conteúdo antes de uma nova rodada.")
        else:
            if not self.old.is_dir():
                raise UnificationError(f"Não encontrei a pasta antiga: {self.old}")
            if self.project.is_relative_to(self.old.resolve()):
                raise UnificationError("A pasta atual não pode estar dentro da antiga.")
            run_id = datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + uuid.uuid4().hex[:8]
            archive_rel = "arquivo/versao_anterior"
            if self.safe(archive_rel).exists():
                archive_rel += "_" + run_id
            self.state = {"versao": 1, "id": run_id, "projeto": str(self.project), "origem": str(self.old), "arquivo": archive_rel, "status": "preparando", "operacoes": [], "links": []}
            self.save_state()
        archive = self.safe(self.state["arquivo"])
        if not self.state.get("backup_banco"):
            self.backup_database()
        elif not regular(self.safe(self.state["backup_banco"])):
            raise UnificationError("O backup registrado não está disponível. A transferência foi interrompida.")
        elif self.state.get("backup_sha256") and fingerprint(self.safe(self.state["backup_banco"]))[0] != self.state["backup_sha256"]:
            raise UnificationError("O backup registrado mudou. A transferência foi interrompida.")
        if self.old.exists():
            if archive.exists():
                raise UnificationError("A origem e o arquivo histórico já existem simultaneamente. Ambos foram preservados.")
            print("Catalogando referências e movendo a versão antiga para dentro da pasta principal...", flush=True)
            self.collect_links()
            archive.parent.mkdir(parents=True, exist_ok=True)
            self.old.rename(archive)
            self.state["status"] = "consolidando"
            self.save_state()
        elif not archive.is_dir():
            raise UnificationError("Não encontrei a origem nem o arquivo histórico registrado.")
        self.adjust_links(archive)
        print("Organizando documentação, backups e arquivos recuperados...", flush=True)
        self.tidy_active()
        self.consolidate_archive(archive)
        self.finish_docs()
        self.state["status"] = "concluido"
        self.save_state()
        print("\nConsolidação concluída.")
        print(f"Pasta única: {self.project}")
        print(f"Relatório: {self.directory / 'RELATORIO.md'}")
        print("Continue usando iniciar_linux.sh nesta mesma pasta. O banco e a configuração Docker foram mantidos.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--destino", type=Path, default=Path(__file__).resolve().parent, help="Pasta Modelagem3D new; por padrão, a pasta deste script")
    args = parser.parse_args()
    try:
        worker = Consolidator(args.destino)
        lock = worker.safe(".unificacao.lock")
        fd = os.open(lock, os.O_CREAT | os.O_RDWR | getattr(os, "O_NOFOLLOW", 0), 0o600)
        with os.fdopen(fd, "w") as handle:
            try:
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise UnificationError("Já existe uma consolidação em execução nesta pasta.")
            worker.run()
        return 0
    except (UnificationError, OSError, ValueError, subprocess.CalledProcessError) as error:
        print(f"\nA consolidação não terminou: {error}", file=sys.stderr)
        print("Os arquivos preservados podem estar na pasta antiga ou em arquivo/versao_anterior, dentro da principal. Corrija a causa e execute o mesmo comando para retomar. Nenhum volume Docker foi removido.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
