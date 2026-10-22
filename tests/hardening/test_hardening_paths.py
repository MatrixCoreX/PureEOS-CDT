"""Standalone-checkout controls: no compiler, node, network or cloud required."""
from argparse import Namespace
from pathlib import Path
import tempfile
import unittest

from hardening_paths import negative_baseline, require_cases, resolve_arguments


class HardeningPathTests(unittest.TestCase):
    def test_sdk_and_output_become_absolute_before_child_cwd_changes(self):
        args=Namespace(sdk=Path('relative-sdk'),output=Path('relative-output'))
        expected=(Path.cwd()/'relative-sdk').resolve()
        resolve_arguments(args,'sdk','output')
        self.assertEqual(args.sdk,expected);self.assertTrue(args.output.is_absolute())

    def test_baseline_is_not_inferred_from_checkout_name(self):
        self.assertIsNone(negative_baseline(Path('cdt'),None))

    def test_baseline_self_and_alias_are_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            source=Path(temporary)/'cdt';source.mkdir()
            alias=Path(temporary)/'alias';alias.symlink_to(source)
            for baseline in (source,alias):
                with self.assertRaisesRegex(ValueError,'separate unmodified'):
                    negative_baseline(source,baseline)

    def test_missing_baseline_inputs_are_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaisesRegex(ValueError,'Incomplete'):
                negative_baseline(Path(temporary)/'source',Path(temporary))

    def test_empty_corpus_is_never_a_pass(self):
        for label in ('toolchain','native SDK unit'):
            with self.assertRaisesRegex(ValueError,'empty corpus'):
                require_cases([],label)
        self.assertEqual(require_cases(['case'],'unit'),['case'])


if __name__=='__main__':unittest.main()
