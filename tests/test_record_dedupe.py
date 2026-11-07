"""Behavior tests for the public API of record_dedupe."""

from __future__ import annotations

import pytest

import record_dedupe


def test_normalize_trims_and_lowercases() -> None:
    assert record_dedupe.normalize("  Hello World ") == "hello world"


@pytest.mark.parametrize("value", ["", "   ", "\t\n"])
def test_normalize_rejects_blank_input(value: str) -> None:
    with pytest.raises(ValueError, match="must not be empty"):
        record_dedupe.normalize(value)


def test_version_is_semver() -> None:
    parts = record_dedupe.__version__.split(".")
    assert len(parts) == 3
    assert all(part.isdigit() for part in parts)
