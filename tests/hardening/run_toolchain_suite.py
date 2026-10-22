"""Execute the real upstream compile/link/ABI corpus with the hardened SDK."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import traceback

SOURCE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(SOURCE / 'tools/toolchain-tester'))
from testsuite import TestSuite
from testrunner import TestRunner


def sha(p):
    with Path(p).open('rb') as stream: return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sdk', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(exist_ok=False)
    corpus = SOURCE / 'tests/toolchain'
    inputs = [*sorted(p for p in corpus.rglob('*') if p.is_file()),
        *sorted((SOURCE / 'tools/toolchain-tester').glob('*.py')), Path(__file__),
        args.sdk / 'bin/cdt-cpp', args.sdk / 'bin/cdt-ld', args.sdk / 'lib/libeosio_dsm.a',
        args.sdk / 'include/eosiolib/core/eosio/varint.hpp', args.sdk / 'include/eosiolib/core/eosio/datastream.hpp']
    # Layout differs between distribution packages; resolve actual overlaid
    # headers by their explicit SDK include tree, never fall back to /usr.
    inputs = [p if p.exists() else args.sdk / 'include/eosio' / p.name for p in inputs]
    report = dict(status='running', started_utc=datetime.now(timezone.utc).isoformat(),
        scope='Real upstream compiler/link/ABI fixtures; not a full LLVM rebuild or node runtime/TPS',
        inputs_sha256={str(p): sha(p) for p in inputs}, rounds=[])
    try:
        for number in range(1, 4):
            temporary = args.output / f'round-{number}'
            temporary.mkdir()
            tempfile.tempdir = str(temporary)
            os.environ['TMPDIR'] = str(temporary)
            suites = [TestSuite(str(p), str(args.sdk / 'bin')) for p in sorted(corpus.iterdir()) if p.is_dir()]
            results = TestRunner(suites, 'all', 2).run_tests()
            cases = [dict(name=r.test.fullname, success=r.test.success, failure=str(r.failure) if r.failure else None,
                artifacts=getattr(r.test, 'output_directory', None)) for r in results]
            unique = [case['artifacts'] for case in cases]
            assert len(unique) == len(set(unique)) and all(unique), 'Test outputs are not isolated'
            failures = [case for case in cases if not case['success'] or case['failure']]
            report['rounds'].append(dict(number=number, cases=len(cases), failed=len(failures), results=cases))
            (args.output / 'report.json').write_text(json.dumps(report, indent=2))
            print(json.dumps(dict(round=number, cases=len(cases), failed=len(failures))), flush=True)
            if failures: raise RuntimeError('Real toolchain corpus failed; do not skip or weaken fixtures')
        assert all(sha(p) == expected for p, expected in report['inputs_sha256'].items())
        report['status'] = 'passed'
    except Exception as error: report.update(status='failed', error=str(error), traceback=traceback.format_exc())
    report['finished_utc'] = datetime.now(timezone.utc).isoformat()
    (args.output / 'report.json').write_text(json.dumps(report, indent=2))
    return 0 if report['status'] == 'passed' else 1


if __name__ == '__main__': raise SystemExit(main())
