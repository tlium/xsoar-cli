"""Unit tests for helpers in ``xsoar_cli.commands.case.commands``."""

from __future__ import annotations

import pytest

from xsoar_cli.commands.case.commands import parse_entry_id


class TestParseEntryId:
    def test_valid_entry_id_returns_case_id(self) -> None:
        assert parse_entry_id("112@153483") == 153483

    def test_multi_digit_entry_number(self) -> None:
        assert parse_entry_id("9@7") == 7

    def test_missing_at_separator_raises(self) -> None:
        with pytest.raises(ValueError, match="invalid entry id"):
            parse_entry_id("112")

    def test_empty_entry_number_raises(self) -> None:
        with pytest.raises(ValueError, match="invalid entry id"):
            parse_entry_id("@153483")

    def test_non_numeric_entry_number_raises(self) -> None:
        with pytest.raises(ValueError, match="invalid entry id"):
            parse_entry_id("12INVALID21@1234")

    def test_empty_case_id_raises(self) -> None:
        with pytest.raises(ValueError, match="invalid entry id"):
            parse_entry_id("112@")

    def test_non_numeric_case_id_raises(self) -> None:
        with pytest.raises(ValueError, match="invalid entry id"):
            parse_entry_id("112@abc")

    def test_too_many_parts_raises(self) -> None:
        with pytest.raises(ValueError, match="invalid entry id"):
            parse_entry_id("112@153483@extra")
