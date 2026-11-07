# record-dedupe

[![PyPI version](https://img.shields.io/pypi/v/trysac-record-dedupe)](https://pypi.org/project/trysac-record-dedupe/)
[![License: MIT](https://img.shields.io/pypi/l/trysac-record-dedupe)](LICENSE)
[![CI](https://github.com/Trysac/u165-record-dedupe/actions/workflows/ci.yml/badge.svg)](https://github.com/Trysac/u165-record-dedupe/actions/workflows/ci.yml)

Find duplicate records with weighted fuzzy field rules: Jaro-Winkler, Levenshtein, exact and numeric tolerance, blocking keys, union-find clusters and survivorship merge

## Problem

Describe in two or three sentences the concrete problem this utility solves, who hits it, and what
they do today without it. Replace this paragraph when the first real feature lands.

## Install

```sh
pip install trysac-record-dedupe
# or
uv add trysac-record-dedupe
```

Requires Python 3.10 or newer. No runtime dependencies.

## Usage

```python
import record_dedupe

# normalize() trims surrounding whitespace and lower-cases the text.
print(record_dedupe.normalize("  Hello World "))  # -> "hello world"

# Blank input is rejected explicitly instead of returning an empty string.
try:
    record_dedupe.normalize("   ")
except ValueError as exc:
    print(f"rejected: {exc}")
```

## Documentation

- [Architecture](docs/ARCHITECTURE.md) and [decisions](docs/decisions/)
- [Testing](docs/TESTING.md) and [security](docs/SECURITY.md)
- [Project record](docs/PROJECT.md) and [stack](docs/STACK.md)
- [Changelog](CHANGELOG.md) and [contributing guide](CONTRIBUTING.md)

## License

[MIT](LICENSE) (c) 2026 Miguel Gomez
