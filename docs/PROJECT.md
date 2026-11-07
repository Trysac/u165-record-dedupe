# Project record

## Objective

Find duplicate records with weighted fuzzy field rules: Jaro-Winkler, Levenshtein, exact and numeric tolerance, blocking keys, union-find clusters and survivorship merge.

## Scope

- The library provides the public API for fuzzy matching, blocking, and clustering.
- Configurable field weights and normalizers are supported.
- Survivorship cluster merging is included.

## Out-of-scope

- Machine-learned weights.
- Phonetic encodings (e.g., Soundex, Metaphone).
- Parallel processing.
- Persistence layers.
- Incremental deduplication.

## Timeline

| Date | Event |
|---|---|
| 2026 | Repository created from the factory utility template. |

## Effort metrics

| Metric | Value |
|---|---|
| Tokens (input / output) | 699798 / 12269 |
| Hours (human) | pending measurement |
| Cost (USD) | 0.1602 |

## Factory run u165 (measured from API usage)

| Phase | Model | Batch | Input | Output | Cache write | Cache read | Cost (USD) |
|---|---|---|---|---|---|---|---|
| generation | gemini-3.8-flash | yes | 4500 | 8267 | 0 | 0 | 0.0172 |
| fix-1 | gemini-3.8-flash | no | 34443 | 916 | 0 | 95662 | 0.0364 |
| fix-2 | gemini-3.8-flash | no | 34403 | 1572 | 0 | 94481 | 0.0388 |
| audit | gemini-3.1-flash-lite | no | 56219 | 247 | 0 | 193531 | 0.0193 |
| docs | gemini-3.1-flash-lite | no | 186559 | 1267 | 0 | 0 | 0.0485 |

Total: $0.1602. Prices: Anthropic list prices.
