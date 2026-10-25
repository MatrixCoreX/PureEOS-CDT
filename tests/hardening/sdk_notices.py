"""Preserve fixed runtime dependency notices; this is not a license-clearance decision."""
import hashlib
import json
from pathlib import Path, PurePosixPath
import shutil


CATALOG = 'licenses/third_party/SOURCES.json'
PINNED = {
    'musl': ('libraries/libc/cdt-musl', 'AntelopeIO/cdt-musl',
             '9e6b206efcf203e875f2a659067a295f22cc83a9', 'COPYRIGHT',
             'f0ee3b78d87987bf951fe1ae136505fe2d0f4013', 'musl.COPYRIGHT'),
    'libcxx': ('libraries/libc++/cdt-libcxx', 'AntelopeIO/cdt-libcxx',
               'dd2d7b0ffea485690e75f4381432be243bf1fb3a', 'LICENSE.TXT',
               'e159d283443f92ac78b964d2bccebe8f95d5d445', 'libcxx.LICENSE.TXT'),
    'softfloat': ('libraries/native/softfloat', 'AntelopeIO/berkeley-softfloat-3',
                 '203b6df7dedc5bae1b2a7b1b23562335a6344578', 'COPYING.txt',
                 'b5690face082dc71bc7a8c612db03daad9605696', 'softfloat.COPYING.txt'),
}


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def regular(root, relative):
    part = PurePosixPath(relative)
    if part.is_absolute() or '..' in part.parts or str(part) != relative:
        raise ValueError('Noncanonical SDK notice path')
    path = root
    for name in part.parts:
        path = path / name
        if path.is_symlink():
            raise ValueError('SDK notice path contains a link')
    if not path.is_file():
        raise ValueError('Missing SDK dependency notice: ' + relative)
    return path


def collect_notices(source):
    source = Path(source)
    if source.is_symlink(): raise ValueError('SDK notice source must not be a link')
    catalog_path = regular(source, CATALOG)
    catalog = json.loads(catalog_path.read_text())
    if (catalog.get('schema') != 1 or
            catalog.get('project_source_commit') != '714543c5a001ac4a9f5b2baa4b55fb5064dadd62' or
            set(catalog.get('components', {})) != set(PINNED)):
        raise ValueError('Incomplete or unknown SDK dependency notice catalog')
    files = {'licenses/dependency-sources.json': dict(source=str(catalog_path), sha256=sha(catalog_path))}
    for component, expected in PINNED.items():
        module, repository, commit, upstream_path, blob, basename = expected
        row = catalog['components'][component]
        source_path = 'licenses/third_party/' + basename
        install_path = 'licenses/' + component + '.license'
        if any(row.get(key) != value for key, value in {
                'module_path': module, 'repository': repository, 'commit': commit,
                'path': upstream_path, 'git_blob_sha': blob,
                'source_path': source_path, 'install_path': install_path}.items()):
            raise ValueError('SDK dependency notice source or destination changed: ' + component)
        original = regular(source, source_path)
        data = original.read_bytes()
        object_id = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
        if object_id != blob or hashlib.sha256(data).hexdigest() != row.get('sha256'):
            raise ValueError('SDK dependency notice differs from fixed Git object: ' + component)
        files[install_path] = dict(source=str(original), sha256=row['sha256'])
    return files


def install_notices(source, sdk):
    files = collect_notices(source)
    sdk = Path(sdk)
    if sdk.is_symlink() or not sdk.is_dir(): raise ValueError('Expected independent SDK directory')
    # Validate every destination before copying. Preserve a conflicting notice
    # for review instead of silently replacing a different dependency version.
    for relative, record in files.items():
        target = sdk / relative
        if target.parent.is_symlink() or target.is_symlink():
            raise ValueError('SDK notice destination contains a link')
        if target.exists() and (not target.is_file() or sha(target) != record['sha256']):
            raise ValueError('Conflicting SDK dependency notice: ' + relative)
    for relative, record in files.items():
        target = sdk / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(record['source'], target)
        target.chmod(0o644)
        if sha(target) != record['sha256'] or sha(record['source']) != record['sha256']:
            raise RuntimeError('SDK dependency notice changed during copy')
    return files
