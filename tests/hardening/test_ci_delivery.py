"""CI configuration scope and preserved workflow provenance, not an SDK build result."""
import hashlib
import json
from pathlib import Path
import unittest

import yaml
from workflow_inventory import require_workflows


ROOT = Path(__file__).resolve().parents[2]


class SourceCIDeliveryTests(unittest.TestCase):
    def test_source_checks_do_not_depend_on_old_organization_or_node_packages(self):
        active = ROOT / '.github/workflows'
        current = require_workflows(ROOT, {'build.yaml'})
        text = current['build.yaml']['content'].decode()
        workflow = yaml.load(text, Loader=yaml.BaseLoader)
        self.assertEqual(workflow['permissions'], {'contents': 'read'})
        for obsolete in ('PureEOSIO/', 'enf-x86-', 'secrets.', 'contents: write', 'release:', 'gh release'):
            self.assertNotIn(obsolete, text)
        job = workflow['jobs']['sdk-source']
        self.assertEqual(job['runs-on'], 'ubuntu-24.04')
        self.assertEqual(job['strategy']['matrix']['ubuntu'], ['26.04', '26.10'])
        self.assertEqual(job['container'], 'ubuntu:${{ matrix.ubuntu }}')
        for step in job['steps']:
            if 'uses' in step:
                self.assertRegex(step['uses'], r'^actions/(checkout|upload-artifact)@[a-f0-9]{40}$')
                if step['uses'].startswith('actions/checkout@'):
                    self.assertEqual(step['with']['submodules'], 'false')
                    self.assertEqual(step['with']['persist-credentials'], 'false')

    def test_declared_entry_runs_actual_sdk_native_regressions(self):
        text = (ROOT / '.github/workflows/build.yaml').read_text()
        self.assertIn('tests/hardening/run_native_tests.py --output ci-results/sdk-native', text)
        runner = (ROOT / 'tests/hardening/run_native_tests.py').read_text()
        self.assertIn("'-fsanitize=address,undefined'", runner)
        self.assertIn('range(1, 4)', runner)
        self.assertIn("'serialization', 'allocator'", runner)

    def test_all_prior_configurations_are_preserved_byte_for_byte(self):
        archive = ROOT / 'docs/ci-reference-20261024'
        manifest = json.loads((archive / 'manifest.json').read_text())
        self.assertEqual(set(manifest['files']), {'build.yaml', 'release.yaml', 'label_new_issues.yaml'})
        for name, record in manifest['files'].items():
            self.assertEqual(record['archive'], name + '.txt')
            self.assertEqual(hashlib.sha256((archive / record['archive']).read_bytes()).hexdigest(), record['sha256'])


if __name__ == '__main__':
    unittest.main()
