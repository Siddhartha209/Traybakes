"""
Unit tests for research_agent/json_normaliser.py.

Run with: pytest tests/test_json_normaliser.py -v
"""

from research_agent.json_normaliser import (
    deduplicate_list,
    clean_and_group_evidence,
    link_opportunities_to_gaps,
    normalise_json,
)


class TestDeduplicateList:
    def test_removes_duplicates_by_key(self):
        items = [{"name": "A", "x": 1}, {"name": "A", "x": 2}, {"name": "B", "x": 3}]
        result = deduplicate_list(items, key_fields=["name"])
        assert len(result) == 2
        assert result[0]["name"] == "A"
        assert result[1]["name"] == "B"

    def test_empty_list(self):
        assert deduplicate_list([], key_fields=["name"]) == []


class TestCleanAndGroupEvidence:
    def test_groups_by_competitor_string(self):

        evidence = [
            {"competitor": "Acme", "query": "q1", "title": "T1", "url": "u1", "snippet": "s1"},
            {"competitor": "Acme", "query": "q2", "title": "T2", "url": "u2", "snippet": "s2"},
            {"competitor": "Beta", "query": "q3", "title": "T3", "url": "u3", "snippet": "s3"},
        ]
        result = clean_and_group_evidence(evidence)
        names = {c["name"] for c in result}
        assert names == {"Acme", "Beta"}

        acme = next(c for c in result if c["name"] == "Acme")
        assert len(acme["evidence"]) == 2

    def test_skips_items_with_no_competitor(self):
        evidence = [{"query": "q1", "title": "T1", "url": "u1", "snippet": "s1"}]
        result = clean_and_group_evidence(evidence)
        assert result == []

    def test_empty_evidence(self):
        assert clean_and_group_evidence([]) == []


class TestLinkOpportunitiesToGaps:
    def test_links_by_substring_match(self):
        gaps = [{"name": "Content Gap"}]
        opportunities = [{"name": "Content Gap opportunity", "score": 5}]
        result = link_opportunities_to_gaps(gaps, opportunities)
        assert result[0]["source_gap"] == "Content Gap"

    def test_no_match_leaves_source_gap_unset(self):
        gaps = [{"name": "Content Gap"}]
        opportunities = [{"name": "Totally Unrelated", "score": 5}]
        result = link_opportunities_to_gaps(gaps, opportunities)
        assert "source_gap" not in result[0]

    def test_does_not_mutate_input(self):
        gaps = [{"name": "Content Gap"}]
        opportunities = [{"name": "Content Gap opportunity", "score": 5}]
        link_opportunities_to_gaps(gaps, opportunities)
        assert "source_gap" not in opportunities[0]


class TestNormaliseJson:
    def _base_raw(self, **overrides):
        raw = {
            "goal": "sell flapjacks",
            "competitors": [{"name": "Acme", "reason": "big player"}],
            "evidence": [
                {"competitor": "Acme", "query": "q1", "title": "T1", "url": "u1", "snippet": "s1"},
            ],
            "patterns": [{"name": "Easter Promotions", "description": "desc"}],
            "gaps": [{"name": "Content Gap", "description": "desc", "reason": "r"}],
            "opportunities": [{"name": "Content Gap opportunity", "score": 9.5}],
        }
        raw.update(overrides)
        return raw

    def test_produces_expected_top_level_shape(self):
        result = normalise_json(self._base_raw())
        assert set(result.keys()) == {"goal", "competitors", "insights", "actions"}
        assert set(result["insights"].keys()) == {"patterns", "gaps", "opportunities"}

    def test_patterns_and_gaps_survive_normalisation_when_present(self):

        result = normalise_json(self._base_raw())
        assert len(result["insights"]["patterns"]) == 1
        assert result["insights"]["patterns"][0]["name"] == "Easter Promotions"
        assert len(result["insights"]["gaps"]) == 1
        assert result["insights"]["gaps"][0]["name"] == "Content Gap"

    def test_empty_patterns_and_gaps_produce_empty_insights_not_errors(self):
        result = normalise_json(self._base_raw(patterns=[], gaps=[], opportunities=[]))
        assert result["insights"]["patterns"] == []
        assert result["insights"]["gaps"] == []
        assert result["insights"]["opportunities"] == []
        assert result["actions"]["highest_priority_opportunity"] is None

    def test_top_opportunities_sorted_by_score_desc(self):
        raw = self._base_raw(opportunities=[
            {"name": "Low", "score": 1.0},
            {"name": "High", "score": 9.0},
            {"name": "Mid", "score": 5.0},
        ])
        result = normalise_json(raw)
        scores = [o["score"] for o in result["insights"]["opportunities"]]

        top_names = result["actions"]["recommended_angles"]
        assert top_names[0] == "High"

    def test_evidence_merges_into_pre_listed_competitor(self):
        result = normalise_json(self._base_raw())
        acme = next(c for c in result["competitors"] if c["name"] == "Acme")
        assert acme["reason"] == "big player" 
        assert len(acme["evidence"]) == 1