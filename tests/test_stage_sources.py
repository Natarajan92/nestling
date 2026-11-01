from nestling import agents, graph, retrieval


def test_pregnancy_skips_infant_and_newborn_sources():
    full = retrieval.sources_for("nourish")
    staged = retrieval.sources_for("nourish", "pregnancy")
    assert "MOHFW-IYCF" in full and "MOHFW-IYCF" not in staged and "ICMR-NIN-DG" in staged
    care = retrieval.sources_for("care", "pregnancy")
    assert {"WHO-ANC", "MOHFW-ANC"} <= set(care) and not (retrieval.STAGE_EXCLUDE["pregnancy"] & set(care))


def test_postpartum_skips_pregnancy_only_sources_and_keeps_newborn_ones():
    care = retrieval.sources_for("care", "postpartum")
    assert "WHO-ANC-ULTRASOUND" not in care and {"WHO-POSTNATAL", "INDIA-UIP"} <= set(care)


def test_unknown_or_missing_stage_changes_nothing():
    for stage in (None, "general", ""):
        assert retrieval.sources_for("care", stage) == retrieval.sources_for("care")


def test_every_excluded_id_is_a_registry_source():
    registry = retrieval.load_registry()
    assert all(i in registry for ids in retrieval.STAGE_EXCLUDE.values() for i in ids)


def test_only_staged_mode_uses_the_life_stage(monkeypatch):
    seen = []
    monkeypatch.setattr(retrieval, "search_reranked", lambda q, source_ids=None, **k: seen.append(source_ids) or [])
    ctx = {"life_stage": "pregnancy", "week": 20}
    agents.retrieve("q", ctx, "nourish", "reranked")
    agents.retrieve("q", ctx, "nourish", "staged")
    assert "MOHFW-IYCF" in seen[0] and "MOHFW-IYCF" not in seen[1]


def test_v7_adds_staged_retrieval_and_v1_to_v6_are_unchanged():
    assert graph.VERSIONS["v7"] == {**graph.VERSIONS["v6"], "retrieval": "staged"}
    assert graph.VERSIONS["v6"]["retrieval"] == "reranked" and graph.VERSIONS["v5"]["retrieval"] == "reranked"
    assert graph.PROMPT_VERSIONS["v7"] not in {graph.PROMPT_VERSIONS[v] for v in ("v1", "v2", "v3", "v4", "v5", "v6")}
