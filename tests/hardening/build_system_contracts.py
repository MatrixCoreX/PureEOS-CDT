"""One-shot full contract rebuild with the isolated hardened SDK, not a release."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
from contract_artifacts import split_contract_artifacts


def contract_source(path):
    requested = Path(path).resolve(strict=True)
    def actual(root):
        return ((root/'CMakeLists.txt').is_file()
            and (root/'eosio.system/src/eosio.system.cpp').is_file()
            and (root/'eosio.token/src/eosio.token.cpp').is_file())
    matches = [p for p in (requested, requested/'contracts') if actual(p)]
    if len(matches) != 1:
        raise ValueError('Expected exactly one reference-contract source (repository root or contracts/ directory)')
    return matches[0]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--sdk', type=Path, required=True)
    parser.add_argument('--contracts', type=Path, required=True, help='Repository root or its contracts/ source directory')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    sdk, source, output = args.sdk.resolve(), contract_source(args.contracts), args.output.resolve()
    if output.is_relative_to(source): raise ValueError('Keep generated contracts outside the source tree')
    output.mkdir(parents=True, exist_ok=False)
    root = Path(__file__).resolve().parents[2]
    report = dict(status='running', scope='All reference contracts rebuilt with modified SDK; runtime and first-release gates separate',
                  started_utc=datetime.now(timezone.utc).isoformat(), jobs=[],
                  requested_source=str(args.contracts.resolve()), actual_source=str(source))
    def sha(path):
        with Path(path).open('rb') as stream: return hashlib.file_digest(stream, 'sha256').hexdigest()
    sources = [p for p in source.rglob('*') if p.is_file() and p.suffix in ('.cpp', '.h', '.hpp', '.txt', '.cmake', '.in')]
    sources += [sdk / 'bin/cdt-cpp', sdk / 'bin/cdt-ld', sdk / 'lib/libeosio_dsm.a', Path(__file__),
                root / 'tests/hardening/isolated_toolchain.cmake', sdk / 'include/eosiolib/core/eosio/datastream.hpp',
                sdk / 'include/eosiolib/core/eosio/varint.hpp']
    def hashes(): return {str(p): sha(p) for p in sources}
    report['inputs_sha256'] = hashes()
    def run(name, command, timeout):
        log = output / (name + '.log')
        with log.open('x') as stream:
            result = subprocess.run(list(map(str, command)), env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'},
                stdout=stream, stderr=subprocess.STDOUT, timeout=timeout)
        report['jobs'].append(dict(name=name, exit_code=result.returncode, log=str(log), command=list(map(str, command))))
        (output / 'report.json').write_text(json.dumps(report, indent=2))
        print(f'{name}: exit={result.returncode}', flush=True)
        if result.returncode: raise RuntimeError(name + ' failed; do not overwrite this attempt')
    try:
        build = output / 'contracts'
        run('configure', ['cmake', '-S', source, '-B', build, '-DCMAKE_POLICY_VERSION_MINIMUM=3.5',
            '-DCMAKE_BUILD_TYPE=Release', '-DCMAKE_TOOLCHAIN_FILE=' + str(root / 'tests/hardening/isolated_toolchain.cmake'),
            '-DPUREEOS_CDT_ROOT=' + str(sdk), '-DCDT_ROOT=' + str(sdk), '-Dcdt_DIR=' + str(sdk / 'lib/cmake/cdt'),
            '-DPUREEOS_BP_PEERING=ON', '-DPUREEOS_BP_MAINTENANCE=ON',
            '-DPUREEOS_UPGRADE_GOVERNANCE=ON', '-DPUREEOS_SINGLE_CHOICE_VOTING=ON',
            '-DPUREEOS_RESOURCE_SPLIT=ON', '-DPUREEOS_SEQUENTIAL_ROTATION=ON', '-DSYSTEM_ENABLE_CDT_VERSION_CHECK=ON'], 120)
        run('build-all-contracts', ['cmake', '--build', build, '--parallel', '2'], 1800)
        artifacts = [p for p in build.rglob('*') if p.is_file() and p.suffix in ('.wasm', '.abi')]
        for required in ('eosio.system/eosio.system.wasm', 'eosio.token/eosio.token.wasm',
                         'eosio.bpay/eosio.bpay.wasm', 'eosio.system/.powerup/powup.results.wasm'):
            assert (build / required).is_file(), required
        inventory = {str(p.relative_to(build)): sha(p) for p in artifacts}
        report['artifacts_sha256'], report['build_probe_artifacts_sha256'] = split_contract_artifacts(inventory)
        assert hashes() == report['inputs_sha256'], 'Frozen inputs changed'
        report['status'] = 'passed'
    except Exception as error:
        report.update(status='failed', error=str(error))
    finally:
        report['finished_utc'] = datetime.now(timezone.utc).isoformat()
        (output / 'report.json').write_text(json.dumps(report, indent=2))
    return 0 if report['status'] == 'passed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
