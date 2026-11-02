"""Render current v3 figures from completed, saved full-set summaries only.

Reproduce without changing the application environment:
    uv run --with matplotlib python -m evals.plot_tradeoff

No provider calls, remote reads, historical benchmark files or subset results are used.
"""

import argparse
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "evals" / "results" / "golden_v3"
MEDIA = ROOT / "docs" / "media"
CREAM, INK, GRID = "#FFF8F1", "#2E2A3A", "#E7DCD2"
COLORS = ("#EAA582", "#86A88A", "#CE94A3", "#CAA353", "#8B9EB8")
ORDER = {"baseline": 0, "round1": 1, "round2": 2, "round3": 3,
         "latency1": 4, "latency2": 5, "latency3": 6, "final": 7}


def _number(value, label, *, share=False):
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"Invalid numeric {label}: {value!r}")
    if value < 0 or (share and value > 1):
        raise ValueError(f"Out-of-range {label}: {value!r}")
    return value


def load_completed(results=RESULTS):
    """Exclude unfinished rounds and reject different data/protocols or subset summaries."""
    frozen = json.loads((ROOT / "evals" / "golden_v3.freeze.json").read_text(encoding="utf-8"))
    rows = []
    for path in sorted(results.glob("*/summary.json"), key=lambda p: (ORDER.get(p.parent.name, 99), p.parent.name)):
        summary = json.loads(path.read_text(encoding="utf-8"))
        if summary.get("progress", {}).get("complete") is not True:
            continue
        run, progress, judging = summary["run"], summary["progress"], summary["judging"]
        if (run.get("dataset_version") != "golden_v3" or
                run.get("dataset_hash") != frozen["normalized_sha256"] or
                run.get("n_cases") != frozen["n_cases"] or
                progress.get("n_expected") != frozen["n_cases"] or
                progress.get("n_done") != frozen["n_cases"] or progress.get("n_errors") != 0):
            raise ValueError(f"Completed summary is not the frozen full v3 evaluation: {path}")
        name = run["round_name"]
        if name != path.parent.name:
            raise ValueError(f"Round name differs from its artifact directory: {path}")
        metric = summary["metrics"]
        faith = _number(judging.get("faithfulness"), "faithfulness", share=True)
        latency = _number(metric["p95_latency_s"]["value"], "p95 latency")
        cost = _number(metric["mean_cost_inr"]["value"], "mean cost")
        if latency is None or cost is None:
            raise ValueError(f"Completed round has no measured latency/cost: {path}")
        n_judged = judging["n_faithfulness_valid"]
        if (faith is None) != (n_judged == 0):
            raise ValueError(f"Faithfulness value/denominator disagree: {path}")
        decision_path = path.parent / "decision.json"
        decision = json.loads(decision_path.read_text(encoding="utf-8")) if decision_path.exists() else {}
        rows.append({"name": name, "label": "Baseline" if name == "baseline" else name.replace("round", "Round ").title(),
            "summary": summary, "faith": faith, "n_judged": n_judged,
            "n_eligible": judging["n_faithfulness_eligible"], "judge_errors": judging["n_faithfulness_errors"],
            "zero_claim": judging["n_zero_claim"],
            "decision": decision.get("decision"),
            "decision_sha256": hashlib.sha256(decision_path.read_bytes()).hexdigest() if decision_path.exists() else None,
            "latency": latency, "cost": cost, "path": path,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
    if not rows:
        raise ValueError("No completed full-set golden_v3 summaries; no figures generated")
    protocols = {(r["summary"]["run"].get("judge_version"), r["summary"]["judging"].get("judge_version")) for r in rows}
    if len(protocols) != 1:
        raise ValueError("Judge protocols differ; these round headlines cannot share a comparison plot")
    retained = next((r["name"] for r in reversed(rows) if r["decision"] == "keep"), None)
    for row in rows:
        row["retained"] = row["name"] == retained
        row["rejected"] = row["decision"] == "reject"
        if row["retained"]:
            row["label"] += " · retained"
        elif row["rejected"]:
            row["label"] += " · rejected"
    return rows


def _fraction(value, denominator):
    return "N/A" if value is None else f"{round(value * denominator)}/{denominator}"


def _style(plt):
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "text.color": INK,
        "axes.labelcolor": INK, "xtick.color": INK, "ytick.color": INK,
        "figure.facecolor": CREAM, "axes.facecolor": CREAM, "savefig.facecolor": CREAM,
        "axes.edgecolor": GRID, "axes.spines.top": False, "axes.spines.right": False,
        "grid.color": GRID, "grid.linewidth": .7, "axes.axisbelow": True})


