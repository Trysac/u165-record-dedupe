"""Unit tests for record_dedupe covering acceptance items, error conditions, and edge cases."""

import pytest

from record_dedupe import (
    DedupeConfig,
    DedupeError,
    Rule,
    find_duplicates,
    jaro_winkler,
    levenshtein_ratio,
    merge_cluster,
)


def test_acceptance_jaro_winkler() -> None:
    """Acceptance: Jaro-Winkler standard strings and edge cases."""
    assert round(jaro_winkler("MARTHA", "MARHTA"), 4) == 0.9611
    assert round(jaro_winkler("DIXON", "DICKSONX"), 4) == 0.8133
    assert round(jaro_winkler("JELLYFISH", "SMELLYFISH"), 4) == 0.8963
    assert jaro_winkler("", "a") == 0.0 and jaro_winkler("", "") == 1.0


def test_acceptance_levenshtein_ratio() -> None:
    """Acceptance: Levenshtein ratio standard strings and empty edge cases."""
    assert (
        round(levenshtein_ratio("kitten", "sitting"), 4) == 0.5714
        and levenshtein_ratio("", "") == 1.0
    )


def test_acceptance_records_with_blocking() -> None:
    """Acceptance: Records with blocking, weighted fields, exact float comparisons."""
    records = [
        {"name": "Jon Smith", "email": "JON@x.com", "zip": "10001"},
        {"name": "John Smith", "email": "jon@x.com", "zip": "10001"},
        {"name": "Mary Jones", "email": "mary@y.com", "zip": "20002"},
    ]
    rules = (
        Rule(field="name", method="jaro_winkler", weight=1.0),
        Rule(field="email", method="exact", weight=2.0),
    )
    config = DedupeConfig(rules=rules, threshold=0.85, blocking=("zip",))
    result = find_duplicates(records, config)

    assert [(m.i, m.j) for m in result.pairs] == [(0, 1)]
    assert round(result.pairs[0].score, 4) == 0.9911
    assert result.clusters == [[0, 1]]
    assert result.comparisons == 1


def test_acceptance_missing_field_and_no_overlap() -> None:
    """Acceptance: None or missing fields are excluded; score is 0.0 when no rule field overlaps."""
    records = [
        {"name": "Alice", "email": None},
        {"name": None, "email": "alice@example.com"},
        {"other": "data"},
    ]
    config = DedupeConfig(
        rules=(Rule(field="name", method="exact"), Rule(field="email", method="exact"))
    )
    result = find_duplicates(records, config)
    assert len(result.pairs) == 0
    assert result.clusters == []


def test_acceptance_transitive_clustering() -> None:
    """Acceptance: Transitive clustering where pairwise link (0, 2) is below threshold."""
    records = [
        {"name": "ann"},
        {"name": "anne"},
        {"name": "annette"},
    ]
    config = DedupeConfig(rules=(Rule(field="name", method="jaro_winkler"),), threshold=0.9)
    result = find_duplicates(records, config)

    assert [(m.i, m.j) for m in result.pairs] == [(0, 1), (1, 2)]
    assert result.clusters == [[0, 1, 2]]
    # Verify (0, 2) similarity is indeed 0.8667
    assert round(jaro_winkler("ann", "annette"), 4) == 0.8667


def test_acceptance_numeric_and_digits_normalizer() -> None:
    """Acceptance: Numeric rule with tolerance and digits normalizer for phone numbers."""
    records = [
        {"val": 10.0, "phone": "(555) 123-4567"},
        {"val": 10.4, "phone": "555.123.4567"},
        {"val": 10.6, "phone": "555-123-4567"},
    ]
    config = DedupeConfig(
        rules=(
            Rule(field="val", method="numeric", tolerance=0.5),
            Rule(field="phone", method="exact", normalizer="digits"),
        ),
        threshold=1.0,
    )
    result = find_duplicates(records, config)
    # (0, 1) val diff is 0.4 <= 0.5 (sim 1.0), phones match under digits (sim 1.0) -> score 1.0
    # (0, 2) val diff is 0.6 > 0.5 (sim 0.0), phones match -> score 0.5 < 1.0
    # (1, 2) val diff is 0.2 <= 0.5 (sim 1.0), phones match -> score 1.0
    assert [(m.i, m.j) for m in result.pairs] == [(0, 1), (1, 2)]
    assert result.clusters == [[0, 1, 2]]


