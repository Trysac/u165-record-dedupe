"""Structured record deduplication with weighted fuzzy rules and blocking."""

from __future__ import annotations

import logging
import math
from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Literal

__all__ = [
    "DedupeConfig",
    "DedupeError",
    "DedupeResult",
    "Match",
    "Rule",
    "__version__",
    "find_duplicates",
    "jaro_winkler",
    "levenshtein_ratio",
    "merge_cluster",
]

__version__ = "0.1.0"

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

ErrorCode = Literal["invalid_config", "block_too_large", "too_many_records"]
MethodType = Literal["exact", "jaro_winkler", "levenshtein", "numeric"]
NormalizerType = Literal["none", "casefold", "alnum", "digits"]


class DedupeError(Exception):
    """Base exception raised for deduplication errors with stable machine-readable codes."""

    def __init__(self, code: ErrorCode, message: str = "") -> None:
        super().__init__(message or code)
        self.code: ErrorCode = code


@dataclass(frozen=True)
class Rule:
    """Comparison rule for an individual record field."""

    field: str
    method: MethodType
    weight: float = 1.0
    normalizer: NormalizerType = "casefold"
    tolerance: float = 0.0


@dataclass(frozen=True)
class DedupeConfig:
    """Configuration governing duplicate detection and execution bounds."""

    rules: tuple[Rule, ...]
    threshold: float = 0.85
    blocking: tuple[str, ...] = ()
    max_block_size: int = 1_000
    max_records: int = 50_000

    def __post_init__(self) -> None:
        if not (0.0 < self.threshold <= 1.0) or math.isnan(self.threshold):
            raise DedupeError("invalid_config", "Threshold must be in (0, 1]")
        if not (1 <= len(self.rules) <= 10):
            raise DedupeError("invalid_config", "Must define between 1 and 10 rules")
        if self.max_block_size < 1 or self.max_records < 1:
            raise DedupeError("invalid_config", "Limits must be positive integers")

        valid_methods = {"exact", "jaro_winkler", "levenshtein", "numeric"}
        valid_normalizers = {"none", "casefold", "alnum", "digits"}

        for rule in self.rules:
            if not isinstance(rule.field, str) or not rule.field:
                raise DedupeError("invalid_config", "Field name must be a non-empty string")
            if rule.method not in valid_methods:
                raise DedupeError("invalid_config", f"Invalid comparison method: {rule.method}")
            if rule.normalizer not in valid_normalizers:
                raise DedupeError("invalid_config", f"Invalid normalizer: {rule.normalizer}")
            if not math.isfinite(rule.weight) or rule.weight <= 0:
                raise DedupeError("invalid_config", "Rule weight must be finite and > 0")
            if not math.isfinite(rule.tolerance) or rule.tolerance < 0:
                raise DedupeError("invalid_config", "Rule tolerance must be finite and >= 0")


@dataclass(frozen=True)
class Match:
    """Matched pair of record indices and score details."""

    i: int
    j: int
    score: float
    field_scores: Mapping[str, float]


@dataclass(frozen=True)
class DedupeResult:
    """Outcome of running duplicate detection across a dataset."""

    pairs: list[Match]
    clusters: list[list[int]]
    comparisons: int


def _normalize_casefold(text: str) -> str:
    return " ".join(text.casefold().split())


def _normalize_alnum(text: str) -> str:
    folded = text.casefold()
    return "".join(c for c in folded if c.isalnum())


def _normalize_digits(text: str) -> str:
    return "".join(c for c in text if c.isdigit())


def _normalize_val(val: object, normalizer: NormalizerType) -> str:
    text = str(val)
    if normalizer == "none":
        return text
    if normalizer == "casefold":
        return _normalize_casefold(text)
    if normalizer == "alnum":
        return _normalize_alnum(text)
    if normalizer == "digits":
        return _normalize_digits(text)
    raise DedupeError("invalid_config", f"Unknown normalizer: {normalizer}")


