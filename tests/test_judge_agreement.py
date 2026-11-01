import csv

import pytest

from evals.judge import agreement


def write_sheet(tmp_path, rows):
    path = tmp_path / "calibration.csv"
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=[
            "case_id", "judge_faithful", "human_faithful", "human_note", "judge_unsupported",
        ])
        writer.writeheader()
        writer.writerows(rows)
    return path


def test_confusion_counts_use_human_reference_and_preserve_review_text(tmp_path):
    path = write_sheet(tmp_path, [
        {"case_id": "TP", "judge_faithful": " y ", "human_faithful": "Y"},
        {"case_id": "TN", "judge_faithful": "n", "human_faithful": " n "},
        {"case_id": "FP", "judge_faithful": "Y", "human_faithful": "N",
         "human_note": "Uncited assertion", "judge_unsupported": ""},
        {"case_id": "FN", "judge_faithful": "N", "human_faithful": "y",
         "human_note": "Supported on cited page", "judge_unsupported": "Claim A"},
        {"case_id": "PENDING", "judge_faithful": "Y", "human_faithful": "  "},
    ])
    original = path.read_bytes()

    result = agreement(path)

    assert (result["n_total"], result["n_labelled"], result["n_unlabelled"]) == (5, 4, 1)
    assert result["agreement"] == 0.5
    assert result["confusion_matrix"] == {"tp": 1, "tn": 1, "fp": 1, "fn": 1}
    assert result["judge_false_pass_count"] == 1
    assert result["disagreements"] == [
        {"case_id": "FP", "judge_faithful": "Y", "human_faithful": "N",
         "human_note": "Uncited assertion", "judge_unsupported": ""},
        {"case_id": "FN", "judge_faithful": "N", "human_faithful": "Y",
         "human_note": "Supported on cited page", "judge_unsupported": "Claim A"},
    ]
    assert path.read_bytes() == original


def test_rates_distinguish_false_pass_among_human_failures_from_judge_passes(tmp_path):
    pairs = [("Y", "Y"), ("Y", "Y"), ("N", "N"), ("Y", "N"), ("N", "Y")]
    path = write_sheet(tmp_path, [
        {"case_id": str(i), "judge_faithful": judge, "human_faithful": human}
        for i, (judge, human) in enumerate(pairs)
    ])

    result = agreement(path)

    expected = {"agreement": (3, 5, 0.6), "judge_false_pass_rate": (1, 2, 0.5),
                "judge_false_fail_rate": (1, 3, 0.333), "judge_pass_error_rate": (1, 3, 0.333)}
    for name, (numerator, denominator, value) in expected.items():
        rate = result["rates"][name]
        assert (rate["numerator"], rate["denominator"], rate["value"]) == (numerator, denominator, value)
        assert rate["definition"]


@pytest.mark.parametrize("rows", [[], [{"case_id": "P", "judge_faithful": "Y", "human_faithful": ""}]])
def test_no_human_labels_are_pending_not_success(tmp_path, rows):
    result = agreement(write_sheet(tmp_path, rows))

    assert result["n_labelled"] == 0
    assert result["n_unlabelled"] == result["n_total"] == len(rows)
    assert result["agreement"] is None
    assert result["confusion_matrix"] == {"tp": 0, "tn": 0, "fp": 0, "fn": 0}
    assert result["judge_false_pass_count"] == 0
    assert result["disagreements"] == []
    assert all(rate["value"] is None and rate["denominator"] == 0 for rate in result["rates"].values())


def test_absent_negative_class_has_undefined_false_pass_rate(tmp_path):
    result = agreement(write_sheet(tmp_path, [{"case_id": "P", "judge_faithful": "Y", "human_faithful": "Y"}]))

    assert result["agreement"] == 1.0
    assert result["rates"]["judge_false_pass_rate"]["value"] is None
    assert result["rates"]["judge_false_pass_rate"]["denominator"] == 0


@pytest.mark.parametrize("field,value", [("human_faithful", "yes"), ("human_faithful", "pending"),
                                        ("judge_faithful", "true"), ("judge_faithful", "")])
def test_invalid_labels_fail_with_case_context_without_changing_file(tmp_path, field, value):
    row = {"case_id": "BAD01", "judge_faithful": "Y", "human_faithful": "N"}
    row[field] = value
    path = write_sheet(tmp_path, [row])
    original = path.read_bytes()

    with pytest.raises(ValueError, match=rf"BAD01.*{field}"):
        agreement(path)

    assert path.read_bytes() == original
