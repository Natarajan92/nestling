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

### 3:25 - 4:30  -  Results, including rejected latency candidates

Screen: [v3 report](v3_evaluation_report.md); compare the full-62 table, paired denominators and saved decisions. All seven runs completed 62 answers with 62 verified traces and zero pipeline/judge errors. Read the selected row aloud and keep every rejected row visible.

| Run / decision | Faithful / valid judgments | Task complete | p95 seconds | Mean pipeline INR |
| --- | ---: | ---: | ---: | ---: |
| Baseline / reference | 29/35 | 47/62 | 22.55 | 0.681 |
| Round 1 / keep, selected | 32/35 | 52/62 | 12.11 | 0.719 |
| Round 2 / reject | 30/33 | 48/62 | 9.23 | 0.590 |
| Round 3 / reject | 28/31 | 47/62 | 11.89 | 0.753 |
| Latency 1 / reject | 35/37 | 55/62 | 13.10 | 0.710 |
| Latency 2 / reject | 33/37 | 52/62 | 11.19 | 0.703 |
| Latency 3 / reject | 32/36 | 52/62 | 11.24 | 0.737 |

Say: "Round 1's citation repair remains selected: paired faithfulness improves 27/33 to 30/33 against baseline, and task completion rises 47/62 to 52/62. The short prompt and compact verifier were rejected. The first latency candidate improved paired support 31/34 to 32/34 but worsened p95 to 13.10 seconds. Warm direct FAST reached 11.19 seconds, and warm low FAST 11.24, but their faithfulness fell below 90%, with paired support 31/34 to 30/34 and 29/32 to 28/32. Faster alone did not satisfy the gates."

Unpaired fractions use different eligible denominators. The `none` and `low` compatibility probes used separate batches/provider conditions; do not present their means as a direct comparison or as pipeline p95. MAIN reasoning was not changed, and its hidden-reasoning contribution cannot be determined from saved aggregate tokens/durations.

Say: "Original request accounting remains INR183.9041. The separate approved INR160 latency campaign accounted for INR146.6423, making combined accounting INR330.5464, with zero pending reservations. These are Nebius token estimates at a fixed comparison exchange rate, excluding hosting and Pinecone charges; pipeline means also exclude offline judging and discarded attempts."

### 4:30 - 5:00  -  Honest close

Say: "Selected Round 1 reaches 32/35, or 91.4%, faithfulness, but p95 remains 12.11 seconds against the eight-second target. Human calibration is still 0/20. This previously exposed regression set is not an unseen holdout or clinical validation; B11's missing-policy expectation remains a label limitation."

Show the fresh QA summary: 39 web tests passed, 25 routes returned HTTP 200, and all 12 videos plus 12 thumbnails returned nonempty bytes. Route checks cover HTTP/server rendering; interaction coverage comes from web tests and prior UI evidence. The final post-patch Python suite passed 470 tests with one existing warning; show its saved XML. Real-device microphone/native sharing and public deployment remain separate work.

End on the actual report and human calibration sheet. The optional API-only startup warmup is default off; its five-second wait does not establish a new R1 request-p95 result. Keep the recording under five minutes; link the finished Loom only after checking playback and access. The recording/link remains pending until the owner supplies it.