def jaro_winkler(a: str, b: str, *, prefix_scale: float = 0.1, max_prefix: int = 4) -> float:
    """Compute Jaro-Winkler similarity between two strings (Winkler 1990).

    Matching window is max(len)//2 - 1. Prefix bonus over common prefix up to max_prefix
    characters, without boost threshold.
    """
    if a == b:
        return 1.0
    len_a = len(a)
    len_b = len(b)
    if len_a == 0 or len_b == 0:
        return 0.0

    match_window = (max(len_a, len_b) // 2) - 1
    if match_window < 0:
        match_window = 0

    a_matches = [False] * len_a
    b_matches = [False] * len_b

    matches = 0
    for i in range(len_a):
        start = max(0, i - match_window)
        end = min(i + match_window + 1, len_b)
        for j in range(start, end):
            if not b_matches[j] and a[i] == b[j]:
                a_matches[i] = True
                b_matches[j] = True
                matches += 1
                break

    if matches == 0:
        return 0.0

    a_matched_chars: list[str] = [a[i] for i in range(len_a) if a_matches[i]]
    b_matched_chars: list[str] = [b[j] for j in range(len_b) if b_matches[j]]

    transpositions = 0
    for c1, c2 in zip(a_matched_chars, b_matched_chars, strict=True):
        if c1 != c2:
            transpositions += 1
    half_transpositions = transpositions / 2.0

    m = float(matches)
    jaro = (m / len_a + m / len_b + (m - half_transpositions) / m) / 3.0

    prefix = 0
    max_p = min(max_prefix, min(len_a, len_b))
    for i in range(max_p):
        if a[i] == b[i]:
            prefix += 1
        else:
            break

    return jaro + (prefix * prefix_scale * (1.0 - jaro))


def levenshtein_ratio(a: str, b: str) -> float:
    """Compute similarity ratio 1 - distance / max(len(a), len(b))."""
    if a == b:
        return 1.0
    len_a = len(a)
    len_b = len(b)
    if len_a == 0 or len_b == 0:
        return 0.0

    prev_row = list(range(len_b + 1))
    curr_row = [0] * (len_b + 1)

    for i in range(1, len_a + 1):
        curr_row[0] = i
        char_a = a[i - 1]
        for j in range(1, len_b + 1):
            cost = 0 if char_a == b[j - 1] else 1
            curr_row[j] = min(
                curr_row[j - 1] + 1,
                prev_row[j] + 1,
                prev_row[j - 1] + cost,
            )
        prev_row, curr_row = curr_row, prev_row

    dist = prev_row[len_b]
    max_len = max(len_a, len_b)
    return 1.0 - (dist / max_len)


class _UnionFind:
    def __init__(self, elements: Sequence[int]) -> None:
        self.parent = {x: x for x in elements}

    def find(self, i: int) -> int:
        root = i
        while self.parent[root] != root:
            root = self.parent[root]
        curr = i
        while curr != root:
            nxt = self.parent[curr]
            self.parent[curr] = root
            curr = nxt
        return root

    def union(self, i: int, j: int) -> None:
        root_i = self.find(i)
        root_j = self.find(j)
        if root_i != root_j:
            self.parent[root_i] = root_j


def find_duplicates(records: Sequence[Mapping[str, object]], config: DedupeConfig) -> DedupeResult:
    """Find duplicate records using blocking and weighted field comparison rules."""
    n_records = len(records)
    if n_records > config.max_records:
        raise DedupeError(
            "too_many_records",
            f"Dataset of {n_records} records exceeds limit {config.max_records}",
        )

    blocks: dict[tuple[str, ...], list[int]] = defaultdict(list)
    has_blocking = len(config.blocking) > 0

    for idx, rec in enumerate(records):
        if has_blocking:
            is_valid_block = True
            block_key: list[str] = []
            for field in config.blocking:
                val = rec.get(field)
                if val is None:
                    is_valid_block = False
                    break
                block_key.append(_normalize_casefold(str(val)))
            if is_valid_block:
                blocks[tuple(block_key)].append(idx)
        else:
            blocks[()].append(idx)

    for indices in blocks.values():
        if len(indices) > config.max_block_size:
            raise DedupeError(
                "block_too_large",
                f"Block contains {len(indices)} records, exceeding limit {config.max_block_size}",
            )

    compared_pairs: set[tuple[int, int]] = set()
    matches: list[Match] = []
    comparisons = 0

    for block_records in blocks.values():
        block_size = len(block_records)
        for a_idx in range(block_size):
            i = block_records[a_idx]
            for b_idx in range(a_idx + 1, block_size):
                j = block_records[b_idx]
                pair = (i, j) if i < j else (j, i)
                if pair in compared_pairs:
                    continue
                compared_pairs.add(pair)
                comparisons += 1

                p_i, p_j = pair
                r_i, r_j = records[p_i], records[p_j]

                total_weight = 0.0
                weighted_score = 0.0
                field_scores: dict[str, float] = {}

                for rule in config.rules:
                    val_i = r_i.get(rule.field)
                    val_j = r_j.get(rule.field)
                    if val_i is None or val_j is None:
                        continue

                    if rule.method == "numeric":
                        try:
                            num_i = float(str(val_i))
                            num_j = float(str(val_j))
                        except (ValueError, TypeError):
                            continue
                        sim = 1.0 if abs(num_i - num_j) <= rule.tolerance else 0.0
                    else:
                        s_i = _normalize_val(val_i, rule.normalizer)
                        s_j = _normalize_val(val_j, rule.normalizer)
                        if rule.method == "exact":
                            sim = 1.0 if s_i == s_j else 0.0
                        elif rule.method == "jaro_winkler":
                            sim = jaro_winkler(s_i, s_j)
                        elif rule.method == "levenshtein":
                            sim = levenshtein_ratio(s_i, s_j)
                        else:
                            continue

                    field_scores[rule.field] = sim
                    weighted_score += rule.weight * sim
                    total_weight += rule.weight

                score = weighted_score / total_weight if total_weight > 0 else 0.0

                if score >= config.threshold:
                    matches.append(Match(i=p_i, j=p_j, score=score, field_scores=field_scores))

    matches.sort(key=lambda match_obj: (match_obj.i, match_obj.j))

    matched_indices: set[int] = set()
    for match_item in matches:
        matched_indices.add(match_item.i)
        matched_indices.add(match_item.j)

    uf = _UnionFind(list(matched_indices))
    for match_item in matches:
        uf.union(match_item.i, match_item.j)

    raw_clusters: dict[int, list[int]] = defaultdict(list)
    for idx in matched_indices:
        root = uf.find(idx)
        raw_clusters[root].append(idx)

    clusters: list[list[int]] = []
    for members in raw_clusters.values():
        if len(members) > 1:
            members.sort()
            clusters.append(members)

    clusters.sort(key=lambda c: c[0])

    return DedupeResult(pairs=matches, clusters=clusters, comparisons=comparisons)


def merge_cluster(records: Sequence[Mapping[str, Any]], cluster: Sequence[int]) -> dict[str, Any]:
    """Merge records in a cluster using survivorship precedence.

    For each field in first-seen order across the cluster, the first value in cluster order
    that is neither None nor '' is selected.
    """
    n_records = len(records)
    for idx in cluster:
        if not isinstance(idx, int) or idx < 0 or idx >= n_records:
            raise DedupeError("invalid_config", f"Index {idx} is outside valid records bounds")

    merged: dict[str, Any] = {}
    seen_fields: list[str] = []

    for idx in cluster:
        rec = records[idx]
        for k in rec:
            if k not in merged:
                seen_fields.append(k)
                merged[k] = None

    result: dict[str, Any] = {}
    for field in seen_fields:
        val: Any = None
        for idx in cluster:
            rec = records[idx]
            if field in rec:
                candidate = rec[field]
                if candidate is not None and candidate != "":
                    val = candidate
                    break
        result[field] = val

    return result
