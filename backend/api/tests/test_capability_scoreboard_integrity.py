import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]


def test_all_55_capability_groups_have_explicit_test_gap_plan():
    document=json.loads((ROOT/'docs/verification/commerce-capability-scoreboard.json').read_text())
    groups=document['capabilities']
    assert len(groups)==55 and {g['id'] for g in groups}=={f'CAP-{n:02}' for n in range(1,56)}
    for group in groups:
        plan=group['verification_plan']
        assert plan['coverage'] in {'scoped_group_only','partial_or_adjacent_only'}
        assert len(plan['required_scenarios'])>=4
        assert plan['remaining_boundary_gap'] and plan['next_action']
        assert plan['candidate_caveat'] and plan['live_provider_or_owner_gate']
        for name in plan['candidate_test_files']:
            path=(ROOT/name).resolve()
            assert path.is_relative_to(ROOT.resolve()) and path.is_file()
            assert path.name.startswith('test_') and 'def test_' in path.read_text()
    summary=document['summary']
    assert summary['inventory_groups']==len(groups)
    assert summary['source_reachable']==sum(g['reachable']=='yes_source_path' for g in groups)
    assert summary['partial_boundary_groups']==sum(g['real_boundary_tested']=='partial' for g in groups)
    assert summary['fully_reconciled_real_boundary_groups']==sum(g['real_boundary_tested']=='yes_scoped_group' for g in groups)
    assert summary['live_verified_groups']==sum(g['live_verified'] for g in groups)
