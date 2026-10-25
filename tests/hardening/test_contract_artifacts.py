import unittest
from contract_artifacts import split_contract_artifacts


class ArtifactInventoryTests(unittest.TestCase):
    def test_cmake_versions_do_not_change_actual_contract_inventory(self):
        actual={'eosio.system/eosio.system.wasm':'a'*64,'eosio.system/eosio.system.abi':'b'*64}
        for version in ('4.2.3','4.3.4'):
            files={**actual,**{f'CMakeFiles/{version}/CompilerId{lang}/CMake{lang}CompilerId.wasm':'c'*64 for lang in ('C','CXX')}}
            contracts,probes=split_contract_artifacts(files)
            self.assertEqual(contracts,actual);self.assertEqual(len(probes),2)

    def test_changed_contract_bytes_remain_visible(self):
        old,_=split_contract_artifacts({'eosio.token/eosio.token.wasm':'a'*64})
        new,_=split_contract_artifacts({'eosio.token/eosio.token.wasm':'b'*64})
        self.assertNotEqual(old,new)

    def test_actual_powerup_hidden_directory_is_preserved(self):
        files={'eosio.system/.powerup/powup.results.wasm':'a'*64}
        self.assertEqual(split_contract_artifacts(files),(files,{}))

    def test_unknown_cmake_wasm_is_never_dropped(self):
        for name in ('CMakeFiles/4.3.4/other.wasm','CMakeFiles/4.3.4/CompilerIdC/CMakeCXXCompilerId.wasm',
                'eosio.system/CMakeFiles/real.wasm'):
            with self.subTest(name=name),self.assertRaises(ValueError):
                split_contract_artifacts({'eosio.system/eosio.system.wasm':'a'*64,name:'b'*64})

    def test_unsafe_paths_and_invalid_digests_are_rejected(self):
        for name,digest in (('../contract.wasm','a'*64),('/contract.wasm','a'*64),('dir\\contract.wasm','a'*64),
                ('contract.wasm','z'*64),('contract.cpp','a'*64)):
            with self.subTest(name=name),self.assertRaises(ValueError):split_contract_artifacts({name:digest})

    def test_empty_and_probe_only_inventories_are_rejected(self):
        for files in ({},{'CMakeFiles/4.3.4/CompilerIdC/CMakeCCompilerId.wasm':'a'*64}):
            with self.subTest(files=files),self.assertRaises(ValueError):split_contract_artifacts(files)


if __name__=='__main__':unittest.main()
