"""Regression tests for the actual toolchain tester, without invoking a compiler."""
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'tools/toolchain-tester'))
import tests as tool_tests
from errors import TestFailure
from testsuite import TestSuite
from testrunner import TestRunner
from main import positive_jobs


class ResultTests(unittest.TestCase):
    def test_failed_compiler_launch_clears_previous_success_and_restores_cwd(self):
        test = tool_tests.BuildPassTest('/fixture/probe.cpp', {}, 0,
            SimpleNamespace(name='build-pass', cdt_path='/nonexistent', directory='/fixture'))
        test.success = True
        previous = os.getcwd()
        with mock.patch('subprocess.run', side_effect=FileNotFoundError('compiler missing')):
            with self.assertRaises(FileNotFoundError): test.run()
        self.assertFalse(test.success)
        self.assertEqual(os.getcwd(), previous)

    def test_case_artifacts_are_isolated_and_cwd_restored_on_failure(self):
        previous = os.getcwd()
        with tempfile.TemporaryDirectory() as temporary, mock.patch.dict(os.environ, {'TMPDIR': temporary}), \
             mock.patch.object(tempfile, 'tempdir', temporary):
            seen = []
            for fail in (False, True):
                test = tool_tests.BuildPassTest('/fixture/same.cpp', {}, 0,
                    SimpleNamespace(name='build-pass', cdt_path='/compiler/bin', directory='/fixture'))
                def compiler(*args, **kwargs):
                    seen.append(os.getcwd())
                    (Path.cwd() / 'same.wasm').write_text(str(fail))
                    return subprocess.CompletedProcess([], int(fail), b'', b'')
                with mock.patch('subprocess.run', side_effect=compiler):
                    if fail:
                        with self.assertRaises(TestFailure): test.run()
                    else: test.run()
                self.assertEqual(os.getcwd(), previous)
            self.assertEqual(len(set(seen)), 2)
            self.assertEqual([(Path(p) / 'same.wasm').read_text() for p in seen], ['False', 'True'])

    def test_qualified_test_selection_does_not_collide_between_suites(self):
        suites = [SimpleNamespace(name=name, tests=[tool_tests.BuildPassTest('same.cpp', {}, 0,
                  SimpleNamespace(name=name))]) for name in ('build-pass', 'compile-pass')]
        runner = TestRunner(suites, 'compile-pass/same_0', 1)
        self.assertEqual([test.fullname for test in runner.tests_to_run], ['compile-pass/same_0'])

    def test_jobs_reject_zero_negative_and_accept_one(self):
        import argparse
        self.assertEqual(positive_jobs('1'), 1)
        for value in ('0', '-1'):
            with self.assertRaises(argparse.ArgumentTypeError): positive_jobs(value)

    def make_test(self, expected=None):
        return tool_tests.BuildPassTest('probe.cpp',
            {} if expected is None else {'expected': expected}, 0,
            SimpleNamespace(name='build-pass'))

    def test_success_requires_zero(self):
        for code in (0, 1, -signal.SIGSEGV, -signal.SIGTERM):
            with self.subTest(code=code):
                test = self.make_test()
                result = subprocess.CompletedProcess([], code, b'', b'diagnostic')
                if code == 0:
                    test.handle_test_result(result)
                    self.assertTrue(test.success)
                else:
                    with self.assertRaises(TestFailure):
                        test.handle_test_result(result)
                    self.assertFalse(test.success)

    def test_crashes_are_not_expected_compiler_failures(self):
        for code in (0, -signal.SIGSEGV, -signal.SIGTERM):
            with self.subTest(code=code):
                test = self.make_test()
                with self.assertRaises(TestFailure):
                    test.handle_test_result(subprocess.CompletedProcess([], code, b'', b''), False)
                self.assertFalse(test.success)

    def test_expected_diagnostic_failure(self):
        test = self.make_test({'exit-code': 1, 'stderr': 'invalid argument'})
        test.handle_test_result(subprocess.CompletedProcess([], 1, b'', b'invalid argument'), False)
        self.assertTrue(test.success)

    def test_wrong_diagnostic_is_not_success(self):
        test = self.make_test({'stderr': 'invalid argument'})
        with self.assertRaises(TestFailure):
            test.handle_test_result(subprocess.CompletedProcess([], 1, b'', b'other error'), False)
        self.assertFalse(test.success)

    def test_explicit_zero_exit_is_checked(self):
        test = self.make_test({'exit-code': 0})
        with self.assertRaises(TestFailure):
            test.handle_test_result(subprocess.CompletedProcess([], 1, b'', b''), False)

    def test_previous_success_does_not_survive_failure(self):
        test = self.make_test()
        test.handle_test_result(subprocess.CompletedProcess([], 0, b'', b''))
        with self.assertRaises(TestFailure):
            test.handle_test_result(subprocess.CompletedProcess([], -9, b'', b''))
        self.assertFalse(test.success)

    def test_build_fail_dispatches_to_negative_test(self):
        fixture = json.dumps({'tests': [{}]})
        with mock.patch('os.listdir', return_value=['probe.cpp', 'probe.json']), \
             mock.patch('os.path.isfile', return_value=True), \
             mock.patch('builtins.open', mock.mock_open(read_data=fixture)):
            suite = TestSuite('/fixtures/build-fail', '/unused')
        self.assertEqual(len(suite.tests), 1)
        self.assertIsInstance(suite.tests[0], tool_tests.BuildFailTest)
        with mock.patch('subprocess.run', return_value=subprocess.CompletedProcess([], 1, b'', b'')):
            suite.tests[0].run()
        self.assertTrue(suite.tests[0].success)


if __name__ == '__main__':
    unittest.main()
