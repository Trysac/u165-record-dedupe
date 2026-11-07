# Testing

## Running

```sh
uv run pytest --cov=record_dedupe   # tests with coverage report
uv run python scripts/check.py      # every gate, as CI and the factory run it
```

## Policy

- Branch coverage must stay at or above 80%.
- Tests exercise the public API (`import record_dedupe`) and assert return values, raised exceptions, and error messages.
- Deterministic testing: no network, no wall clock.

## Existing Tests

- `tests/test_record_dedupe.py`: Contains acceptance tests mirroring the specification (Jaro-Winkler, Levenshtein, duplicate finding, blocking, survivorship merge, and edge cases). It also tests error conditions for configuration limits and invalid parameters.