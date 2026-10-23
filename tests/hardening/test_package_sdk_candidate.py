"""Offline packaging safety; no compiler/node/SDK conformance is simulated."""
from pathlib import Path
import shutil
import tempfile
import unittest

from package_sdk_candidate import distribution_metadata, materialize, sha


def notice_fixture(source):
    original = Path(__file__).resolve().parents[2]/'licenses/third_party'
    shutil.copytree(original, source/'licenses/third_party')


class SDKPackagingControls(unittest.TestCase):
    def test_absolute_and_relative_tools_are_materialized(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); base = root/'base'; stage = root/'stage'; base.mkdir(); stage.mkdir()
            program = base/'compiler'; program.write_bytes(b'fixture'); program.chmod(0o755)
            (stage/'cpp').symlink_to(program)
            (stage/'cc').symlink_to('cpp')
            destination = root/'out'; files = materialize(stage, destination, (stage, base))
            self.assertEqual(set(files), {'cpp', 'cc'})
            for name in files:
                self.assertFalse((destination/name).is_symlink())
                self.assertEqual((destination/name).read_bytes(), b'fixture')
                self.assertEqual((destination/name).stat().st_mode & 0o777, 0o755)

    def test_external_link_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); source = root/'source'; source.mkdir()
            secret = root/'not-sdk'; secret.write_text('not included')
            (source/'link').symlink_to(secret)
            with self.assertRaisesRegex(ValueError, 'escapes'): materialize(source, root/'out', (source,))

    def test_input_nested_output_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp)
            with self.assertRaisesRegex(ValueError, 'independent'): materialize(source, source/'out', (source,))

    def test_explicit_overlay_preserves_licenses_and_replaces_only_own_sdk(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); base = root/'base'; stage = root/'stage'; base.mkdir(); stage.mkdir()
            (base/'LICENSE').write_text('retained')
            (base/'runtime').write_text('original'); (stage/'runtime').write_text('hardened')
            out = root/'out'; files = materialize(base, out, (base,))
            files.update(materialize(stage, out, (stage,), overlay=True))
            self.assertEqual(set(files), {'runtime', 'LICENSE'})
            self.assertEqual((out/'runtime').read_text(), 'hardened')
            self.assertEqual((out/'LICENSE').read_text(), 'retained')

    def test_directory_link_cycle_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); source = root/'source'; source.mkdir(); (source/'loop').symlink_to(source)
            with self.assertRaisesRegex(ValueError, 'Cyclic'): materialize(source, root/'out', (source,))

    def test_existing_output_never_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); source = root/'source'; source.mkdir(); out = root/'out'; out.mkdir()
            (out/'keep').write_text('unchanged')
            with self.assertRaises(FileExistsError): materialize(source, out, (source,))
            self.assertEqual((out/'keep').read_text(), 'unchanged')


    def test_new_identity_preserves_history_outside_sdk_and_retains_component_licenses(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); base = root/'base'; source = root/'source'; output = root/'output'
            base.mkdir(); source.mkdir(); output.mkdir()
            notice_fixture(source)
            for name in ('LICENSE', 'AIC_LICENSE.md', 'LICENSING.md', 'VERSION', 'UPSTREAM_BASELINE.json'):
                (source/name).write_text('source '+name)
            (base/'PUREEOS_SDK_PROVENANCE.json').write_text('old identity')
            (base/'AIC_CDT_PROVENANCE.json').write_text('older AIC candidate')
            (base/'licenses').mkdir(); (base/'licenses/llvm.license').write_text('retained')
            sdk = output/'sdk'; files = materialize(base, sdk, (base,))
            baseline_hash = sha(base/'PUREEOS_SDK_PROVENANCE.json')
            history = distribution_metadata(source, sdk, output, files)
            self.assertEqual(set(history), {'PUREEOS_SDK_PROVENANCE.json', 'AIC_CDT_PROVENANCE.json'})
            for name, item in history.items():
                self.assertFalse((sdk/name).exists()); self.assertNotIn(name, files)
                self.assertEqual(sha(Path(item['saved_as'])), item['sha256'])
            self.assertEqual(sha(base/'PUREEOS_SDK_PROVENANCE.json'), baseline_hash)
            self.assertEqual((sdk/'licenses/llvm.license').read_text(), 'retained')
            for name in ('LICENSE', 'AIC_LICENSE.md', 'LICENSING.md', 'VERSION', 'UPSTREAM_BASELINE.json'):
                self.assertEqual(sha(sdk/name), sha(source/name))
                self.assertEqual(files[name]['sha256'], sha(source/name))

    def test_historical_provenance_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); sdk = root/'sdk'; output = root/'output'; source = root/'source'
            sdk.mkdir(); output.mkdir(); source.mkdir(); (output/'historical-provenance').mkdir()
            notice_fixture(source)
            name = 'PUREEOS_SDK_PROVENANCE.json'
            (sdk/name).write_text('candidate'); (output/'historical-provenance'/name).write_text('keep')
            with self.assertRaises(FileExistsError): distribution_metadata(source, sdk, output, {name:{}})
            self.assertEqual((sdk/name).read_text(), 'candidate')
            self.assertEqual((output/'historical-provenance'/name).read_text(), 'keep')


if __name__ == '__main__': unittest.main()
