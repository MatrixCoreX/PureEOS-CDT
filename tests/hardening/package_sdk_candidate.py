#!/usr/bin/env python3
"""Materialize a relocatable DEVELOPMENT SDK, not a stable release or LLVM rebuild."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import tarfile
import traceback
from sdk_archive import archive_sdk
from aic_identity import identity
from source_revision import source_revision
from sdk_notices import collect_notices, install_notices
from rebuild_runtime_library import rebuild_runtime
from check_runtime_parameters import check_parameters


def sha(path):
    with Path(path).open('rb') as stream: return hashlib.file_digest(stream, 'sha256').hexdigest()


def materialize(source, destination, allowed_roots, *, overlay=False):
    """Follow only explicit SDK roots; never preserve host-absolute links."""
    source, destination = Path(source), Path(destination)
    roots = tuple(Path(p).resolve(strict=True) for p in allowed_roots)
    if any(destination.resolve().is_relative_to(root) for root in roots):
        raise ValueError('Materialized output must be independent of SDK inputs')
    destination.mkdir(exist_ok=overlay)
    if destination.is_symlink(): raise ValueError('Output must not be a directory link')
    files = {}
    def walk(current, target, ancestors):
        resolved = current.resolve(strict=True)
        if not any(resolved.is_relative_to(root) for root in roots):
            raise ValueError('SDK link escapes explicit input roots: '+str(current))
        if resolved.is_dir():
            if resolved in ancestors: raise ValueError('Cyclic SDK directory link')
            target.mkdir(exist_ok=True)
            for item in sorted(resolved.iterdir()): walk(item, target/item.name, ancestors | {resolved})
        elif resolved.is_file():
            expected = sha(resolved)
            shutil.copyfile(resolved, target)
            target.chmod(stat.S_IMODE(resolved.stat().st_mode) & 0o777)
            if sha(target) != expected: raise RuntimeError('SDK changed during materialization')
            files[str(target.relative_to(destination))] = dict(source=str(resolved), sha256=expected)
        else: raise ValueError('SDK contains a special file')
    walk(source, destination, set())
    return files


def distribution_metadata(source, sdk, output, files):
    """Preserve historical package evidence outside the new SDK; retain licenses."""
    source, sdk, output = map(Path, (source, sdk, output))
    collect_notices(source)  # Reject missing/changed declarations before moving old metadata.
    historical = {}
    for name in ('PUREEOS_SDK_PROVENANCE.json', 'AIC_CDT_PROVENANCE.json'):
        old = sdk/name
        if old.exists():
            evidence = output/'historical-provenance'; evidence.mkdir(exist_ok=True)
            target = evidence/name
            if target.exists(): raise FileExistsError('Historical package evidence already exists')
            digest = sha(old)
            old.rename(target); files.pop(name, None)
            historical[name] = dict(sha256=digest, saved_as=str(target))
    for name in ('LICENSE', 'AIC_LICENSE.md', 'LICENSING.md', 'VERSION', 'UPSTREAM_BASELINE.json'):
        original = source/name; target = sdk/name
        shutil.copyfile(original, target)
        files[name] = dict(source=str(original), sha256=sha(original))
        if sha(target) != files[name]['sha256']: raise RuntimeError('Distribution metadata changed during copy')
    files.update(install_notices(source, sdk))
    return historical


def main():
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('sdk', 'base-sdk', 'wasm-evidence', 'node-source', 'output'):
        parser.add_argument('--'+name, type=Path, required=True)
    parser.add_argument('--frontend-evidence', type=Path, required=True)
    parser.add_argument('--runtime-parameter-tester', type=Path, required=True,
        help='Real node cdt_runtime_parameter_test executable; validates SDK get/set in both WASM engines')
    parser.add_argument('--source-metadata', type=Path,
        help='Complete externally stored frozen-source manifest, for source archive packaging without git')
    parser.add_argument('--original-sdk', type=Path, required=True,
        help='Unmodified upstream SDK for historical failure controls; separate from the complete base SDK')
    args = parser.parse_args()
    for name in ('sdk', 'base_sdk', 'original_sdk', 'wasm_evidence', 'node_source', 'frontend_evidence', 'runtime_parameter_tester'):
        setattr(args, name, getattr(args, name).resolve(strict=True))
    args.output = args.output.resolve()
    root = Path(__file__).resolve().parents[2]
    revision = source_revision(root, args.source_metadata)
    aic = identity(root); package_directory = aic['package_directory']
    if any(args.output == p or args.output.is_relative_to(p) for p in (args.sdk, args.base_sdk, args.original_sdk, root)):
        raise ValueError('Output must be independent of the SDK and source inputs')
    args.output.mkdir(exist_ok=False)
    report = dict(status='running', release_ready=False, scope=__doc__, jobs=[],
        source_commit=revision['source_commit'], source_revision=revision,
        started_utc=datetime.now(timezone.utc).isoformat(), package_script_sha256=sha(__file__))
    report['distribution_identity'] = aic
    def save():
        pending = args.output/'report.pending'; pending.write_text(json.dumps(report, indent=2))
        pending.replace(args.output/'report.json')
    def run(name, command, timeout=600):
        with (args.output/(name+'.log')).open('x') as stream:
            result = subprocess.run(list(map(str, command)), stdout=stream, stderr=subprocess.STDOUT, timeout=timeout)
        report['jobs'].append(dict(name=name, exit_code=result.returncode, command=list(map(str, command)))); save()
        if result.returncode: raise RuntimeError(name+' failed; preserve this candidate')
    try:
        save()
        previous = json.loads(args.wasm_evidence.read_text())
        assert previous['status'] == 'passed'
        frontend = json.loads(args.frontend_evidence.read_text())
        assert frontend['status'] == 'passed' and frontend['distribution_identity'] == aic
        for tool in ('cdt-cc','cdt-cpp','cdt-ld','cdt-abidiff','cdt-init'):
            assert sha(args.sdk/'bin'/tool) == frontend['tools_sha256']['bin/'+tool], 'Rebuilt AIC frontends required'
        for name in ('simple_malloc.cpp', 'simple_memory.hpp', 'core/eosio/varint.hpp', 'core/eosio/datastream.hpp'):
            suffix = '/libraries/eosiolib/'+name
            old = [d for p, d in previous['inputs_sha256'].items() if p.endswith(suffix)]
            assert len(old) == 1 and sha(root/('libraries/eosiolib/'+name)) == old[0], 'SDK production source changed'
        expected_runtime = [d for p, d in previous['artifacts_sha256'].items() if p.endswith('/sdk/lib/libeosio_dsm.a')]
        assert expected_runtime == [sha(args.sdk/'lib/libeosio_dsm.a')]
        # All current core headers, not merely the two modified headers.
        for p in (root/'libraries/eosiolib/core').rglob('*'):
            if p.is_file(): assert sha(p) == sha(args.sdk/'include/eosiolib/core'/p.relative_to(root/'libraries/eosiolib/core'))
        payload = args.output/'payload'; payload.mkdir()
        sdk = payload/package_directory
        # Retain the complete official SDK layout, scripts and third-party
        # licenses, not only the minimal headers/tools used by the test stage.
        files = materialize(args.base_sdk, sdk, (args.base_sdk,))
        files.update(materialize(args.sdk, sdk, (args.sdk, args.base_sdk), overlay=True))
        report['historical_package_provenance'] = distribution_metadata(root, sdk, args.output, files)
        report['baseline_runtime_parameters'] = check_parameters(sdk, root,
            args.runtime_parameter_tester, args.output/'baseline-runtime-parameters', baseline=True)
        runtime = rebuild_runtime(sdk, root, args.output/'core-runtime-rebuild')
        report['core_runtime_rebuild'] = runtime
        for name, row in runtime['libraries'].items():
            files['lib/'+name] = dict(source=row['source'], sha256=row['sha256'])
        for name, row in runtime['installed_headers'].items():
            files[name] = dict(source=row['source'], sha256=row['sha256'])
        report['rebuilt_runtime_parameters'] = check_parameters(sdk, root,
            args.runtime_parameter_tester, args.output/'rebuilt-runtime-parameters')
        for name, template in (('cdt-config.cmake', 'cdt-config.cmake'),
                ('CDTWasmToolchain.cmake', 'CDTWasmToolchain.cmake.in')):
            source = root/'modules'/template
            text = source.read_text().replace('@VERSION_FULL@', aic['version']).replace('@SYSROOT_DIR@', '')
            assert '@CDT_ROOT_DIR@' not in text and '@VERSION_FULL@' not in text
            path = sdk/'lib/cmake/cdt'/name; path.write_text(text)
            files['lib/cmake/cdt/'+name] = dict(source=str(source), source_sha256=sha(source), sha256=sha(path))
        report['native_tools_sha256'] = frontend['tools_sha256']
        assert all(sha(sdk/p) == d for p, d in report['native_tools_sha256'].items())
        report['archive_helper_sha256'] = sha(Path(__file__).with_name('sdk_archive.py'))
        report.update(sdk_files=len(files), sdk_manifest_sha256=None)
        assert files and not any(p.is_symlink() for p in sdk.rglob('*'))
        (args.output/'materialized-files.json').write_text(json.dumps(files, indent=2))
        report['sdk_manifest_sha256'] = sha(args.output/'materialized-files.json'); save()
        # Rename the entire prefix before the first invocation. Compiler/SDK
        # checks then run without reintroducing the staging prefix via PATH.
        relocated = payload/('relocated-'+package_directory); sdk.rename(relocated); sdk = relocated
        run('compiler-version', [sdk/'bin/cdt-cpp', '--version'])
        assert 'AIC CDT '+aic['version'] in (args.output/'compiler-version.log').read_text()
        negative = args.output/'original-cmake-negative.log'
        with negative.open('x') as stream:
            old = subprocess.run(['cmake', '-S', str(root/'tests/hardening/sdk_relocation_fixture'),
                '-B', str(args.output/'original-cmake-negative'),
                '-DCMAKE_TOOLCHAIN_FILE='+str(args.original_sdk/'lib/cmake/cdt/CDTWasmToolchain.cmake'),
                '-Dcdt_DIR='+str(args.original_sdk/'lib/cmake/cdt'), '-DPUREEOS_EXPECTED_SDK='+str(args.original_sdk),
                '-DPUREEOS_TEST_CONTRACT='+str(args.node_source/'tests/fixtures/cdt_modern_smoke.cpp')],
                stdout=stream, stderr=subprocess.STDOUT, timeout=120)
        assert old.returncode > 0 and any(s in negative.read_text() for s in
            ('/usr/bin/cdt-cpp', 'CDT resolved outside', 'CDTMacros')), 'Original failure not reproduced'
        report['original_cmake_negative_control'] = dict(expected_failure=True, exit_code=old.returncode,
            toolchain_sha256=sha(args.original_sdk/'lib/cmake/cdt/CDTWasmToolchain.cmake'),
            config_sha256=sha(args.original_sdk/'lib/cmake/cdt/cdt-config.cmake'))
        cmake_build = args.output/'cmake-smoke'
        run('relocated-cmake-configure', ['cmake', '-S', root/'tests/hardening/sdk_relocation_fixture',
            '-B', cmake_build, '-DCMAKE_TOOLCHAIN_FILE='+str(sdk/'lib/cmake/cdt/CDTWasmToolchain.cmake'),
            '-Dcdt_DIR='+str(sdk/'lib/cmake/cdt'), '-DPUREEOS_EXPECTED_SDK='+str(sdk),
            '-DPUREEOS_TEST_CONTRACT='+str(args.node_source/'tests/fixtures/cdt_modern_smoke.cpp')])
        run('relocated-cmake-build', ['cmake', '--build', cmake_build, '--parallel', '1'])
        assert (cmake_build/'cdtcompat.wasm').read_bytes()[:8] == b'\x00asm\x01\x00\x00\x00'
        assert sha(cmake_build/'cdtcompat.abi') == sha(args.wasm_evidence.parent/'cdtcompat/cdtcompat.abi')
        report['cmake_fixture_sha256'] = {p.name: sha(p) for p in
            (cmake_build/'cdtcompat.wasm', cmake_build/'cdtcompat.abi')}
        old_parent = args.output/'original-init-parent'; old_parent.mkdir()
        run('original-init-generate', [args.original_sdk/'bin/cdt-init', '--project=oldproject', '--path='+str(old_parent)])
        run('original-init-configure', ['cmake', '-S', old_parent/'oldproject', '-B', args.output/'original-init-build',
            '-DCMAKE_PREFIX_PATH='+str(sdk)])
        with (args.output/'original-init-build-negative.log').open('x') as stream:
            old_init = subprocess.run(['cmake', '--build', str(args.output/'original-init-build'), '--parallel', '1'],
                stdout=stream, stderr=subprocess.STDOUT, timeout=120)
        assert old_init.returncode > 0 and 'No cmake_minimum_required' in (args.output/'original-init-build-negative.log').read_text()
        report['original_init_negative_control'] = dict(expected_failure=True, exit_code=old_init.returncode,
            original_binary_sha256=sha(args.original_sdk/'bin/cdt-init'))
        run('relocated-toolchain-three-rounds', ['python3', root/'tests/hardening/run_toolchain_suite.py',
            '--sdk', sdk, '--output', args.output/'toolchain'], 1200)
        detail = json.loads((args.output/'toolchain/report.json').read_text())
        assert detail['status'] == 'passed' and len(detail['rounds']) == 3
        assert all(r['cases'] == 32 and r['failed'] == 0 for r in detail['rounds'])
        run('relocated-sdk-native-units', ['python3', root/'tests/hardening/run_sdk_native_units.py',
            '--sdk', sdk, '--output', args.output/'sdk-units'], 1200)
        detail = json.loads((args.output/'sdk-units/report.json').read_text())
        assert detail['status'] == 'passed' and len(detail['jobs']) == 76
        report['fixtures'] = {}
        for name, contract in (('cdtcompat', 'tests/fixtures/cdt_modern_smoke.cpp'),
                ('complexbench', 'unittests/test-contracts/complex_benchmark/complex_benchmark.cpp')):
            directory = args.output/name; directory.mkdir(); target = directory/(name+'.wasm')
            run('relocated-compile-'+name, [sdk/'bin/cdt-cpp', '-O3', '-abigen', '--sysroot='+str(sdk),
                '-I'+str(sdk/'include'), '-contract='+name, args.node_source/contract, '-o', target])
            for artifact in (target, target.with_suffix('.abi')):
                original = args.wasm_evidence.parent/name/artifact.name
                # A freshly rebuilt core runtime legitimately changes linked
                # WASM bytes. The public ABI must stay unchanged; execution is
                # checked separately, including parameter get/set round trips.
                if artifact.suffix == '.abi':
                    assert sha(artifact) == sha(original), 'Runtime rebuild changed fixture ABI: '+artifact.name
                report['fixtures'][name+'/'+artifact.name] = sha(artifact)
        assert all(sha(sdk/p) == v['sha256'] and sha(v['source']) == v.get('source_sha256', v['sha256']) for p, v in files.items())
        provenance = dict(scope=__doc__, stable_release=False, source_commit=report['source_commit'],
            distribution_identity=aic, upstream_compiler_unchanged=False, full_llvm_rebuild=False,
            frontend_build_report_sha256=sha(args.frontend_evidence),
            rebuilt_native_tools=['cdt-cc','cdt-cpp','cdt-ld','cdt-abidiff','cdt-init'],
            native_tools_sha256=report['native_tools_sha256'],
            rebuilt_core_runtime=runtime,
            hardened_runtime_sha256=expected_runtime[0], files_sha256={p: v['sha256'] for p, v in files.items()},
            acceptance='Relocated compile/link/ABI/native checks only; joint final node release still required')
        (sdk/'AIC_CDT_PROVENANCE.json').write_text(json.dumps(provenance, indent=2))
        archive = args.output/(package_directory+'-candidate.tar.gz')
        epoch = revision['source_epoch']
        archive_sdk(sdk, archive, epoch)
        replica = args.output/'reproducibility-check.tar.gz'; archive_sdk(sdk, replica, epoch)
        assert sha(archive) == sha(replica), 'Identical SDK produced different archive bytes'
        report['reproducible_archive'] = dict(epoch=epoch, identical_sha256=sha(archive), replica=str(replica))
        with tarfile.open(archive) as stream:
            for member in stream:
                assert not Path(member.name).is_absolute() and '..' not in Path(member.name).parts
                assert member.isdir() or member.isfile()
                assert member.uid == member.gid == 0 and member.mode in (0o644, 0o755)
            for p, v in files.items():
                member = stream.getmember(package_directory+'/'+p)
                assert member.isfile() and hashlib.file_digest(stream.extractfile(member), 'sha256').hexdigest() == v['sha256']
            installation = args.output/'installed'; installation.mkdir()
            stream.extractall(installation, filter='data')
        installed = installation/package_directory
        assert all(sha(installed/p) == v['sha256'] for p, v in files.items())
        assert all(sha(installed/p) == d for p, d in report['native_tools_sha256'].items())
        run('installed-compiler-version', [installed/'bin/cdt-cpp', '--version'])
        project_parent = args.output/'project with spaces'; project_parent.mkdir()
        run('installed-init-generate', [installed/'bin/cdt-init', '--project=smoketest', '--path='+str(project_parent)])
        generated = project_parent/'smoketest'
        before = {str(p.relative_to(generated)): sha(p) for p in generated.rglob('*') if p.is_file()}
        run('installed-init-configure', ['cmake', '-S', generated, '-B', args.output/'init-build',
            '-DCMAKE_PREFIX_PATH='+str(installed)])
        run('installed-init-build', ['cmake', '--build', args.output/'init-build', '--parallel', '1'])
        assert (args.output/'init-build/smoketest/smoketest.wasm').read_bytes()[:8] == b'\x00asm\x01\x00\x00\x00'
        refusal = subprocess.run([installed/'bin/cdt-init', '--project=smoketest', '--path='+str(project_parent)],
            capture_output=True, text=True, timeout=30)
        assert refusal.returncode > 0 and 'refusing to overwrite' in refusal.stderr
        assert all(sha(generated/p) == d for p, d in before.items()), 'Existing project overwritten'
        report['installed_init'] = dict(generated=True, built=True, existing_project_preserved=True,
            wasm_sha256=sha(args.output/'init-build/smoketest/smoketest.wasm'))
        assert all(sha(installed/p) == v['sha256'] and sha(sdk/p) == v['sha256'] for p, v in files.items())
        report.update(status='passed', package=dict(local=str(archive), bytes=archive.stat().st_size, sha256=sha(archive)),
            boundary='SDK packaging/relocation passed, NOT stable node/CDT joint release')
    except Exception as error:
        report.update(status='failed', error=str(error), traceback=traceback.format_exc())
    report['finished_utc'] = datetime.now(timezone.utc).isoformat(); save()
    return 0 if report['status'] == 'passed' else 1


if __name__ == '__main__': raise SystemExit(main())
