# Five-minute demo script

Target: owner review by **10:00 AM IST, 2 November 2026**; official submission target **12:00 PM IST**. Record only the actual verified state. This script does not authorize deployment or more paid evaluation.

Before recording, open `http://localhost:3000`, API health at `http://localhost:8010/api/health`, the [v3 report](v3_evaluation_report.md), and the H07 trace below. Use a synthetic demo profile and hide terminals containing credentials. Prepare the video tab before recording.

Start the API from the repository root:

```powershell
uv run uvicorn api.main:app --host 127.0.0.1 --port 8010
```

Start the web app in a separate terminal:

```powershell
cd web
$env:NEXT_PUBLIC_API_URL = "http://localhost:8010"
npm.cmd run dev -- --port 3000
```

### 0:00–0:35 · Today: the parent experience

Screen: `/welcome`, then `/`. Choose a synthetic pregnancy profile, vegetarian diet, Tamil tradition and consent. Show the week ring, sourced daily tip and journeys.

Say: “Nestling helps first-time parents in India navigate pregnancy and the first weeks with their baby. The experience is personal; health, diet and insurance answers must identify their trusted source.”

### 0:35–1:10 · Guardian: code decides escalation

Screen: Ask sheet. Exact question: **“Swollen feet and headache since morning”** (K01).

Show the red Guardian response, source chip and “How I answered.” Say: “This danger-sign rule runs in code before model routing. For this directly matched case, the pipeline skips model calls and sends the parent to medical care.” In its saved evaluation trace, show `model=rules`, zero tokens and zero pipeline cost; do not confuse the separately billed offline judge with the response itself.

### 1:10–1:55 · A reviewed Little Lesson

Screen: `/lessons`, before-birth filter, `/lessons/prenatal_yoga_preparation`. Play a few seconds; show source chips, safety cards and review date. Exact optional Ask question: **“How do I prepare for a prenatal yoga class?”**

Backup screen: `/lessons/burping`; exact question **“How do I burp my baby?”** Use direct library navigation if avoiding another live model request.

Say: “These instructions are prepared from registered sources, reviewed scene by scene, and served only when that exact storyboard version is approved and its media exists. A model score cannot approve a lesson.”

### 1:55–2:30 · The frozen dataset and evaluation contract

Screen: `evals/golden_v3.freeze.json`, then `evals/results/golden_v3/submission40_questions.csv` and the report.

Say: “All 62 shortlisted questions are owner-attested as the owner's own and reviewed. Authorship is self-attested, not independently certified. Their questions and labels were frozen before these measurements. The 40-case presentation view uses 20 happy, 12 edge, 6 known-fail and 2 adversarial cases, selected without scores. All 62 remain the regression gate.”

### 2:30–3:25 · H07: trace a failure to a code cause

Exact question: **“Which iron-rich foods can I eat as a vegetarian?”** Context: pregnancy, week 24.

Open [the baseline H07 trace](https://smith.langchain.com/o/20d8f2fd-49d5-4daa-be0a-340ae1552592/projects/p/122b1a9c-81b7-4ee4-9408-3e1d05498c0a/r/3cc681e6-6164-4eec-a2b3-4ca97d8669c8?poll=true), specialist child, then verifier child. Show [the saved diagnosis](../evals/results/golden_v3/round1/diagnosis.json).

Say: “The specialist returned ICMR and WHO citations. A citation regex matched a suffix inside `ICMR-NIN-DG`, damaged seven markers and removed ICMR evidence before verification. The verifier received only WHO evidence and replaced the answer after finding six unsupported claims. Round 1 changes that regex boundary alone. This is a concrete evidence-handling bug; the measured round decides whether the fix improves outcomes.”

### 3:25–4:30 · Results, including regressions

Screen: [v3 report](v3_evaluation_report.md); compare full-62 rows, then the same 40-case view. Use saved completed results only.

Completed baseline on all 62 cases: escalation/refusal **100%**, routing **95.2%**, citation match **69.6%**, faithfulness **29/35 = 82.9%**, task fulfillment **47/62 = 75.8%**, p95 **22.55 seconds**, mean pipeline cost **INR 0.681**. There are 38 faithfulness-eligible replies, three zero-claim answers, six abstentions and no judge errors.

All four runs completed 62 answers with 62 verified traces and no pipeline errors. Read the selected row aloud; show the other rows to make rejected results visible.

| Run / decision | Faithful / valid judgments | Task complete | p95 seconds | Mean pipeline INR |
| --- | ---: | ---: | ---: | ---: |
| Baseline / reference | 29/35 | 47/62 | 22.55 | 0.681 |
| Round 1 / **keep, selected** | 32/35 | 52/62 | 12.11 | 0.719 |
| Round 2 / reject | 30/33 | 48/62 | 9.23 | 0.590 |
| Round 3 / reject | 28/31 | 47/62 | 11.89 | 0.753 |

Say: “The citation repair is retained: paired faithfulness improves 27/33 to 30/33 and task completion 47/62 to 52/62. Routing falls 59/62 to 58/62 and mean cost increases, so this is a measured tradeoff. The 90-word prompt was faster but reduced useful coverage; the compact verifier also failed its quality/cost tradeoff. Both are rejected and preserved. All request accounting is INR 183.9041 of the shared INR 350 cap.” Unpaired fractions in the table use different eligible denominators; show paired comparisons in the report for improvement claims.

### 4:30–5:00 · Honest close

Say: “Selected Round 1 reaches 91.4% faithfulness on 35 valid judgments, but p95 remains 12.11 seconds against the eight-second target. Expected-label review and judging actual answers are separate: human calibration is 0/20. This is a previously exposed regression set, not an unseen holdout. B11's missing-policy citation expectation remains a documented label limitation. Physical-device voice/sharing checks and deployment remain separate work.”

End on the actual current report, the saved calibration sheet and next measured improvement. Keep the recording under five minutes; link the finished Loom only after checking playback and access.
