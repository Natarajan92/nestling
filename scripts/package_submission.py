"""Package saved Week 4 evidence offline; never calls providers or deploys.

Run after reports, plots, PDF, executed notebook and QA have been refreshed:
    uv run python scripts/package_submission.py
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output/submission"
RESULTS = ROOT / "evals/results/golden_v3"


def build() -> Path:
    from evals.v3_run import JUDGE_SCHEMA, JUDGE_SYSTEM, JUDGE_VERSION
    from evals.label_calibration import report as calibration_report
    from nestling import golden

    golden.load()
    files = [ROOT / "README.md", ROOT / "pyproject.toml", ROOT / "uv.lock",
             ROOT / ".env.example", ROOT / "render.yaml",
             ROOT / "evals/golden_v3.csv", ROOT / "evals/golden_v3.freeze.json",
             ROOT / "evals/golden_v3.submission40.json",
             ROOT / "notebooks/09_v3_evaluation.ipynb",
             ROOT / "output/pdf/Nestling_Week4_Submission.pdf"]
    files += [ROOT / "docs" / name for name in (
        "week4_report.md", "v3_evaluation_report.md", "SUBMISSION.md",
        "engineering_notes.md", "loom_script.md", "deploy_checklist.md",
        "submission_finish_prompt.md", "NESTLING_PLAN.md", "github_cleanup.md")]
    files += sorted((ROOT / "docs/media").glob("*.png"))
    files += sorted((ROOT / "nestling").rglob("*.py"))
    files += sorted((ROOT / "scripts").glob("*.py"))
    files += [ROOT / "evals" / name for name in (
        "v3_run.py", "v3_compare.py", "evaluators.py", "judge.py", "judge_prompt.md",
        "budgeted_run.py", "plot_tradeoff.py", "label_calibration.py")]
    files += sorted((ROOT / "playbooks").glob("*.yaml"))
    files += [ROOT / "sources/registry.yaml"]
    files += [p for p in RESULTS.iterdir() if p.is_file() and p.suffix in (".csv", ".json")]
    for name in ("baseline", "round1", "round2", "round3"):
        folder = RESULTS / name
        summary = json.loads((folder / "summary.json").read_text(encoding="utf-8"))
        if not summary["progress"]["complete"] or summary["progress"]["n_trace_verified"] != 62:
            raise ValueError(f"Incomplete/unverified evidence: {name}")
        files += [p for p in folder.iterdir() if p.is_file() and p.suffix in (".csv", ".json")
                  and p.name not in ("checkpoint.json", "calibration.csv")]
    files += sorted((RESULTS / "qa").glob("*"))
    files = sorted(set(files))
    for path in files:
        if not path.is_file() or not path.is_relative_to(ROOT):
            raise ValueError(f"Missing/invalid submission input: {path}")
    notebook = json.loads((ROOT / "notebooks/09_v3_evaluation.ipynb").read_text(encoding="utf-8"))
    code = [cell for cell in notebook["cells"] if cell["cell_type"] == "code"]
    if not code or any(cell.get("execution_count") is None for cell in code):
        raise ValueError("Submission notebook must be executed")
    OUT.mkdir(parents=True, exist_ok=True)
    calibration = calibration_report(RESULTS / "human_review.csv")
    pending = []
    if any(calibration[key]["n_labelled"] < calibration[key]["n_total"]
           for key in ("faithfulness", "task_fulfillment")):
        pending.append("Owner's actual-output calibration (20 cases)")
    report_text = (ROOT / "docs/week4_report.md").read_text(encoding="utf-8")
    loom = re.search(r"^\*\*Loom:\*\*\s*(.*)$", report_text, re.MULTILINE)
    if not loom or not re.search(r"https?://", loom.group(1)):
        pending.append("Owner's Loom recording/link")
    manifest = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "dataset_version": golden.DATASET_VERSION, "dataset_sha256": golden.SHA256,
        "selected_round": "round1", "completed_rejected_rounds": ["round2", "round3"],
        "pending": pending,
        "excluded": ["Secrets and personal data", "Full copyrighted source passages/checkpoints",
                     "Private Git backups", "Lesson media (separate approved local render files)"],
        "files": [{"path": p.relative_to(ROOT).as_posix(), "bytes": p.stat().st_size,
                   "sha256": hashlib.sha256(p.read_bytes()).hexdigest()} for p in files],
    }
    target = OUT / "Nestling_Week4_Submission.zip"
    with ZipFile(target, "w", ZIP_DEFLATED) as archive:
        for path in files:
            archive.write(path, path.relative_to(ROOT).as_posix())
        archive.writestr("judge_protocol.json", json.dumps({
            "judge_version": JUDGE_VERSION, "system_prompt": JUDGE_SYSTEM,
            "response_schema": JUDGE_SCHEMA}, indent=2))
        archive.writestr("manifest.json", json.dumps(manifest, indent=2))
        archive.writestr("START_HERE.txt", (
            "Read output/pdf/Nestling_Week4_Submission.pdf and docs/week4_report.md.\n"
            "All four complete runs are included; Round 1 is retained.\n"
            f"Pending: {', '.join(pending) if pending else 'No missing owner calibration or Loom link'}.\n"
            "Case CSVs contain answers/scores/trace links. Private LangSmith access may be needed.\n"
            "No secrets, personal data, source PDFs or private review checkpoints are included.\n"
            "This is an evidence pack with evaluation code, not a full application checkout.\n"
            "Complete app source: https://github.com/Natarajan92/nestling (private access required).\n"))
    with ZipFile(target) as archive:
        if archive.testzip() is not None:
            raise ValueError("ZIP integrity check failed")
        for item in manifest["files"]:
            if hashlib.sha256(archive.read(item["path"])).hexdigest() != item["sha256"]:
                raise ValueError(f"Packaged hash mismatch: {item['path']}")
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Verified {len(files)} inputs: {target}")
    return target


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(ROOT))
    build()
