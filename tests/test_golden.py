from types import SimpleNamespace
import copy

import pytest

from nestling import golden


def examples():
    return [SimpleNamespace(**golden.to_example(c)) for c in golden.load()]


def test_only_v3_is_active_and_reviewed_with_versioned_ids():
    cases = golden.load()
    assert golden.DATASET_VERSION == 'golden_v3' and len(cases) == 62
    assert all(c['review_status'] == 'reviewed' for c in cases)
    example = golden.to_example(cases[0])
    assert example['metadata']['dataset_sha256'] == golden.SHA256
    golden.validate_examples(examples())


@pytest.mark.parametrize('field', ['inputs', 'outputs', 'metadata', 'id', 'duplicate'])
def test_remote_same_count_changed_content_is_rejected(field):
    rows = copy.deepcopy(examples())
    if field == 'inputs': rows[0].inputs['question'] = 'changed question'
    elif field == 'outputs': rows[0].outputs['expected_escalate'] = True
    elif field == 'metadata': rows[0].metadata['dataset_sha256'] = 'wrong'
    elif field == 'id': rows[0].id = 'foreign-id'
    else: rows[0] = rows[1]
    with pytest.raises(ValueError, match='dataset|example|duplicate'):
        golden.validate_examples(rows)


def test_hash_normalizes_bom_crlf_and_rejects_changed_file(tmp_path, monkeypatch):
    original = golden.PATH.read_text(encoding='utf-8-sig').replace('\r\n', '\n')
    path = tmp_path / 'golden.csv'
    path.write_bytes(('\ufeff' + original.replace('\n', '\r\n')).encode('utf-8'))
    monkeypatch.setattr(golden, 'PATH', path)
    assert len(golden.load()) == 62
    path.write_text(original.replace('vegetarian?', 'vegetarian please?', 1), encoding='utf-8')
    with pytest.raises(RuntimeError, match='changed after'):
        golden.load()


@pytest.mark.parametrize('bad_metadata', [True, False])
def test_upload_validates_existing_dataset_metadata_and_frozen_tag(bad_metadata):
    class FakeClient:
        def has_dataset(self, **kwargs): return True
        def read_dataset(self, **kwargs):
            return SimpleNamespace(id='dataset-id', metadata={
                'dataset_version': golden.DATASET_VERSION,
                'dataset_sha256': 'wrong' if bad_metadata else golden.SHA256, 'n_cases': 62})
        def list_examples(self, **kwargs):
            rows = examples()
            if kwargs.get('as_of') == 'frozen':
                rows[0].outputs['expected_behavior'] = 'changed frozen tag'
            return rows
    with pytest.raises(ValueError, match='dataset'):
        golden.upload(FakeClient())


@pytest.mark.parametrize('module_name, function, args', [
    ('nestling.graph', 'run_experiment', ('v6',)), ('nestling.graph', 'run_one', ('H01',)),
    ('nestling.baseline', 'run_experiment', ()), ('nestling.baseline', 'run_one', ('H01',)),
])
def test_active_v3_uses_metered_runner_instead_of_unmetered_legacy_paths(module_name, function, args):
    import importlib
    with pytest.raises(RuntimeError, match='v3_run'):
        getattr(importlib.import_module(module_name), function)(*args)
