"""Offline packaging safety; no compiler/node/SDK conformance is simulated."""
from pathlib import Path
import tempfile
import unittest

from package_sdk_candidate import materialize


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


if __name__ == '__main__': unittest.main()
