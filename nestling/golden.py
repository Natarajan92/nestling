"""Golden dataset: the frozen eval set every experiment runs against.

The file is frozen (plan §9.3, constitution): `load()` refuses to return cases if the
file's content no longer matches the recorded SHA-256. The hash is taken after dropping
the BOM and normalizing line endings, so a Windows (CRLF) and a Linux (LF) checkout agree.
New cases go in a new version file with its own hash; never edit a frozen one.

    uv run python -m nestling.golden upload   # create the LangSmith dataset (idempotent)
"""

import csv
import hashlib
import io
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATASET_VERSION = "golden_v3"
PATH = ROOT / "evals" / "golden_v3.csv"
SHA256 = "8075c270caa94751047580136d7588ba1d49a51fb9a194688c54be92fc387012"  # normalized content
FROZEN_ON = "2026-11-02"
LANGSMITH_DATASET = "nestling-golden-v3"
_ID_NAMESPACE = uuid.UUID("7b0e8a52-3f0e-4c8e-9a51-6e57e1c0a2b4")  # stable example IDs


def load() -> list[dict]:
    """The frozen cases as dicts. Raises if the file has changed since it was frozen."""
    text = PATH.read_bytes().decode("utf-8-sig").replace("\r\n", "\n")
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    if digest != SHA256:
        raise RuntimeError(
            f"{PATH.name} changed after it was frozen on {FROZEN_ON} "
            f"(sha256 {digest[:12]}... != {SHA256[:12]}...). Put new cases in a new version."
        )
    return list(csv.DictReader(io.StringIO(text)))


def _split(value: str) -> list[str]:
    return [v for v in value.split("|") if v]


def to_example(case: dict) -> dict:
    """One case as a LangSmith example: what the app sees, what it should do, and labels."""
    return {
        "id": uuid.uuid5(_ID_NAMESPACE, f"{DATASET_VERSION}:{case['case_id']}"),
        "inputs": {
            "question": case["input"],
            "week": int(case["week"]) if case["week"] else None,
            "diet": case["diet"] or None,
            "tradition": case["tradition"] or None,
            "parent_role": case["parent_role"],
            "life_stage": case["life_stage"],
            "requires_context": case["requires_context"] or None,
        },
        "outputs": {
            "expected_escalate": case["expected_escalate"] == "Y",
            "expected_route": _split(case["expected_route"]),
            "expected_refusal": case["expected_refusal"] == "Y",
            "must_cite_source_ids": _split(case["must_cite_source_ids"]),
            "expected_behavior": case["expected_behavior"],
            "must_include": case["must_include"],
            "must_avoid": case["must_avoid"],
        },
        "metadata": {
            "case_id": case["case_id"],
            "dataset_version": DATASET_VERSION,
            "dataset_sha256": SHA256,
            "scenario_type": case["scenario_type"],
            "theme": case["theme"],
            "risk_level": case["risk_level"],
            "urgency": case["urgency"],
            "review_status": case["review_status"],
            "source_verification": case["source_verification"],
        },
        "split": case["scenario_type"],
    }


def validate_examples(examples, cases=None) -> None:
    """Reject remote drift, including same-count edits, before any paid request."""
    cases = load() if cases is None else cases
    expected = {c['case_id']: to_example(c) for c in cases}
    rows = list(examples)
    actual = {}
    for row in rows:
        cid = (row.metadata or {}).get('case_id')
        if cid not in expected or cid in actual:
            raise ValueError(f'Remote dataset has missing/foreign/duplicate example: {cid}')
        ref = expected[cid]
        if (str(row.id) != str(ref['id']) or row.inputs != ref['inputs'] or row.outputs != ref['outputs']
                or any((row.metadata or {}).get(k) != v for k, v in ref['metadata'].items())):
            raise ValueError(f'Remote dataset example differs from frozen v3: {cid}')
        actual[cid] = row
    if actual.keys() != expected.keys():
        raise ValueError('Remote dataset does not contain exactly the frozen examples')


def upload(client=None) -> str:
    """Create the LangSmith dataset from the frozen file and tag that version 'frozen'."""
    from langsmith import Client

    client = client or Client()
    cases = load()
    if client.has_dataset(dataset_name=LANGSMITH_DATASET):
        dataset = client.read_dataset(dataset_name=LANGSMITH_DATASET)
        expected_meta = {'dataset_version': DATASET_VERSION, 'dataset_sha256': SHA256, 'n_cases': len(cases)}
        if any((dataset.metadata or {}).get(k) != v for k, v in expected_meta.items()):
            raise ValueError('Remote dataset metadata does not match frozen v3')
        validate_examples(client.list_examples(dataset_id=dataset.id), cases)
        validate_examples(client.list_examples(dataset_id=dataset.id, as_of='frozen'), cases)
        return str(dataset.id)

    dataset = client.create_dataset(
        LANGSMITH_DATASET,
        description=f"Nestling golden set {DATASET_VERSION}: {len(cases)} cases, frozen {FROZEN_ON}, sha256 {SHA256[:12]}",
        metadata={'dataset_version': DATASET_VERSION, 'dataset_sha256': SHA256, 'n_cases': len(cases)},
    )
    client.create_examples(dataset_id=dataset.id, examples=[to_example(c) for c in cases])
    validate_examples(client.list_examples(dataset_id=dataset.id), cases)
    latest = max(client.list_dataset_versions(dataset_id=dataset.id), key=lambda v: v.as_of)
    client.update_dataset_tag(dataset_id=dataset.id, as_of=latest.as_of, tag="frozen")
    validate_examples(client.list_examples(dataset_id=dataset.id, as_of='frozen'), cases)
    return str(dataset.id)


if __name__ == "__main__":
    from dotenv import find_dotenv, load_dotenv

    load_dotenv(find_dotenv(usecwd=True))
    if sys.argv[1:] == ["upload"]:
        print("dataset id:", upload())
    else:
        print(f"{DATASET_VERSION}: {len(load())} cases, sha256 ok")
