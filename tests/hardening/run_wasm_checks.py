"""Isolated modified-runtime build and actual serial/parallel fresh-chain checks."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--sdk', type=Path, required=True)
    parser.add_argument('--node-source', type=Path, required=True)
    parser.add_argument('--programs', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    sdk, node, programs = args.sdk.resolve(), args.node_source.resolve(), args.programs.resolve()
    output = args.output.resolve(); output.mkdir(parents=True, exist_ok=False)
    report = dict(status='running', scope='Modified SDK headers/runtime on frozen existing node; not new node wakeup integration, full compiler rebuild or TPS',
                  started_utc=datetime.now(timezone.utc).isoformat(), jobs=[])
    def sha(path):
        with Path(path).open('rb') as stream: return hashlib.file_digest(stream, 'sha256').hexdigest()
    inputs = [Path(__file__), root / 'libraries/eosiolib/simple_malloc.cpp', root / 'libraries/eosiolib/simple_memory.hpp',
              root / 'libraries/eosiolib/core/eosio/datastream.hpp', root / 'libraries/eosiolib/core/eosio/varint.hpp',
              node / 'tests/fixtures/cdt_modern_smoke.cpp', node / 'tests/ubuntu_cdt_runtime_test.py',
              node / 'unittests/test-contracts/complex_benchmark/complex_benchmark.cpp',
              sdk / 'bin/cdt-cpp', programs / 'nodeos.elf', programs / 'cleos.elf', programs / 'fixture.elf']
    report['inputs_sha256'] = {str(p): sha(p) for p in inputs}
    env = {**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'}
    def run(name, command, timeout=120):
        log = output / (name + '.log')
        with log.open('x') as stream:
            result = subprocess.run(list(map(str, command)), cwd=output, env=env, stdout=stream,
                                    stderr=subprocess.STDOUT, timeout=timeout)
        report['jobs'].append(dict(name=name, exit_code=result.returncode, log=str(log), command=list(map(str, command))))
        (output / 'report.json').write_text(json.dumps(report, indent=2))
        print(f'{name}: exit={result.returncode}', flush=True)
        if result.returncode: raise RuntimeError(name + ' failed; original log retained')
    try:
        assert shutil.disk_usage(output).free > 9 * 1024**3
        staged = output / 'sdk'
        staged.mkdir()
        for item in sdk.iterdir():
            if item.is_file(): shutil.copy2(item, staged / item.name)
        shutil.copytree(sdk / 'include', staged / 'include')
        shutil.copytree(sdk / 'lib', staged / 'lib', ignore=shutil.ignore_patterns('libeosio_dsm.a'))
        shutil.copytree(root / 'libraries/eosiolib/core', staged / 'include/eosiolib/core', dirs_exist_ok=True)
        (staged / 'bin').mkdir()
        for program in (sdk / 'bin').iterdir():
            target = staged / 'bin' / program.name
            if program.name in ('cdt-cpp', 'cdt-ld'):
                # Their whereami-based default library paths must resolve to
                # THIS SDK. A symlink would resolve back to the official SDK.
                shutil.copy2(program, target)
            else:
                target.symlink_to(program)
        compiler = staged / 'bin/cdt-cpp'
        obj = output / 'simple_malloc.o'
        run('compile-modified-runtime', [compiler, '-O3', '-c', root / 'libraries/eosiolib/simple_malloc.cpp', '-o', obj])
        archive = staged / 'lib/libeosio_dsm.a'
        run('archive-modified-runtime', [sdk / 'bin/llvm-ar', 'rcs', archive, obj])
        common = [compiler, '-O3', '-abigen', '--sysroot=' + str(staged),
                  '-I' + str(staged / 'include')]
        contract = output / 'cdtcompat'; contract.mkdir()
        complex_dir = output / 'complexbench'; complex_dir.mkdir()
        wasm = contract / 'cdtcompat.wasm'
        complex_wasm = complex_dir / 'complexbench.wasm'
        # Keep objects out of the source-only ABI generator. The relocated
        # driver/linker use the independently rebuilt runtime archive.
        for label, source, target in (
            ('cdtcompat', node / 'tests/fixtures/cdt_modern_smoke.cpp', wasm),
            ('complexbench', node / 'unittests/test-contracts/complex_benchmark/complex_benchmark.cpp', complex_wasm)):
            run('compile-' + label, [*common, '-contract=' + label, source, '-o', target])
        report['artifacts_sha256'] = {str(p): sha(p) for p in (obj, archive, wasm, wasm.with_suffix('.abi'), complex_wasm)}
        for round_number in range(1, 4):
            target = output / f'actual-round-{round_number}'
            run(f'actual-round-{round_number}', [sys.executable, node / 'tests/ubuntu_cdt_runtime_test.py',
                '--nodeos', programs / 'nodeos.elf', '--cleos', programs / 'cleos.elf',
                '--fixture-exporter', programs / 'fixture.elf', '--complex-wasm', complex_wasm,
                '--cdt-wasm', wasm, '--sdk-hardening', '--work-dir', target], timeout=900)
            actual = json.loads((target / 'report.json').read_text())
            assert actual['status'] == 'passed'
        assert {str(p): sha(p) for p in inputs} == report['inputs_sha256'], 'Inputs changed during checks'
        report['status'] = 'passed'
    except Exception as error:
        report.update(status='failed', error=str(error))
    finally:
        report['finished_utc'] = datetime.now(timezone.utc).isoformat()
        (output / 'report.json').write_text(json.dumps(report, indent=2))
    return 0 if report['status'] == 'passed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
