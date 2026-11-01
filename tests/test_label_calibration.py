import csv

import pytest

from evals import label_calibration as labels


def rows():
    return [{'case_id': 'A', 'judge_faithful': 'Y', 'judge_task_fulfilled': 'Y',
             'human_faithful': '', 'human_task_fulfilled': '', 'human_note': ''}]


def test_empty_review_never_claims_agreement(tmp_path):
    path = tmp_path / 'review.csv'
    labels.save_rows(path, rows())
    result = labels.report(path)
    assert result['faithfulness']['n_labelled'] == 0
    assert result['faithfulness']['agreement'] is None


def test_false_pass_counts_and_atomic_save_preserve_existing_note(tmp_path):
    path = tmp_path / 'review.csv'
    data = rows()
    data[0].update(human_faithful='N', human_task_fulfilled='Y', human_note='unsupported claim')
    labels.save_rows(path, data)
    result = labels.report(path)
    assert result['faithfulness']['judge_false_passes'] == 1
    assert result['faithfulness']['agreement'] == 0
    assert result['task_fulfillment']['agreement'] == 1
    assert labels.read_rows(path)[0]['human_note'] == 'unsupported claim'


def test_skip_and_invalid_input_never_make_a_human_yes():
    answers = iter(['maybe', 'skip'])
    assert labels.ask_label('label', lambda prompt: next(answers)) == ''


def test_evidence_rejects_path_traversal(tmp_path):
    with pytest.raises(ValueError, match='Unknown review round'):
        labels.evidence({'round': '../../.env'}, tmp_path)
