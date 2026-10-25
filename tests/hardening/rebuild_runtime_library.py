"""Rebuild the SDK core runtime with the same headers/compiler shipped to users.

The inherited libeosio.a can have empty class deserializers even while contracts
compiled with current headers deserialize correctly. Materializing that archive
does not validate it. Rebuild both WASM and native core archives in a private staging SDK;
the real parameter get/set WASM regression is a separate required check.
"""
import hashlib
import os
from pathlib import Path
import shutil
import stat
import subprocess
import tempfile


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def rebuild_runtime(sdk, source, output):
    sdk, source = (Path(p).resolve(strict=True) for p in (sdk, source))
    output = Path(output).absolute()
    if output.is_relative_to(sdk) or output.is_relative_to(source):
        raise ValueError('Runtime build evidence must be outside SDK and source')
    if output.exists():
        raise FileExistsError('Preserve previous runtime build evidence')
    compiler, archiver = sdk/'bin/cdt-cpp', sdk/'bin/llvm-ar'
    variants = {
        'libeosio.a': (('eosiolib.cpp', 'crypto.cpp', 'base64.cpp'), ()),
        'libnative_eosio.a': (('eosiolib.cpp', 'crypto.cpp', 'malloc.cpp', 'base64.cpp'), ('-fnative',)),
    }
    for path in (compiler, archiver, *(sdk/'lib'/name for name in variants)):
        if path.is_symlink() or not path.is_file():
            raise ValueError('Expected materialized SDK runtime/tool')
    inputs = {str(p): sha(p) for p in (compiler, archiver)}
    headers = list((source/'libraries/eosiolib').rglob('*.hpp'))
    headers += list((source/'libraries/eosiolib').rglob('*.h'))
    headers += [source/'libraries/eosiolib'/n for n in ('eosiolib.cpp', 'crypto.cpp', 'malloc.cpp', 'base64.cpp')]
    inputs.update({str(p): sha(p) for p in headers})
    output.mkdir(parents=True)
    # This public C/C++ declaration fix must travel with the rebuilt archives.
    # The caller supplied a private staging SDK; never edit its original base.
    header_source = source/'libraries/eosiolib/contracts/eosio/system.hpp'
    header_name = 'include/eosiolib/contracts/eosio/system.hpp'
    header_target = sdk/header_name
    if header_target.is_symlink() or not header_target.is_file():
        raise ValueError('Expected materialized runtime system header')
    old_header = sha(header_target)
    shutil.copyfile(header_source, header_target)
    if sha(header_target) != sha(header_source):
        raise RuntimeError('Runtime header changed during staging')
    previous = {name: sha(sdk/'lib'/name) for name in variants}
    for name in variants:
        shutil.copyfile(sdk/'lib'/name, output/('previous-'+name))
    jobs = []

    def run(name, args):
        with (output/(name+'.log')).open('x') as log:
            result = subprocess.run(list(map(str, args)), stdout=log,
                                    stderr=subprocess.STDOUT, timeout=180)
        jobs.append(dict(name=name, command=list(map(str, args)), exit_code=result.returncode))
        if result.returncode:
            raise RuntimeError(name+' failed; original staged runtime retained')

    libraries = {}
    for library_name, (names, flags) in variants.items():
        directory = output/library_name.removesuffix('.a')
        directory.mkdir()
        objects = []
        for name in names:
            target = directory/(name+'.obj')
            run(library_name+'-compile-'+name, [compiler, *flags, '-O3', '-std=c++17', '-c',
                '-I'+str(source/'libraries/eosiolib'), '-o', target,
                source/'libraries/eosiolib'/name])
            objects.append(target)
        rebuilt = output/library_name
        run(library_name+'-archive-runtime', [archiver, 'rcsD', rebuilt, *objects])
        members = subprocess.check_output([str(archiver), 't', str(rebuilt)],
                                          text=True, timeout=30).splitlines()
        if members != [n+'.obj' for n in names]:
            raise RuntimeError('Unexpected core runtime archive members')
        libraries[library_name] = dict(old_sha256=previous[library_name],
            sha256=sha(rebuilt), source=str(rebuilt), members=members)
    if not all(sha(Path(name)) == digest for name, digest in inputs.items()):
        raise RuntimeError('Runtime source or compiler changed during build')
    if not all(sha(sdk/'lib'/name) == digest for name, digest in previous.items()):
        raise RuntimeError('Staged runtimes changed during build')
    for name, row in libraries.items():
        library = sdk/'lib'/name
        with tempfile.NamedTemporaryFile(prefix='.aic-runtime-', dir=library.parent,
                                         delete=False) as temporary:
            pending = Path(temporary.name)
        try:
            shutil.copyfile(row['source'], pending)
            pending.chmod(stat.S_IMODE(library.stat().st_mode))
            if sha(pending) != row['sha256']:
                raise RuntimeError('Runtime copy changed')
            os.replace(pending, library)
        finally:
            pending.unlink(missing_ok=True)
    return dict(status='rebuilt-current-core-runtimes', inputs_sha256=inputs, jobs=jobs,
        old_library_sha256=previous['libeosio.a'],
        new_library_sha256=libraries['libeosio.a']['sha256'], libraries=libraries,
        source=libraries['libeosio.a']['source'], original_input_SDK_unchanged=True,
        installed_headers={header_name: dict(source=str(header_source),
            old_sha256=old_header, sha256=sha(header_target))},
        acceptance='Compilation only; require real-WASM parameter get/set and native SDK regressions')
