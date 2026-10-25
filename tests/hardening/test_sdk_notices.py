"""Check actual pinned dependency declarations and reject incomplete SDK delivery."""
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from sdk_notices import CATALOG, collect_notices, install_notices


class SDKNoticeControls(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root/'source'
        self.sdk = self.root/'sdk'
        self.sdk.mkdir()
        shutil.copytree(Path(__file__).resolve().parents[2]/'licenses/third_party',
                        self.source/'licenses/third_party')

    def change_catalog(self, mutate):
        path = self.source/CATALOG
        catalog = json.loads(path.read_text())
        mutate(catalog)
        path.write_text(json.dumps(catalog))

    def test_complete_pinned_notices_install_without_changing_bytes(self):
        files = collect_notices(self.source)
        self.assertEqual(set(files), {'licenses/dependency-sources.json',
                         'licenses/musl.license', 'licenses/libcxx.license',
                         'licenses/softfloat.license'})
        self.assertEqual(install_notices(self.source, self.sdk), files)
        self.assertEqual(install_notices(self.source, self.sdk), files)
        for relative, row in files.items():
            self.assertEqual((self.sdk/relative).read_bytes(), Path(row['source']).read_bytes())

    def test_missing_notice_rejected_before_any_copy(self):
        (self.source/'licenses/third_party/softfloat.COPYING.txt').unlink()
        with self.assertRaisesRegex(ValueError, 'Missing'):
            install_notices(self.source, self.sdk)
        self.assertEqual(list(self.sdk.iterdir()), [])

    def test_changed_notice_and_matching_catalog_digest_still_rejected(self):
        path = self.source/'licenses/third_party/musl.COPYRIGHT'
        path.write_bytes(path.read_bytes()+b'changed')
        self.change_catalog(lambda d: d['components']['musl'].update(
            sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
        with self.assertRaisesRegex(ValueError, 'fixed Git object'):
            collect_notices(self.source)

    def test_wrong_fixed_commit_rejected(self):
        self.change_catalog(lambda d: d['components']['musl'].update(commit='0'*40))
        with self.assertRaisesRegex(ValueError, 'changed'):
            collect_notices(self.source)

    def test_unknown_or_missing_component_rejected(self):
        self.change_catalog(lambda d: d['components'].pop('libcxx'))
        with self.assertRaisesRegex(ValueError, 'Incomplete'):
            collect_notices(self.source)

    def test_destination_escape_rejected(self):
        self.change_catalog(lambda d: d['components']['musl'].update(install_path='../outside'))
        with self.assertRaisesRegex(ValueError, 'changed'):
            install_notices(self.source, self.sdk)
        self.assertFalse((self.root/'outside').exists())

    def test_source_symlink_rejected(self):
        path = self.source/'licenses/third_party/musl.COPYRIGHT'
        external = self.root/'external'
        path.rename(external)
        path.symlink_to(external)
        with self.assertRaisesRegex(ValueError, 'link'):
            collect_notices(self.source)

    def test_destination_directory_symlink_rejected_without_external_write(self):
        external = self.root/'external'
        external.mkdir()
        (self.sdk/'licenses').symlink_to(external, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, 'link'):
            install_notices(self.source, self.sdk)
        self.assertEqual(list(external.iterdir()), [])

    def test_conflicting_notice_preserved_and_no_partial_copy(self):
        (self.sdk/'licenses').mkdir()
        conflict = self.sdk/'licenses/softfloat.license'
        conflict.write_bytes(b'original conflicting declaration')
        with self.assertRaisesRegex(ValueError, 'Conflicting'):
            install_notices(self.source, self.sdk)
        self.assertEqual(conflict.read_bytes(), b'original conflicting declaration')
        self.assertEqual(list((self.sdk/'licenses').iterdir()), [conflict])


if __name__ == '__main__':
    unittest.main()
