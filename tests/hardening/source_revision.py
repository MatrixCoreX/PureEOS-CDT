"""Verify complete frozen source metadata when packaging outside a git checkout."""
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import subprocess


def sha(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def source_revision(root, metadata=None):
    root=Path(root).resolve(strict=True)
    if metadata is None:
        commit=subprocess.check_output(['git','-C',str(root),'rev-parse','HEAD'],text=True).strip()
        epoch=int(subprocess.check_output(['git','-C',str(root),'show','-s','--format=%ct',commit],text=True))
        return dict(source_commit=commit,source_epoch=epoch,metadata=None)
    metadata=Path(metadata).resolve(strict=True)
    if metadata.is_relative_to(root):raise ValueError('Frozen metadata must be outside the source tree')
    data=json.loads(metadata.read_text());commit=data['repository_base_commit'];epoch=data['repository_base_epoch']
    if not isinstance(commit,str) or not re.fullmatch('[0-9a-f]{40}',commit):raise ValueError('Invalid source base commit')
    if type(epoch) is not int or not 0<=epoch<=0xffffffff:raise ValueError('Invalid source base epoch')
    files=data['files_sha256']
    if not isinstance(files,dict) or not files:raise ValueError('Empty frozen source manifest')
    for name,digest in files.items():
        part=PurePosixPath(name)
        if part.is_absolute() or '..' in part.parts or str(part)!=name or not re.fullmatch('[0-9a-f]{64}',digest):
            raise ValueError('Invalid frozen source entry')
        path=root/name
        if not path.is_file() or path.is_symlink() or not path.resolve().is_relative_to(root) or sha(path)!=digest:
            raise ValueError('Frozen source bytes differ: '+name)
    actual={str(p.relative_to(root)) for p in root.rglob('*') if p.is_file()
        and not {'.git','__pycache__'}.intersection(p.relative_to(root).parts)}
    if actual!=set(files):raise ValueError('Frozen manifest must cover the complete source tree')
    return dict(source_commit=commit,source_epoch=epoch,metadata=str(metadata),metadata_sha256=sha(metadata),source_files=len(files))
