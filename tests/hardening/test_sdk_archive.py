import hashlib
import os
from pathlib import Path
import tarfile
import tempfile
import unittest

from sdk_archive import archive_sdk


class SDKArchiveControls(unittest.TestCase):
    def fixture(self, root):
        sdk = root/'sdk'; sdk.mkdir(mode=0o700); (sdk/'bin').mkdir(mode=0o700)
        (sdk/'LICENSE').write_text('retained license'); (sdk/'LICENSE').chmod(0o600)
        (sdk/'bin/compiler').write_bytes(b'fixture'); (sdk/'bin/compiler').chmod(0o700)
        return sdk

    def test_public_install_permissions_and_owners(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); sdk = self.fixture(root); archive = root/'sdk.tar.gz'; archive_sdk(sdk, archive, 1234)
            with tarfile.open(archive) as stream:
                for m in stream:
                    self.assertEqual((m.uid, m.gid, m.uname, m.gname, m.mtime), (0, 0, 'root', 'root', 1234))
                    self.assertEqual(m.mode, 0o755 if m.isdir() or m.name.endswith('/compiler') else 0o644)

    def test_same_bytes_despite_archive_name_and_source_mtime(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); sdk = self.fixture(root)
            archive_sdk(sdk, root/'one.tar.gz', 1234)
            for p in [sdk, *sdk.rglob('*')]: os.utime(p, (2000, 3000))
            archive_sdk(sdk, root/'two.tar.gz', 1234)
            self.assertEqual(hashlib.sha256((root/'one.tar.gz').read_bytes()).digest(),
                hashlib.sha256((root/'two.tar.gz').read_bytes()).digest())

    def test_existing_archive_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); sdk = self.fixture(root); out = root/'old'; out.write_bytes(b'keep')
            with self.assertRaises(FileExistsError): archive_sdk(sdk, out, 1234)
            self.assertEqual(out.read_bytes(), b'keep')

    def test_links_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); sdk = self.fixture(root); (sdk/'link').symlink_to('LICENSE')
            with self.assertRaisesRegex(ValueError, 'links'): archive_sdk(sdk, root/'sdk.tar.gz', 1234)

    def test_archive_inside_sdk_and_invalid_epoch_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); sdk = self.fixture(root)
            with self.assertRaises(ValueError): archive_sdk(sdk, sdk/'self.tar.gz', 1234)
            for value in (-1, 0x100000000, '123'):
                with self.subTest(value=value), self.assertRaises(ValueError): archive_sdk(sdk, root/'out', value)


if __name__ == '__main__': unittest.main()
