"""Small real CPU training jobs. Synthetic fixtures never approve deployment."""
import json
import math
from pathlib import Path

import pytest
import torch
from app.services.ai_behavior_engine import ACTION_MAP, OmniNetConfig
from app.services.behavior_checkpoint import load_behavior_checkpoint, ModelArtifactError
from app.services.behavior_training import (
    load_interaction_dataset, split_examples, subject_partition, train_behavior_candidate,
)


def tiny():
    return OmniNetConfig(internal_dim=8,intermediate_size=16,heads=2,layers=1,
                         dropout=0,supported_dims={'dim_8':8})


def dataset(path):
    groups={name:[] for name in ('train','validation','test')}
    for i in range(1000):
        name=f'subject-{i}';p=subject_partition(name)
        if len(groups[p])<3:groups[p].append(name)
        if all(len(group)==3 for group in groups.values()):break
    rows=[]
    for subjects in groups.values():
        for n,subject in enumerate(subjects):
            events=[]
            for i,action in enumerate(['view','view','cart','buy','discard','cart','discard']):
                item=(n+i)%8
                events.append(dict(event_id=f'{subject}-{i}',item_id=f'item-{item}',action=action,
                                   timestamp=1000+i,vector=[float(x==item) for x in range(8)]))
            rows.append(dict(subject_id=subject,embedding_source='test-embedding@revision1',source='synthetic',events=events))
    path.write_text(''.join(json.dumps(row)+'\n' for row in rows));return rows


def test_dataset_and_subject_split_are_stable_and_disjoint(tmp_path):
    path=tmp_path/'data.jsonl';dataset(path)
    sessions=load_interaction_dataset(path);splits,subjects=split_examples(sessions)
    assert not subjects['train'] & subjects['test']
    assert not subjects['train'] & subjects['validation']
    assert not subjects['test'] & subjects['validation']
    assert split_examples(list(reversed(sessions)))[1]==subjects
    for examples in splits.values():
        assert all(x.context[-1].timestamp<=x.target.timestamp for x in examples)
        assert all(x.target.event_id not in {e.event_id for e in x.context} for x in examples)


@pytest.mark.parametrize('case',['duplicate','unordered','dimension','revision','nonfinite','unknown_action'])
def test_dataset_rejects_invalid_records(tmp_path,case):
    path=tmp_path/'data.jsonl';rows=dataset(path)
    if case=='duplicate':rows[1]['events'][0]['event_id']=rows[0]['events'][0]['event_id']
    if case=='unordered':rows[0]['events'][1]['timestamp']=1
    if case=='dimension':rows[0]['events'][0]['vector']=[1.]*4
    if case=='revision':rows[0]['embedding_source']='no-revision'
    if case=='nonfinite':rows[0]['events'][0]['vector'][0]=float('nan')
    if case=='unknown_action':rows[0]['events'][0]['action']='fabricated_action'
    path.write_text(''.join(json.dumps(row)+'\n' for row in rows))
    with pytest.raises(ValueError):load_interaction_dataset(path)


def test_missing_partition_is_rejected(tmp_path):
    path=tmp_path/'data.jsonl';rows=dataset(path);path.write_text(json.dumps(rows[0]))
    with pytest.raises(ValueError,match='nonempty'):split_examples(load_interaction_dataset(path))


def test_real_training_warm_start_and_unapproved_artifact(tmp_path):
    path=tmp_path/'data.jsonl';dataset(path);out=tmp_path/'candidate.pt'
    old_threads=torch.get_num_threads();torch.set_num_threads(1)
    try:
        report=train_behavior_candidate(path,out,tiny(),model_version='test-v1',epochs=1,batch_size=3)
        loaded=load_behavior_checkpoint(out,expected_sha256=report['sha256'],expected_actions=ACTION_MAP)
        assert all(x>0 for x in report['optimizer_steps'].values())
        assert loaded.manifest.production_approved is False
        assert loaded.manifest.evaluation_source=='synthetic'
        assert all(math.isfinite(x) for x in report['test_metrics'].values())
        assert json.loads(Path(str(out)+'.metrics.json').read_text())['sha256']==loaded.sha256
        warm=tmp_path/'warm.pt'
        warm_report=train_behavior_candidate(path,warm,tiny(),model_version='test-v2',epochs=1,batch_size=3,warm_start=out)
        assert warm_report['model_version']=='test-v2'
        assert not warm_report['production_approved']
        with pytest.raises(ModelArtifactError,match='real-data'):
            load_behavior_checkpoint(warm,production=True,expected_sha256=warm_report['sha256'])
        wrong=tiny().model_copy(update={'intermediate_size':24})
        with pytest.raises(ValueError,match='architecture'):
            train_behavior_candidate(path,tmp_path/'bad.pt',wrong,model_version='bad',epochs=1,warm_start=out)
    finally:torch.set_num_threads(old_threads)


def test_cli_runs_real_small_job_without_replacing_an_artifact(tmp_path,capsys):
    from scripts.train_behavior import main
    path=tmp_path/'data.jsonl';dataset(path)
    config=tmp_path/'config.json';config.write_text(tiny().model_dump_json())
    output=tmp_path/'candidate.pt'
    args=['--dataset',str(path),'--config',str(config),'--output',str(output),
          '--model-version','cli-v1','--epochs','1','--batch-size','3']
    assert main(args)==0
    report=json.loads(capsys.readouterr().out)
    assert report['production_approved'] is False
    original=output.read_bytes()
    with pytest.raises(SystemExit):main(args)
    assert output.read_bytes()==original


def test_training_api_refuses_existing_output_before_work(tmp_path):
    output=tmp_path/'existing.pt';output.write_bytes(b'keep existing artifact')
    with pytest.raises(ValueError,match='exists'):
        train_behavior_candidate(tmp_path/'missing.jsonl',output,tiny(),model_version='v1')
    assert output.read_bytes()==b'keep existing artifact'
