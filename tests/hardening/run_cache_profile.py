"""Profile comparisons in actual multi_index.hpp, not elapsed TPS or chain I/O."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import traceback


def sha(path):
    with Path(path).open('rb') as stream: return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sdk', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(exist_ok=False)
    source = Path(__file__).with_name('multi_index_cache_profile.cpp')
    header = args.sdk / 'include/eosiolib/contracts/eosio/multi_index.hpp'
    compiler = args.sdk / 'bin/cdt-cpp'
    report = dict(status='running', started_utc=datetime.now(timezone.utc).isoformat(), scope=__doc__,
        inputs_sha256={str(p): sha(p) for p in (Path(__file__), source, header, compiler)})
    try:
        program = args.output / 'cache-profile.elf'
        with (args.output / 'compile.log').open('x') as stream:
            subprocess.run([str(compiler), '-fnative', '-O2', str(source), '-o', str(program)],
                stdout=stream, stderr=subprocess.STDOUT, check=True, timeout=120, cwd=args.output)
        with (args.output / 'profile.jsonl').open('x') as stream:
            subprocess.run([program], stdout=stream, stderr=subprocess.STDOUT, check=True, timeout=60)
        rows = [json.loads(line) for line in (args.output / 'profile.jsonl').read_text().splitlines() if line.startswith('{')]
        assert len(rows) == 12
        for number in (1, 2, 3): assert [row['rows'] for row in rows if row['round'] == number] == [1, 8, 64, 1024]
        assert all(row['find_comparisons'] == row['require_find_comparisons'] == row['rows'] * (row['rows'] + 1) // 2
                   and row['host_reads'] == 0 for row in rows)
        assert all(sha(p) == expected for p, expected in report['inputs_sha256'].items())
        report.update(status='passed', measurements=rows, program_sha256=sha(program),
            performance_or_tps_claim=False, multi_index_source_modified=False)
    except Exception as error: report.update(status='failed', error=str(error), traceback=traceback.format_exc())
    report['finished_utc'] = datetime.now(timezone.utc).isoformat()
    (args.output / 'report.json').write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))
    return 0 if report['status'] == 'passed' else 1


if __name__ == '__main__': raise SystemExit(main())