def _footer(fig, lines):
    for i, line in enumerate(lines):
        fig.text(.075, .155 - i * .031, line, fontsize=8.4, color="#685F68")


def _save(fig, path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    sources = [{"round": r["name"], "summary": r["path"].relative_to(ROOT).as_posix()
                if r["path"].is_relative_to(ROOT) else str(r["path"]), "sha256": r["sha256"],
                "decision": r["decision"], "decision_sha256": r["decision_sha256"]} for r in rows]
    fig.savefig(path, dpi=180, metadata={"Description": json.dumps({"dataset": "golden_v3", "sources": sources})})


def tradeoff(rows, output, plt):
    from matplotlib.patches import Rectangle

    fig = plt.figure(figsize=(11.4, 7.1))
    fig.text(.075, .94, "Quality, latency and cost", fontsize=23, fontweight="bold")
    n_cases = rows[0]["summary"]["run"]["n_cases"]
    fig.text(.075, .895, f"Nestling · full {n_cases}-case regression set · completed rounds only", fontsize=11)
    ax = fig.add_axes([.075, .27, .57, .54])
    right = fig.add_axes([.69, .27, .29, .54])
    right.axis("off")
    xmax = max(12, max(r["latency"] for r in rows) * 1.18)
    ax.set(xlim=(0, xmax), ylim=(0, 105), xlabel="p95 answer latency (seconds)", ylabel="Faithfulness (%)")
    ax.grid(True, alpha=.7)
    ax.add_patch(Rectangle((0, 90), 8, 10, color="#E3ECDE", zorder=0))
    ax.axhline(90, color="#65846A", linestyle="--", linewidth=1.2)
    ax.axvline(8, color="#65846A", linestyle="--", linewidth=1.2)
    ax.text(.985, 91.5, "Faithfulness target ≥90%", transform=ax.get_yaxis_transform(),
            ha="right", va="bottom", fontsize=8.5, color="#54705A")
    ax.text(8.35, 5, "Latency target <8s", fontsize=8.5, color="#54705A", rotation=90, va="bottom")
    for i, row in enumerate(rows):
        color = COLORS[i % len(COLORS)]
        if row["faith"] is not None:
            ax.scatter(row["latency"], row["faith"] * 100, s=row["cost"] * 1400,
                       facecolors="none" if row["rejected"] else color,
                       edgecolors=color if row["rejected"] else INK,
                       linewidths=2 if row["rejected"] or row["retained"] else .9,
                       alpha=.95, zorder=6 if row["retained"] else 4)
        top = .98 - i * .205
        right.scatter([.025], [top - .018], s=110, facecolors="none" if row["rejected"] else color,
                      edgecolors=color if row["rejected"] else INK, linewidths=1.5 if row["rejected"] else .6)
        right.text(.1, top, row["label"], fontweight="bold", fontsize=11, va="top")
        quality = "N/A" if row["faith"] is None else f"{row['faith']:.1%} · {_fraction(row['faith'], row['n_judged'])} judgments"
        right.text(.1, top - .06, quality, fontsize=9, va="top")
        right.text(.1, top - .11, f"p95 {row['latency']:.2f}s · mean INR {row['cost']:.3f}", fontsize=9, va="top")
        right.text(.1, top - .16, f"{row['n_judged']}/{row['n_eligible']} valid/eligible · {row['judge_errors']} errors · {row['zero_claim']} zero-claim",
                   fontsize=8.2, color="#685F68", va="top")
    right.set(xlim=(0, 1), ylim=(0, 1))
    _footer(fig, ["Bubble area is proportional to mean pipeline cost in INR; judge and retry spend is tracked separately.",
        "Faithfulness uses each round's valid eligible subset; zero-claim replies and judge errors are excluded and reported.",
        "Retained rounds are labeled; rejected candidates use hollow markers. Use paired comparisons for selection.",
        "Source: evals/results/golden_v3/<round>/summary.json · frozen dataset, previously exposed cases."])
    _save(fig, output / "tradeoff.png", rows)
    plt.close(fig)


def metrics(rows, output, plt):
    fig = plt.figure(figsize=(11.4, 7.1))
    fig.text(.075, .94, "Safety and answer quality", fontsize=23, fontweight="bold")
    n_cases = rows[0]["summary"]["run"]["n_cases"]
    fig.text(.075, .895, f"Nestling · full {n_cases}-case regression set · numerator / denominator shown", fontsize=11)
    ax = fig.add_axes([.075, .29, .89, .49])
    ax.set(ylim=(0, 118), ylabel="Correct / faithful (%)")
    ax.set_xticks(range(4), ["Escalation\nrecall", "Refusal\naccuracy", "Routing\naccuracy", "Faithfulness"])
    ax.grid(axis="y", alpha=.7)
    width = .76 / len(rows)
    for i, row in enumerate(rows):
        summary = row["summary"]
        values = [(summary["metrics"][key]["value"], summary["metrics"][key]["n"]) for key in
                  ("escalation_recall", "refusal_accuracy", "routing_accuracy")]
        values.append((row["faith"], row["n_judged"]))
        positions = [x - .38 + width * (i + .5) for x in range(4)]
        ax.bar(positions, [v * 100 if v is not None else 0 for v, _ in values], width=width * .9,
               color=COLORS[i % len(COLORS)], edgecolor=INK, linewidth=1.1 if row["retained"] else .65,
               hatch="//" if row["rejected"] else None, alpha=.6 if row["rejected"] else 1,
               label=row["label"], zorder=3)
        for x, (value, denominator) in zip(positions, values):
            label = f"{value:.1%}\n{_fraction(value, denominator)}" if value is not None else "N/A\n0 judged"
            ax.text(x, (value * 100 if value is not None else 0) + 2, label, ha="center", va="bottom",
                    fontsize=9 if len(rows) <= 2 else 7.1, linespacing=1.3, zorder=5,
                    bbox={"facecolor": CREAM, "edgecolor": "none", "pad": 1.5})
    for x, target in enumerate((100, 100, 90, 90)):
        ax.plot([x - .43, x + .43], [target, target], color="#54705A", linestyle="--", linewidth=1.2, zorder=4)
    ax.legend(loc="upper left", bbox_to_anchor=(0, 1.17), ncol=min(len(rows), 5), frameon=False)
    _footer(fig, ["Dashed targets: escalation and refusal 100%; routing and faithfulness ≥90%.",
        "Faithfulness denominators exclude judge errors and zero-claim replies; eligibility can differ between rounds.",
        "Retained rounds are labeled; rejected candidates are hatched. Headline bars are not paired gains.",
        f"Source: evals/results/golden_v3/<round>/summary.json · {n_cases} primary cases; presentation subset excluded."])
    _save(fig, output / "metrics_by_version.png", rows)
    plt.close(fig)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, default=RESULTS)
    parser.add_argument("--output", type=Path, default=MEDIA)
    args = parser.parse_args(argv)
    rows = load_completed(args.results)
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    _style(plt)
    tradeoff(rows, args.output, plt)
    metrics(rows, args.output, plt)
    print(json.dumps({"dataset": "golden_v3", "n_primary_cases": rows[0]["summary"]["run"]["n_cases"],
        "completed_rounds": [{"round": r["name"], "faithfulness": r["faith"], "n_valid": r["n_judged"],
            "p95_latency_s": r["latency"], "mean_cost_inr": r["cost"]} for r in rows],
        "figures": [str(args.output / "tradeoff.png"), str(args.output / "metrics_by_version.png")]}, indent=2))


if __name__ == "__main__":
    main()
