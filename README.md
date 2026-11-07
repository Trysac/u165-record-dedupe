# record-dedupe

CRM exports, supplier lists, and sign-up tables often contain duplicate entries with typos, casing variations, or missing fields. Exact matching is insufficient, and existing frameworks often require training data or heavy dependencies. `record-dedupe` provides explicit weighted rules, deterministic scores, and blocking for bounded comparisons in pure Python.

## Installation

```bash
pip install record-dedupe
```

## Usage

```python
from record_dedupe import DedupeConfig, Rule, find_duplicates, merge_cluster

records = [
    {"name": "Jon Smith", "email": "JON@x.com"},
    {"name": "John Smith", "email": "jon@x.com"},
]
config = DedupeConfig(
    rules=(Rule("name", "jaro_winkler", 1.0), Rule("email", "exact", 2.0)), threshold=0.85
)
result = find_duplicates(records, config)
merged = merge_cluster(records, result.clusters[0])
```

## API Summary

- **Functions**: `jaro_winkler(a, b)`, `levenshtein_ratio(a, b)`, `find_duplicates(records, config)`, `merge_cluster(records, cluster)`.
- **Config**: `DedupeConfig` accepts 1-10 `Rule` definitions. It validates that the threshold is in (0, 1], weights and tolerances are non-negative/finite, and limits (`max_block_size`, `max_records`) are positive integers.
- **Limits**: Blocks exceeding `max_block_size` and datasets exceeding `max_records` raise `DedupeError`.
- **Options**: Rules support `exact`, `jaro_winkler`, `levenshtein`, or `numeric` methods with `none`, `casefold`, `alnum`, or `digits` normalizers.

## Why not <best-known alternative>?

Unlike frameworks such as dedupe.io or recordlinkage, this library requires no training data, has no dependency on pandas, and provides deterministic, explainable per-field similarity scores.

See [docs/SECURITY.md](docs/SECURITY.md) for details on security.