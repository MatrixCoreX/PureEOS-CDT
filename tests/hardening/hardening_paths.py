"""Portable path and nonempty-corpus checks for the standalone CDT repository."""
from pathlib import Path


def resolve_arguments(args, *names):
    for name in names:
        setattr(args, name, Path(getattr(args, name)).resolve())


def negative_baseline(source, baseline):
    if baseline is None:
        return None
    source, baseline = Path(source).resolve(), Path(baseline).resolve(strict=True)
    if source == baseline:
        raise ValueError('Negative control baseline must be a separate unmodified checkout')
    for name in ('libraries/eosiolib/core/eosio/varint.hpp',
                 'libraries/eosiolib/core/eosio/datastream.hpp', 'libraries/meta_refl/include'):
        if not (baseline/name).exists():
            raise ValueError('Incomplete negative control baseline: '+name)
    return baseline


def require_cases(cases, label):
    if not cases:
        raise ValueError('No '+label+' cases found; an empty corpus is not a pass')
    return cases
