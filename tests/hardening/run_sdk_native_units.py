"""Compile/run actual CDT upstream native unit sources with the isolated SDK."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import traceback
from hardening_paths import require_cases, resolve_arguments


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sdk', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    resolve_arguments(args,'sdk','output')
    root = Path(__file__).resolve().parents[2]
    args.output.mkdir(exist_ok=False)
    cases = sorted((root / 'tests/unit').glob('*.cpp'))
    inputs = [Path(__file__), *cases, args.sdk / 'bin/cdt-cpp']
    def sha(path):
        with Path(path).open('rb') as stream: return hashlib.file_digest(stream, 'sha256').hexdigest()
    report = dict(status='running', started_utc=datetime.now(timezone.utc).isoformat(),
        inputs_sha256={str(p): sha(p) for p in inputs}, jobs=[],
        scope='Upstream x86 native SDK unit sources; not WASM/node execution or native allocator replacement')
    def run(name, command, timeout=120):
        with (args.output / (name + '.log')).open('x') as log:
            result = subprocess.run(list(map(str, command)), cwd=args.output, stdout=log, stderr=subprocess.STDOUT, timeout=timeout)
        report['jobs'].append(dict(name=name, exit_code=result.returncode, command=list(map(str, command))))
        (args.output / 'report.json').write_text(json.dumps(report, indent=2))
        print(name + ': exit=' + str(result.returncode), flush=True)
        if result.returncode: raise RuntimeError(name + ' failed; remaining units not claimed')
    try:
        require_cases(cases,'native SDK unit')
        for source in cases:
            program = args.output / (source.stem + '.elf')
            run('compile-' + source.stem, [args.sdk / 'bin/cdt-cpp', '-fnative', '-O2', source, '-o', program])
            for number in range(1, 4): run(source.stem + '-round-' + str(number), [program])
        assert all(sha(p) == expected for p, expected in report['inputs_sha256'].items())
        report['status'] = 'passed'
    except Exception as error: report.update(status='failed', error=str(error), traceback=traceback.format_exc())
    report['finished_utc'] = datetime.now(timezone.utc).isoformat()
    (args.output / 'report.json').write_text(json.dumps(report, indent=2))
    return 0 if report['status'] == 'passed' else 1


if __name__ == '__main__': raise SystemExit(main())