def test_acceptance_config_and_boundary_errors() -> None:
    """Acceptance: DedupeConfig and execution boundary checks raise DedupeError."""
    with pytest.raises(DedupeError) as exc:
        DedupeConfig(rules=(Rule("a", "exact"),), threshold=1.5)
    assert exc.value.code == "invalid_config"

    with pytest.raises(DedupeError) as exc:
        DedupeConfig(rules=())
    assert exc.value.code == "invalid_config"

    with pytest.raises(DedupeError) as exc:
        DedupeConfig(rules=(Rule("a", "exact", weight=-1.0),))
    assert exc.value.code == "invalid_config"

    # block_too_large
    records_1001 = [{"k": "group"} for _ in range(1001)]
    cfg_1000 = DedupeConfig(rules=(Rule("k", "exact"),), blocking=("k",), max_block_size=1000)
    with pytest.raises(DedupeError) as exc:
        find_duplicates(records_1001, cfg_1000)
    assert exc.value.code == "block_too_large"

    # unblocked run also respects max_block_size
    cfg_unblocked = DedupeConfig(rules=(Rule("k", "exact"),), max_block_size=1000)
    with pytest.raises(DedupeError) as exc:
        find_duplicates(records_1001, cfg_unblocked)
    assert exc.value.code == "block_too_large"

    # too_many_records
    cfg_limit = DedupeConfig(rules=(Rule("k", "exact"),), max_records=5)
    records_6 = [{"k": str(i)} for i in range(6)]
    with pytest.raises(DedupeError) as exc:
        find_duplicates(records_6, cfg_limit)
    assert exc.value.code == "too_many_records"


def test_acceptance_merge_cluster() -> None:
    """Acceptance: Survivorship merge over cluster with empty strings and determinism."""
    cluster_records = [{"a": "", "b": 1}, {"a": "x", "b": 2}]
    merged = merge_cluster(cluster_records, [0, 1])
    assert merged == {"a": "x", "b": 1}

    # Determinism: identical on multiple runs
    for _ in range(5):
        assert merge_cluster(cluster_records, [0, 1]) == {"a": "x", "b": 1}


def test_merge_cluster_invalid_index() -> None:
    records = [{"a": 1}]
    with pytest.raises(DedupeError) as exc:
        merge_cluster(records, [0, 5])
    assert exc.value.code == "invalid_config"

    with pytest.raises(DedupeError) as exc:
        merge_cluster(records, [-1])
    assert exc.value.code == "invalid_config"


def test_additional_config_validations() -> None:
    with pytest.raises(DedupeError) as exc:
        DedupeConfig(rules=(Rule("a", "exact"),), threshold=0.0)
    assert exc.value.code == "invalid_config"

    with pytest.raises(DedupeError) as exc:
        DedupeConfig(rules=tuple(Rule(f"f{i}", "exact") for i in range(11)))
    assert exc.value.code == "invalid_config"

    with pytest.raises(DedupeError) as exc:
        DedupeConfig(rules=(Rule("", "exact"),))
    assert exc.value.code == "invalid_config"

    with pytest.raises(DedupeError) as exc:
        DedupeConfig(rules=(Rule("f", "unknown"),))  # type: ignore
    assert exc.value.code == "invalid_config"

    with pytest.raises(DedupeError) as exc:
        DedupeConfig(rules=(Rule("f", "exact", normalizer="unknown"),))  # type: ignore
    assert exc.value.code == "invalid_config"

    with pytest.raises(DedupeError) as exc:
        DedupeConfig(rules=(Rule("f", "exact", tolerance=-0.1),))
    assert exc.value.code == "invalid_config"

    with pytest.raises(DedupeError) as exc:
        DedupeConfig(rules=(Rule("f", "exact"),), max_block_size=0)
    assert exc.value.code == "invalid_config"


def test_normalizers_and_methods() -> None:
    records = [
        {"code": "  Ab-12 # ", "lev": "kitten", "num": "invalid_num"},
        {"code": "ab-12", "lev": "sitting", "num": "not_a_num"},
    ]
    # normalizer 'alnum'
    config = DedupeConfig(
        rules=(
            Rule("code", "exact", normalizer="alnum"),
            Rule("lev", "levenshtein", weight=2.0),
            Rule("num", "numeric"),
        ),
        threshold=0.5,
    )
    result = find_duplicates(records, config)
    assert len(result.pairs) == 1
    match = result.pairs[0]
    assert match.field_scores["code"] == 1.0
    assert round(match.field_scores["lev"], 4) == 0.5714
    assert "num" not in match.field_scores


def test_levenshtein_ratio_edge_cases() -> None:
    assert levenshtein_ratio("a", "") == 0.0
    assert levenshtein_ratio("", "a") == 0.0
    assert levenshtein_ratio("abc", "abc") == 1.0
    assert levenshtein_ratio("abc", "def") == 0.0


def test_jaro_winkler_adversarial_and_edges() -> None:
    # No common characters
    assert jaro_winkler("abc", "xyz") == 0.0
    # Different prefix bonus length
    assert round(jaro_winkler("abcd", "abce"), 4) == 0.8833
