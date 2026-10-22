"""Deterministic SDK tar: public install permissions, no host owners or links."""
import gzip
from pathlib import Path
import tarfile


def archive_sdk(sdk, archive, epoch):
    sdk, archive = Path(sdk).resolve(strict=True), Path(archive).resolve()
    if archive.is_relative_to(sdk): raise ValueError('Archive must not be inside the SDK')
    if not isinstance(epoch, int) or not 0 <= epoch <= 0xffffffff: raise ValueError('Invalid archive epoch')
    def public(info):
        if not (info.isfile() or info.isdir()): raise ValueError('SDK archive cannot contain links or special files')
        info.uid = info.gid = 0; info.uname = info.gname = 'root'; info.mtime = epoch
        info.mode = 0o755 if info.isdir() or info.mode & 0o111 else 0o644
        info.pax_headers = {}
        return info
    with archive.open('xb') as raw, gzip.GzipFile(filename='', mode='wb', fileobj=raw,
            compresslevel=1, mtime=epoch) as compressed, tarfile.open(fileobj=compressed,
            mode='w', format=tarfile.PAX_FORMAT) as stream:
        stream.add(sdk, arcname='pureeos-cdt-candidate', recursive=False, filter=public)
        for path in sorted(sdk.rglob('*')):
            if path.is_symlink(): raise ValueError('Materialize SDK links before archiving')
            stream.add(path, arcname='pureeos-cdt-candidate/'+str(path.relative_to(sdk)), recursive=False, filter=public)
