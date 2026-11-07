# Use pure Python standard library for weighted record deduplication and blocking

Status: accepted (generated, pending human review)

## Context

Customer and catalog record deduplication commonly requires heavy machine learning frameworks or C-extension packages. In lightweight pipelines, deterministic, explainable rules with blocking boundaries and zero dependencies are preferred.

## Decision

Implement Jaro-Winkler (Winkler 1990) and Levenshtein dynamic programming directly in pure Python standard library, with union-find clustering and field-level normalization.

## Consequences

Zero external dependencies and cross-platform determinism, with execution bounded by explicit dataset and block limits.
