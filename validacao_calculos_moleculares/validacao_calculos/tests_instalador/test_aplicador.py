from pathlib import Path
import base64
import hashlib
import importlib.util
import json
import shutil
import stat
import zlib

import pytest

HERE=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('installer_calculos',HERE/'corrigir_calculos_moleculares.py')
installer=importlib.util.module_from_spec(spec);spec.loader.exec_module(installer)

@pytest.fixture
def project(tmp_path):
    target=tmp_path/'project with spaces'
    shutil.copytree(HERE/'antes_correcao_calculos',target,ignore=shutil.ignore_patterns('node_modules','dist','__pycache__'))
    return target

def hashes(root):
    return {str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob('*') if p.is_file()}

def test_dry_run_does_not_write(project):
    before=hashes(project);installer.apply_update(project,installer.load_payload(),True)
    assert hashes(project)==before and not (project/'backups/correcao_calculos_moleculares').exists()

def test_apply_exact_contents_and_backup_existing_files(project):
    package=installer.load_payload();before=hashes(project)
    backup=installer.apply_update(project,package)
    for item in package['files']:
        assert installer.sha256((project/item['path']).read_bytes())==item['new_sha256']
        if item['old_sha256'] is not None:
            assert installer.sha256((backup/item['path']).read_bytes())==before[item['path']]
    changed={item['path'] for item in package['files']}
    for path,digest in before.items():
        if path not in changed: assert installer.sha256((project/path).read_bytes())==digest

def test_idempotency_does_not_create_additional_backups(project):
    package=installer.load_payload();installer.apply_update(project,package);before=hashes(project)
    assert installer.apply_update(project,package) is None
    assert hashes(project)==before

def test_source_conflict_stops_before_all_mutations(project):
    package=installer.load_payload();item=next(i for i in package['files'] if i['old_sha256'])
    path=project/item['path'];path.write_text(path.read_text()+'\n# edited by user\n')
    before=hashes(project)
    with pytest.raises(ValueError,match='Nenhum arquivo'):installer.apply_update(project,package)
    assert hashes(project)==before

def test_new_path_collision_is_not_overwritten(project):
    package=installer.load_payload();item=next(i for i in package['files'] if i['old_sha256'] is None)
    path=project/item['path'];path.parent.mkdir(parents=True,exist_ok=True);path.write_text('user content')
    before=hashes(project)
    with pytest.raises(ValueError):installer.apply_update(project,package)
    assert hashes(project)==before

def test_crlf_and_outer_blank_lines_preserve_exact_backup(project):
    package=installer.load_payload();item=next(i for i in package['files'] if i['old_sha256'])
    path=project/item['path'];original=b'\r\n'+path.read_bytes().replace(b'\n',b'\r\n')+b'\r\n'
    path.write_bytes(original);backup=installer.apply_update(project,package)
    assert (backup/item['path']).read_bytes()==original
    assert path.read_bytes()==item['bytes']

def test_whitespace_inside_code_is_not_normalized_away(project):
    package=installer.load_payload();item=next(i for i in package['files'] if i['old_sha256'] and i['path'].endswith('.py'))
    path=project/item['path'];path.write_bytes(path.read_bytes().replace(b'    ',b'   ',1))
    before=hashes(project)
    with pytest.raises(ValueError):installer.apply_update(project,package)
    assert hashes(project)==before

def test_source_symlink_is_rejected(project,tmp_path):
    package=installer.load_payload();item=next(i for i in package['files'] if i['old_sha256'])
    path=project/item['path'];outside=tmp_path/'outside';outside.write_bytes(path.read_bytes());path.unlink();path.symlink_to(outside)
    original=outside.read_bytes()
    with pytest.raises(ValueError,match='simbólico'):installer.apply_update(project,package)
    assert outside.read_bytes()==original

def test_backup_symlink_is_rejected(project,tmp_path):
    path=project/'backups/correcao_calculos_moleculares';path.parent.mkdir(exist_ok=True)
    outside=tmp_path/'outside';outside.mkdir();path.symlink_to(outside,target_is_directory=True)
    with pytest.raises(ValueError,match='simbólico'):installer.apply_update(project,installer.load_payload())
    assert not list(outside.iterdir())

def test_partial_write_failure_rolls_back_all_changes(project,monkeypatch):
    package=installer.load_payload();before=hashes(project);original=installer.write_atomic
    failing=project/package['files'][2]['path']
    def fail_one(path,data,mode=0o644):
        if path==failing:raise OSError('simulated write failure')
        return original(path,data,mode)
    monkeypatch.setattr(installer,'write_atomic',fail_one)
    with pytest.raises(RuntimeError,match='restaurados'):installer.apply_update(project,package)
    after={p:h for p,h in hashes(project).items() if not p.startswith('backups/correcao_calculos_moleculares/')}
    assert after==before

def test_mode_is_preserved(project):
    package=installer.load_payload();item=next(i for i in package['files'] if i['old_sha256'])
    path=project/item['path'];path.chmod(0o640);installer.apply_update(project,package)
    assert stat.S_IMODE(path.stat().st_mode)==0o640

def test_corrupt_embedded_payload_fails_integrity(monkeypatch):
    monkeypatch.setattr(installer,'PAYLOAD_SHA256','0'*64)
    with pytest.raises(ValueError,match='integridade'):installer.load_payload()

def test_payload_cannot_escape_project(monkeypatch):
    package={'files':[{'path':'../escape.py'}]};raw=json.dumps(package).encode()
    monkeypatch.setattr(installer,'PAYLOAD',base64.b85encode(zlib.compress(raw)).decode())
    monkeypatch.setattr(installer,'PAYLOAD_SHA256',installer.sha256(raw))
    with pytest.raises(ValueError,match='Caminho'):installer.load_payload()

def test_wrong_project_root_is_rejected(tmp_path):
    with pytest.raises(ValueError,match='backend e frontend'):installer.apply_update(tmp_path,installer.load_payload())
