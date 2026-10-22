"""Only source-layout controls; no compiled contract evidence."""
from pathlib import Path
import tempfile
import unittest

from build_system_contracts import contract_source


def fixture(root):
    root.mkdir(parents=True, exist_ok=True); (root/'CMakeLists.txt').write_text('# fixture')
    for name in ('eosio.system', 'eosio.token'):
        directory = root/name/'src'; directory.mkdir(parents=True)
        (directory/(name+'.cpp')).write_text('// fixture')


class ContractSourceControls(unittest.TestCase):
    def test_repository_and_inner_source_resolve_identically(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); fixture(root/'contracts')
            self.assertEqual(contract_source(root), (root/'contracts').resolve())
            self.assertEqual(contract_source(root/'contracts'), (root/'contracts').resolve())

    def test_incomplete_or_ambiguous_input_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with self.assertRaises(ValueError): contract_source(root)
            fixture(root); fixture(root/'contracts')
            with self.assertRaises(ValueError): contract_source(root)

    def test_alias_resolves_only_to_the_actual_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); fixture(root/'source'); (root/'alias').symlink_to(root/'source')
            self.assertEqual(contract_source(root/'alias'), (root/'source').resolve())


if __name__ == '__main__': unittest.main()
