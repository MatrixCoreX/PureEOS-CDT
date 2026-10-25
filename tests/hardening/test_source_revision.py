from pathlib import Path
import json
import tempfile
import unittest

from source_revision import sha,source_revision


class FrozenSourceRevisionTests(unittest.TestCase):
    def fixture(self,tmp):
        root=Path(tmp)/'source';root.mkdir();(root/'VERSION').write_text('1.0.0\n')
        metadata=Path(tmp)/'identity.json'
        data=dict(repository_base_commit='a'*40,repository_base_epoch=1234,files_sha256={'VERSION':sha(root/'VERSION')})
        metadata.write_text(json.dumps(data));return root,metadata,data

    def test_complete_frozen_source_is_usable_without_git(self):
        with tempfile.TemporaryDirectory() as tmp:
            root,metadata,_=self.fixture(tmp);actual=source_revision(root,metadata)
            self.assertEqual(actual['source_commit'],'a'*40);self.assertEqual(actual['source_files'],1)
            self.assertEqual(actual['metadata_sha256'],sha(metadata))

    def test_modified_or_unlisted_sources_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root,metadata,_=self.fixture(tmp);(root/'VERSION').write_text('2.0.0\n')
            with self.assertRaises(ValueError):source_revision(root,metadata)
            (root/'VERSION').write_text('1.0.0\n');(root/'extra.cpp').write_text('unlisted')
            with self.assertRaises(ValueError):source_revision(root,metadata)

    def test_escaping_paths_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root,metadata,data=self.fixture(tmp)
            for name in ('../identity.json','/VERSION','./VERSION'):
                data['files_sha256']={name:'a'*64};metadata.write_text(json.dumps(data))
                with self.assertRaises(ValueError):source_revision(root,metadata)

    def test_malformed_commit_epoch_and_empty_manifest_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root,metadata,original=self.fixture(tmp)
            for update in ({'repository_base_commit':'unknown'},{'repository_base_epoch':True},
                    {'repository_base_epoch':-1},{'files_sha256':{}}):
                metadata.write_text(json.dumps({**original,**update}))
                with self.assertRaises(ValueError):source_revision(root,metadata)

    def test_metadata_inside_source_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root,metadata,_=self.fixture(tmp);inside=root/'identity.json';inside.write_bytes(metadata.read_bytes())
            with self.assertRaises(ValueError):source_revision(root,inside)


if __name__=='__main__':unittest.main()
