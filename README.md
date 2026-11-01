# nestling
From bump to baby. Every answer, sourced.

A calm companion for first-time parents in India. Every medical, diet and insurance answer cites a trusted source, and danger signs are sent to a doctor by code-owned rules, not by the AI.

**Evaluation (Week 4, frozen golden set v2, 104 cases)**

| Pipeline | Escalation recall | Refusal | Routing | Citation match | p95 latency | Cost / answer |
|---|---|---|---|---|---|---|
| Baseline (single Sonnet + plain RAG) | 100% | 97.1% | 84.6% | 78.1% | 8.57 s | ₹1.31 |

Plan: [docs/NESTLING_PLAN.md](docs/NESTLING_PLAN.md) · Baseline: [notebooks/01_baseline_ask_agent.ipynb](notebooks/01_baseline_ask_agent.ipynb)
