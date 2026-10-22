"""Build actual changed SDK components and retain every result in a new directory."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from hardening_paths import negative_baseline


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--baseline',type=Path,help='Explicit separate unmodified checkout for negative control')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    report = dict(status='running', scope='Native SDK serialization/allocator and toolchain tester; not WASM or full node',
                  source=str(root), started_utc=datetime.now(timezone.utc).isoformat(), jobs=[])
    sources = [*sorted(p for p in (root / 'tests/hardening').glob('*.*') if p.is_file()),
               root / 'libraries/eosiolib/simple_memory.hpp', root / 'libraries/eosiolib/simple_malloc.cpp',
               root / 'libraries/eosiolib/core/eosio/varint.hpp', root / 'libraries/eosiolib/core/eosio/datastream.hpp',
               root / 'tools/toolchain-tester/tests.py', root / 'tools/toolchain-tester/testsuite.py',
               root / 'tools/toolchain-tester/main.py', root / 'tools/toolchain-tester/testrunner.py']
    def hashes():
        return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}
    report['sources_sha256'] = hashes()
    env = {**os.environ, 'PYTHONDONTWRITEBYTECODE': '1',
           'ASAN_OPTIONS': 'detect_leaks=1:abort_on_error=1', 'UBSAN_OPTIONS': 'halt_on_error=1:print_stacktrace=1'}

    def run(name, command, allowed=(0,), timeout=60):
        log = output / (name + '.log')
        with log.open('x') as stream:
            result = subprocess.run(list(map(str, command)), cwd=root, env=env,
                                    stdout=stream, stderr=subprocess.STDOUT, timeout=timeout)
        job = dict(name=name, exit_code=result.returncode, status='passed' if result.returncode in allowed else 'failed',
                   log=str(log), command=list(map(str, command)))
        report['jobs'].append(job)
        print(f"{name}: {job['status']} (exit={result.returncode})", flush=True)
        (output / 'report.json').write_text(json.dumps(report, indent=2))
        return result.returncode in allowed

    try:
        if not run('toolchain-results', [sys.executable, '-m', 'unittest', 'discover', '-s',
                                       'tests/hardening', '-p', 'test_*.py', '-v']):
            raise RuntimeError('Toolchain result regression failed')
        compiler = subprocess.check_output(['g++', '--version'], text=True).splitlines()[0]
        report['compiler'] = compiler
        includes = ['-I' + str(root / 'libraries/eosiolib/core'),
                    '-I' + str(root / 'libraries/meta_refl/include')]
        # Original checkout stays untouched: this negative control must reject
        # the new expectations, not get silently relabeled as passing.
        baseline = negative_baseline(root,args.baseline)
        report['negative_control_baseline']=str(baseline) if baseline else None
        report['negative_control']='requested' if baseline else 'not-requested-not-a-negative-control-pass'
        baseline_program = output / 'serialization-original.elf'
        if baseline is not None:
            old_includes = ['-I' + str(baseline / 'libraries/eosiolib/core'),
                            '-I' + str(baseline / 'libraries/meta_refl/include')]
            if not run('compile-original-control', ['g++', '-std=c++17', '-O2', '-Wno-attributes',
                       *old_includes, root / 'tests/hardening/serialization_tests.cpp', '-o', baseline_program]):
                raise RuntimeError('Original source negative control did not compile')
            if not run('original-control-expected-failure', [baseline_program], allowed=(1,)):
                raise RuntimeError('Original serialization unexpectedly met hardened expectations')
            report['negative_control']='passed-original-rejected-hardened-expectations'
        for mode, flags in [('normal', ['-O2']), ('asan-ubsan', ['-O1', '-g', '-fno-omit-frame-pointer',
                                                                '-fsanitize=address,undefined', '-fno-sanitize-recover=all'])]:
            for case in ('serialization', 'allocator'):
                program = output / f'{case}-{mode}.elf'
                if not run(f'compile-{case}-{mode}', ['g++', '-std=c++17', '-Wno-attributes',
                            *flags, *includes, root / f'tests/hardening/{case}_tests.cpp', '-o', program], timeout=90):
                    raise RuntimeError('Compilation failed')
                for round_number in range(1, 4):
                    if not run(f'{case}-{mode}-round-{round_number}', [program]):
                        raise RuntimeError('Native regression/sanitizer failed; later rounds not run')
        if hashes() != report['sources_sha256']:
            raise RuntimeError('Source changed during native validation')
        report['status'] = 'passed'
    except Exception as error:
        report.update(status='failed', error=str(error))
    finally:
        report['finished_utc'] = datetime.now(timezone.utc).isoformat()
        (output / 'report.json').write_text(json.dumps(report, indent=2))
    return 0 if report['status'] == 'passed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
