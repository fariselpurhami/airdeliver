#!/usr/bin/env python3
"""Export every exact Python lock identity, including alternate platform builds.

No installs, imports of project code, registry access or secret reads. Version
identities are never normalized to hide vendor build suffixes. Requirements are
split because pip-audit rejects simultaneous versions of one package name.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import tomllib
from urllib.parse import quote


def inventory(path):
    raw = Path(path).read_bytes()
    lock = tomllib.loads(raw.decode())
    entries = []
    seen = set()
    for row in lock['package']:
        name, version = row['name'], row['version']
        if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,150}', name):
            raise ValueError('Invalid package name')
        if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.+!-]{0,150}', version):
            raise ValueError('Invalid locked version')
        identity = (name.lower().replace('_', '-'), version)
        if identity in seen:
            raise ValueError('Duplicate lock identity')
        seen.add(identity)
        source = row.get('source', {})
        entries.append({'name': name, 'version': version,
            'purl': 'pkg:pypi/' + quote(name, safe='') + '@' + quote(version, safe=''),
            'source_type': source.get('type', 'pypi'),
            'source_name': source.get('reference'),
            'hashes': sorted({f['hash'] for f in row.get('files', [])}),
            'audit_requirement_eligible': source.get('type') not in {'git', 'directory', 'file', 'url'},
            'license_status': 'not_collected_requires_review'})
    return {'format': 'airdeliver-exact-python-lock-inventory-v1',
            'lock_sha256': hashlib.sha256(raw).hexdigest(),
            'components': sorted(entries, key=lambda row: (row['name'], row['version'])),
            'caveat': 'Lock inventory, not installed-runtime attestation, license clearance, image SBOM or vulnerability verdict.'}


def batches(components):
    result = []
    for component in components:
        if not component['audit_requirement_eligible']:
            continue
        name = component['name']
        for batch in result:
            if name not in batch:
                batch[name] = component['version']
                break
        else:
            result.append({name: component['version']})
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--lock', default='apps/api/poetry.lock')
    parser.add_argument('--output-dir', required=True)
    args = parser.parse_args()
    output = Path(args.output_dir)
    output.mkdir(parents=True, exist_ok=True)
    data = inventory(args.lock)
    (output / 'inventory.json').write_text(json.dumps(data, indent=2) + '\n')
    for index, batch in enumerate(batches(data['components'])):
        (output / f'requirements-{index}.txt').write_text(''.join(f'{name}=={version}\n' for name, version in sorted(batch.items())))
    print(json.dumps({'components': len(data['components']), 'batches': len(batches(data['components'])),
                      'lock_sha256': data['lock_sha256'], 'writes': 'output directory only'}))

if __name__ == '__main__':
    main()
