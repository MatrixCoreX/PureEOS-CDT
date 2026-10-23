"""AIC distribution identity; inherited compiler provenance remains separate."""
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]


def identity(root=ROOT):
    root = Path(root)
    version = (root/'VERSION').read_text().strip()
    if re.fullmatch(r'(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)', version) is None:
        raise ValueError('AIC CDT VERSION must contain major.minor.patch')
    provenance = json.loads((root/'UPSTREAM_BASELINE.json').read_text())
    if provenance['product'] != 'AIC CDT': raise ValueError('Unexpected toolchain product')
    return dict(product='AIC CDT', version=version, package_directory='aic-cdt-'+version,
                upstream=provenance)
