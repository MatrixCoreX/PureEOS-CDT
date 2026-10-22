"""Fresh system-contract integration; keep wallet paths short, state on roomy disk."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import tempfile


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--node-source', type=Path, required=True)
    parser.add_argument('--programs', type=Path, required=True)
    parser.add_argument('--contracts', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve(); output.mkdir(parents=True, exist_ok=False)
    real_build = output / 'build'; (real_build / 'programs').mkdir(parents=True)
    short_parent = Path(tempfile.mkdtemp(prefix='pv1-sys-'))
    build = short_parent / 'b'; build.symlink_to(real_build)
    for name in ('nodeos', 'cleos', 'keosd', 'helios-util'):
        target = args.programs.resolve() / (name + '.elf')
        assert target.is_file()
        directory = real_build / 'programs' / name; directory.mkdir()
        (directory / name).symlink_to(target)
    def sha(path):
        with Path(path).open('rb') as stream: return hashlib.file_digest(stream, 'sha256').hexdigest()
    sources = [args.node_source.resolve() / 'tests/pureeos_single_choice_local_test.py', Path(__file__),
               args.programs.resolve() / 'nodeos.elf']
    sources += sorted(args.contracts.resolve().rglob('*.wasm'))
    sources += sorted(args.contracts.resolve().rglob('*.abi'))
    frozen = {str(p): sha(p) for p in sources}
    sys.path.insert(0, str(args.node_source.resolve() / 'tests'))
    from pureeos_single_choice_local_test import LocalTest
    test = LocalTest(build, args.contracts.resolve(), resource_split=True)
    code = test.execute()
    result = dict(status='passed' if code == 0 else 'failed', report=str((test.root / 'report.json').resolve()),
        short_alias=str(short_parent), inputs_sha256=frozen, finished_utc=datetime.now(timezone.utc).isoformat(),
        scope='New hardened SDK system/token/PowerUp fresh-chain functional/recovery; existing frozen node, not N4 new-node or TPS')
    if any(sha(p) != expected for p, expected in frozen.items()):
        result.update(status='failed', error='Frozen inputs changed'); code = 1
    (output / 'report.json').write_text(json.dumps(result, indent=2))
    return code


if __name__ == '__main__':
    raise SystemExit(main())
