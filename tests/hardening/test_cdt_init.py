"""Compile and execute the ACTUAL standalone project generator, not a mock."""
from pathlib import Path
import subprocess
import tempfile
import unittest


class CDTInitTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.area = tempfile.TemporaryDirectory(prefix='pureeos-cdt-init-unit-')
        cls.root = Path(cls.area.name); cls.program = cls.root/'cdt-init'
        source = Path(__file__).resolve().parents[2]/'tools/init/cdt-init.cpp'
        try:
            subprocess.run(['c++', '-std=c++17', '-O2', '-Wall', '-Wextra', '-Werror',
                '-DAIC_CDT_INIT_VERSION="test-candidate"', str(source), '-o', str(cls.program)],
                capture_output=True, text=True, check=True, timeout=120)
        except BaseException:
            cls.area.cleanup(); raise

    @classmethod
    def tearDownClass(cls): cls.area.cleanup()

    def invoke(self, *args, cwd=None):
        return subprocess.run([str(self.program), *args], cwd=cwd or self.root,
            capture_output=True, text=True, timeout=10)

    def test_help_and_version_need_no_project(self):
        self.assertEqual(self.invoke('--help').returncode, 0)
        result = self.invoke('--version'); self.assertEqual(result.returncode, 0)
        self.assertIn('test-candidate', result.stdout)
        self.assertEqual(result.stdout.strip(), 'AIC CDT test-candidate (cdt-init)')

    def test_normal_scaffold_has_both_cmake_minima_and_pinned_child_sdk(self):
        with tempfile.TemporaryDirectory(dir=self.root) as parent:
            result = self.invoke('--project=normal', '--path='+parent); self.assertEqual(result.returncode, 0, result.stderr)
            root = Path(parent)/'normal'
            self.assertIn('cmake_minimum_required(VERSION 3.20)', (root/'CMakeLists.txt').read_text())
            self.assertIn('cmake_minimum_required(VERSION 3.20)', (root/'src/CMakeLists.txt').read_text())
            self.assertIn('-Dcdt_DIR=${CDT_ROOT}/lib/cmake/cdt', (root/'CMakeLists.txt').read_text())
            self.assertTrue((root/'src/normal.cpp').is_file()); self.assertTrue((root/'include/normal.hpp').is_file())

    def test_bare_and_separated_arguments_in_parent_with_spaces(self):
        with tempfile.TemporaryDirectory(prefix='parent with spaces ', dir=self.root) as parent:
            result = self.invoke('--project', 'barecase', '--path', parent, '--bare')
            self.assertEqual(result.returncode, 0, result.stderr)
            root = Path(parent)/'barecase'
            self.assertTrue((root/'barecase.cpp').is_file()); self.assertTrue((root/'barecase.hpp').is_file())
            self.assertFalse((root/'CMakeLists.txt').exists())

    def test_existing_project_is_preserved(self):
        with tempfile.TemporaryDirectory(dir=self.root) as parent:
            root = Path(parent)/'keep'; root.mkdir(); (root/'user.txt').write_text('unchanged')
            result = self.invoke('--project=keep', '--path='+parent)
            self.assertNotEqual(result.returncode, 0); self.assertIn('refusing to overwrite', result.stderr)
            self.assertEqual(list(root.iterdir()), [root/'user.txt']); self.assertEqual((root/'user.txt').read_text(), 'unchanged')

    def test_project_symlink_is_not_overwritten(self):
        with tempfile.TemporaryDirectory(dir=self.root) as parent:
            root = Path(parent); (root/'real').mkdir(); (root/'alias').symlink_to(root/'real')
            self.assertNotEqual(self.invoke('--project=alias', '--path='+parent).returncode, 0)
            self.assertEqual(list((root/'real').iterdir()), [])

    def test_invalid_identifier_duplicate_unknown_and_missing_values_refused(self):
        for args in ((), ('--project=../escape',), ('--project=',), ('--project',),
                ('--unknown',), ('--project=a', '--project=b'), ('--project=1wrong',)):
            with self.subTest(args=args): self.assertNotEqual(self.invoke(*args).returncode, 0)

    def test_missing_or_non_directory_parent_refused_without_creation(self):
        with tempfile.TemporaryDirectory(dir=self.root) as parent:
            root = Path(parent); (root/'file').write_text('not directory')
            for p in (root/'missing', root/'file'):
                with self.subTest(path=p): self.assertNotEqual(self.invoke('--project=test', '--path='+str(p)).returncode, 0)
            self.assertEqual(list(root.iterdir()), [root/'file'])


if __name__ == '__main__': unittest.main()
