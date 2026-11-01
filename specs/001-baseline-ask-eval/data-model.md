# Data Model

**Golden case** (`nestling/golden.py`, frozen): `case_id, scenario_type, input, week, diet,
tradition, parent_role, life_stage, requires_context, expected_escalate (Y/N),
expected_route (pipe list), expected_refusal (Y/N), must_cite_source_ids (pipe list)`, plus
review columns. LangSmith example: `inputs` (question + context), `outputs` (labels),
`metadata.case_id`.

**Retrieved passage** (`retrieval.search`): `id, score, chunk_text, source_id, title, year,
url, page, page_label, section`.

**Baseline answer** (target output; schema in contracts/): `answer, escalate, route,
refused, sources_cited` from the model, plus `retrieved_source_ids, invalid_citations,
unretrieved_citations, provider_refusal, model, latency_ms, tokens_in, tokens_out, cost_inr,
error`.

**Case result** (one row of `baseline_<date>_cases.csv`): `case_id, scenario_type,
expected_escalate, predicted_escalate, escalation_match, expected_route, predicted_route,
route_match, expected_refusal, refused, refusal_match, must_cite, sources_cited,
citation_match (blank if not scored), invalid_citations, correct, latency_ms, cost_inr,
error, trace_url`.

**Run summary** (`baseline_<date>_summary.json`): `run` (dataset version, pipeline version,
prompt version, model, date, experiment name/URL, n cases, n errors) · `metrics` (each:
value, pass bar, passed) · `failures` (missed escalations, wrong refusals, errors: case ID,
scenario type, trace URL).

Rules: route ∈ {care, nourish, ready, money, celebrate, journal, guardian, out_of_scope,
clarify}; an error row scores false on every metric; no personal data in any field.
