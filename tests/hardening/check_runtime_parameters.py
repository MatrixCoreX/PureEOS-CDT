"""Real-WASM SDK parameter checks on a supplied native controller test binary."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET


KNOWN_EMPTY_DESERIALIZER = '9a76c3952072032e5aef0b20b97b22312aec7e80b9c91092aefc91ecef21dfd3'


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def check_parameters(sdk, source, tester, output, *, baseline=False):
    sdk, source, tester = (Path(p).resolve(strict=True) for p in (sdk, source, tester))
    output = Path(output).absolute()
    output.mkdir(parents=True, exist_ok=False)
    contract = source/'tests/fixtures/runtime_parameters.cpp'
    inputs = {str(p): sha(p) for p in
              (sdk/'bin/cdt-cpp', sdk/'lib/libeosio.a', tester, contract)}
    with (output/'compile.log').open('x') as log:
        result = subprocess.run([str(sdk/'bin/cdt-cpp'), '-O3', '-abigen',
            '-contract=rtparams', '-o', str(output/'runtimeparams.wasm'), str(contract)],
            stdout=log, stderr=subprocess.STDOUT, timeout=180)
    if result.returncode:
        raise RuntimeError('Parameter probe compilation failed; preserve original log')
    negative = baseline and inputs[str(sdk/'lib/libeosio.a')] == KNOWN_EMPTY_DESERIALIZER
    rounds = []
    for number in range(1, (1 if baseline else 3) + 1):
        xml = output/('round-'+str(number)+'.xml')
        with (output/('round-'+str(number)+'.log')).open('x') as log:
            result = subprocess.run([str(tester), '--run_test=cdt_runtime_parameter_tests',
                '--report_level=detailed', '--report_format=XML', '--report_sink='+str(xml),
                '--color_output=no'], stdout=log, stderr=subprocess.STDOUT, timeout=180,
                env={**os.environ, 'PUREEOS_CDT_PARAMETER_PROBE_DIR': str(output)})
        root = ET.parse(xml).getroot().find('TestSuite')
        if root is None:
            raise RuntimeError('Missing actual native test report')
        counts = root.attrib
        if negative:
            log = (output/('round-'+str(number)+'.log')).read_text()
            valid = (result.returncode > 0 and counts.get('test_cases_failed') == '4' and
                counts.get('test_cases_aborted') == '0' and
                'SDK parameter deserialization differs' in log)
        else:
            valid = (result.returncode == 0 and counts.get('test_cases_passed') == '4' and
                counts.get('test_cases_failed') == '0' and counts.get('assertions_failed') == '0')
        rounds.append(dict(round=number, exit_code=result.returncode, counts=counts))
        if not valid:
            raise RuntimeError('Runtime parameter check failed; do not retry until a cause is fixed')
    if not all(sha(Path(name)) == digest for name, digest in inputs.items()):
        raise RuntimeError('Runtime parameter inputs changed during checks')
    report = dict(status='known-old-runtime-failure-reproduced' if negative else 'passed',
        scope='Real SDK get/set/all68wirebytes roundtrip and native full-config restoration; JIT/interpreter, default/custom genesis',
        baseline=baseline, inputs_sha256=inputs, rounds=rounds,
        artifacts_sha256={p.name: sha(p) for p in output.iterdir() if p.is_file()},
        inputs_unchanged=True)
    (output/'report.json').write_text(json.dumps(report, indent=2)+'\n')
    return report
