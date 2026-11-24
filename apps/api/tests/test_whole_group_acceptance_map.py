"""The twenty partial groups need explicit separate acceptance, not count inflation."""
import json,re,subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]


def test_acceptance_map_exactly_tracks_partial_groups_and_existing_evidence_leads():
    document=json.loads((ROOT/'docs/verification/whole-group-acceptance-map-v1.json').read_text())
    ledger=json.loads((ROOT/'docs/verification/current-parity-progress-2026-11-24.json').read_text())
    expected={r['id'] for r in ledger['rows'] if r['parity']!='preserved'}
    assert len(document['rows'])==len(expected)==20
    assert {r['id'] for r in document['rows']}==expected
    assert document['closed_partial_groups']==0 and document['remaining_partial_groups']==20
    assert document['canonical_group_count']==55
    assert re.fullmatch('[0-9a-f]{40}',document['source_revision'])
    for row in document['rows']:
        assert row['whole_group_closed'] is False
        assert row['code_status']=='review_required'
        assert row['quality_status']==row['owner_status']=='unverified'
        assert row['evidence_leads'] and not row['unresolved_test_leads']
        assert all((ROOT/p).is_file() for p in row['evidence_leads'])
        assert all(row[k] for k in ('current_source_scope','next_code_or_boundary_acceptance','quality_acceptance','owner_acceptance'))
