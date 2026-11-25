"""Historical method retention is a tripwire, never behavior acceptance."""
import ast,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]

def identities(path):
    found=set()
    for node in ast.parse(path.read_text()).body:
        if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)):found.add(node.name)
        elif isinstance(node,ast.ClassDef):
            found.update(node.name+'.'+member.name for member in node.body if isinstance(member,(ast.FunctionDef,ast.AsyncFunctionDef)))
    return found

def test_all_252_original_qualified_method_identities_retained():
    document=json.loads((ROOT/'docs/verification/original-method-inventory-v1.json').read_text())
    assert document['baseline']=='8b82cf3'
    assert document['total']==252==sum(len(v) for v in document['files'].values())
    for filename,original in document['files'].items():
        # Preserve the historical inventory verbatim; resolve only its source location.
        canonical=filename.replace('apps/api/','backend/api/')
        manifests=['provider-capacity-layout-v1.json','service-domain-layout-v1.json']
        for manifest_name in manifests:
            manifest=json.loads((ROOT/'docs/verification'/manifest_name).read_text())
            for row in manifest['modules']:
                legacy=row.get('legacy_module',row.get('old_module',''))
                previous='backend/api/'+legacy.replace('.','/')+'.py'
                if canonical==previous:canonical=row['path']
        path=ROOT/canonical
        assert path.is_file() and len(original)==len(set(original))
        assert set(original)<=identities(path), (filename,sorted(set(original)-identities(path)))

def test_canonical_group_identity_never_implies_live_or_full_feature_acceptance():
    original=json.loads((ROOT/'docs/verification/original-current-parity-2026-11-24.json').read_text())
    current=json.loads((ROOT/'docs/verification/current-parity-progress-2026-11-24.json').read_text())
    scoreboard=json.loads((ROOT/'docs/verification/commerce-capability-scoreboard.json').read_text())
    expected={f'CAP-{i:02}' for i in range(1,56)}
    assert {r['id'] for r in original['rows']}=={r['id'] for r in current['rows']}=={r['id'] for r in scoreboard['capabilities']}==expected
    for row in scoreboard['capabilities']:
        assert isinstance(row['live_verified'],bool)
        if row['live_verified']:
            assert row.get('live_evidence_reference'), 'Live flag needs an explicit deployed receipt'
    assert current['no_live_certification'] is True
