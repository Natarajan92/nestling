"""Offline human review of actual v3 outputs. Never calls an API or fills labels automatically.

    uv run python -m evals.label_calibration
    uv run python -m evals.label_calibration --report
"""

import argparse
import csv
import json
import os
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT = ROOT / 'evals/results/golden_v3/human_review.csv'


def read_rows(path):
    with Path(path).open(encoding='utf-8-sig', newline='') as handle:
        rows = list(csv.DictReader(handle))
    ids = [row['case_id'] for row in rows]
    if not ids or len(set(ids)) != len(ids):
        raise ValueError('Human review packet needs unique nonempty case IDs')
    for row in rows:
        for field in ('judge_faithful', 'judge_task_fulfilled', 'human_faithful', 'human_task_fulfilled'):
            if row[field].strip().upper() not in ('', 'Y', 'N'):
                raise ValueError(f"{row['case_id']}: invalid {field}; use Y/N or leave blank")
    return rows


def save_rows(path, rows):
    path = Path(path)
    temp = path.with_suffix('.csv.tmp')
    with temp.open('w', encoding='utf-8', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    os.replace(temp, path)


def comparison(rows, human, predicted):
    counts = {'tp': 0, 'tn': 0, 'fp': 0, 'fn': 0}
    disagreements = []
    for row in rows:
        actual, model = row[human].strip().upper(), row[predicted].strip().upper()
        if not actual or not model:
            continue
        category = {('Y', 'Y'): 'tp', ('N', 'N'): 'tn', ('N', 'Y'): 'fp', ('Y', 'N'): 'fn'}[(actual, model)]
        counts[category] += 1
        if actual != model:
            disagreements.append({'case_id': row['case_id'], 'human': actual, 'judge': model,
                                  'note': row.get('human_note', '')})
    n = sum(counts.values())
    return {'n_labelled': n, 'n_total': len(rows),
            'agreement': (counts['tp'] + counts['tn']) / n if n else None,
            'confusion_matrix': counts, 'judge_false_passes': counts['fp'],
            'disagreements': disagreements, 'status': 'pending human labels' if not n else 'human-labelled sample only'}


def report(path=DEFAULT):
    rows = read_rows(path)
    return {'faithfulness': comparison(rows, 'human_faithful', 'judge_faithful'),
            'task_fulfillment': comparison(rows, 'human_task_fulfilled', 'judge_task_fulfilled'),
            'limits': 'Purposive calibration sample; agreement is not clinical validation or unbiased population accuracy.'}


def evidence(row, directory):
    round_name = row['round']
    if round_name not in ('baseline', 'round1', 'round2', 'round3', 'final'):
        raise ValueError('Unknown review round')
    cp = json.loads((Path(directory) / round_name / 'checkpoint.json').read_text(encoding='utf-8'))
    from nestling import golden
    if cp.get('dataset_version') != golden.DATASET_VERSION or cp.get('dataset_hash') != golden.SHA256:
        raise ValueError('Review evidence does not match the frozen dataset')
    saved = cp['cases'][row['case_id']]
    if saved['output']['answer'] != row['answer']:
        raise ValueError('Review answer differs from its original checkpoint')
    return saved['judge_passages']


def ask_label(prompt, input_fn=input):
    while True:
        value = input_fn(prompt).strip().upper()
        if value in ('Y', 'N', 'S', 'SKIP', ''):
            return value if value in ('Y', 'N') else ''
        print('Enter Y, N or skip. No label is assumed.')


def review(path=DEFAULT, *, input_fn=input, output=print):
    path = Path(path)
    rows = read_rows(path)
    reviewer = input_fn('Reviewer name/role (kept in this local CSV): ').strip()
    reviewed_on = input_fn('Actual review date YYYY-MM-DD: ').strip()
    if not reviewer:
        raise ValueError('Reviewer identity is required for entered human labels')
    date.fromisoformat(reviewed_on)
    try:
        for index, row in enumerate(rows, 1):
            if row['human_faithful'] and row['human_task_fulfilled']:
                continue  # preserve completed human work
            output(f"\n{index}/{len(rows)} {row['case_id']} ({row['agent']})\nQuestion: {row['question']}\nAnswer: {row['answer']}")
            output(f"Expected: {row['expected_behavior']}\nRequired: {row['must_include']}\nAvoid: {row['must_avoid']}")
            for passage in evidence(row, path.parent):
                output(f"\n[{passage['source_id']}, page {passage.get('page_label')}]\n{passage['text']}")
            # Judge predictions/reasons deliberately remain hidden until after human input.
            previous = (row['human_faithful'], row['human_task_fulfilled'])
            for column, question in [('human_faithful', 'Every factual claim supported by the passages? Y/N/skip: '),
                                     ('human_task_fulfilled', 'Expected task fulfilled, with correct visible citations? Y/N/skip: ')]:
                if not row[column]:
                    row[column] = ask_label(question, input_fn)
            if previous != (row['human_faithful'], row['human_task_fulfilled']):
                note = input_fn('Your reason / disagreement note (Enter preserves an existing note): ').strip()
                if note:
                    row['human_note'] = note
                row['reviewer'], row['reviewed_on'] = reviewer, reviewed_on
                save_rows(path, rows)
            output(f"Judge after your input: faithful={row['judge_faithful']}, task={row['judge_task_fulfilled']}\n{row['judge_reason']}")
    except (KeyboardInterrupt, EOFError):
        output('\nStopped; previously entered labels are saved. Unreviewed fields stay blank.')
    return report(path)


if __name__ == '__main__':
    import sys
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--path', type=Path, default=DEFAULT)
    parser.add_argument('--report', action='store_true', help='Read-only statistics; no model calls')
    args = parser.parse_args()
    print(json.dumps(report(args.path) if args.report else review(args.path), indent=2))
