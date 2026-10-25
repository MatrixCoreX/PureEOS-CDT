"""Distribution version cannot silently inherit the upstream release number."""
import json
from pathlib import Path
import tempfile
import unittest
import shutil
import subprocess

from aic_identity import ROOT, identity


class AICIdentityTests(unittest.TestCase):
    def test_product_release_and_upstream_are_distinct(self):
        actual=identity()
        self.assertEqual(actual['product'],'AIC CDT')
        self.assertEqual(actual['version'],'1.0.0')
        self.assertEqual(actual['package_directory'],'aic-cdt-1.0.0')
        self.assertEqual(actual['upstream']['upstream_version'],'5.0.0-dev1.1')
        self.assertIn('include(modules/AICCDTVersion.cmake)', (ROOT/'CMakeLists.txt').read_text())
    def test_actual_cmake_reader_uses_the_same_version_and_rejects_extra_lines(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'modules').mkdir()
            shutil.copy2(ROOT/'modules/AICCDTVersion.cmake',root/'modules/AICCDTVersion.cmake')
            script=root/'probe.cmake'
            script.write_text('include("${CMAKE_CURRENT_LIST_DIR}/modules/AICCDTVersion.cmake")\n'
                'message(STATUS "AIC=${AIC_CDT_VERSION};parts=${VERSION_MAJOR}.${VERSION_MINOR}.${VERSION_PATCH}")\n')
            for value,passed in [('1.0.0\n',True),('01.0.0',False),('1.0.0\n2.0.0',False),('1.0',False)]:
                (root/'VERSION').write_text(value)
                result=subprocess.run(['cmake','-P',str(script)],text=True,capture_output=True,timeout=15)
                self.assertEqual(result.returncode==0,passed,result.stdout+result.stderr)
                if passed:self.assertIn('AIC=1.0.0;parts=1.0.0',result.stdout)
    def test_invalid_versions_are_rejected_before_packaging(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'UPSTREAM_BASELINE.json').write_text(json.dumps({'product':'AIC CDT'}))
            for invalid in ('','5.0.0-dev1.1','1.0','01.0.0','../1.0.0','1.0.0\n2.0.0'):
                (root/'VERSION').write_text(invalid)
                with self.assertRaises(ValueError):identity(root)


if __name__=='__main__':unittest.main()
