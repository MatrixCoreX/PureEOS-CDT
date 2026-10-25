"""Separate actual contract products from the narrowly recognized CMake compiler probes."""
from pathlib import PurePosixPath
import re


def split_contract_artifacts(files):
    if not isinstance(files,dict) or not files:raise ValueError('Empty contract artifact inventory')
    contracts,probes={},{}
    for name,digest in sorted(files.items()):
        path=PurePosixPath(name)
        if (path.is_absolute() or '..' in path.parts or str(path)!=name or '\\' in name
                or path.suffix not in ('.wasm','.abi') or not re.fullmatch('[0-9a-f]{64}',digest)):
            raise ValueError('Invalid contract artifact entry: '+name)
        if 'CMakeFiles' in path.parts:
            if not re.fullmatch(r'CMakeFiles/[0-9]+(?:\.[0-9]+){1,3}(?:-[A-Za-z0-9.]+)?/CompilerId(C|CXX)/CMake\1CompilerId\.wasm',name):
                raise ValueError('Unrecognized build artifact cannot be silently excluded: '+name)
            probes[name]=digest
        else:contracts[name]=digest
    if not contracts:raise ValueError('No actual contract products')
    return contracts,probes
