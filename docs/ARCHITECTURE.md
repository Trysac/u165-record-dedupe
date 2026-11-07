# Architecture

`record_dedupe` provides bounded, deterministic entity resolution and duplicate record detection on structured data.

## Pipeline

1. **Validation & Configuration**: `DedupeConfig` checks rule specifications, weights, tolerances, and bounds.
2. **Blocking**: Partitions records by normalized blocking keys (`casefold`). Any record missing a blocking key is skipped. If no blocking keys are provided, the dataset forms a single block subject to `max_block_size`.
3. **Pairwise Comparison**: Within blocks, candidate pairs `(i, j)` with `i < j` are compared. Normalized field similarities are evaluated across matching rules; missing fields are excluded from both numerator and denominator.
4. **Clustering**: Matched pairs above `threshold` are grouped using a disjoint-set (union-find) data structure with path compression.
5. **Survivorship Merging**: Clusters can be merged via `merge_cluster`, which preserves field order and chooses the first non-empty, non-`None` value in cluster order.
