"""test_validators.py — ACTOR_REGEX 및 validate_actor() 엣지 케이스 테스트."""
from __future__ import annotations

import re

import pytest

from py_sync_contracts import ACTOR_REGEX
from py_sync_contracts.validators import validate_actor


class TestActorRegex:
    def test_regex_compiles(self) -> None:
        pattern = re.compile(ACTOR_REGEX)
        assert pattern is not None

    def test_max_length_boundary(self) -> None:
        pattern = re.compile(ACTOR_REGEX)
        assert pattern.match("x" * 64) is not None   # 경계값 — 통과
        assert pattern.match("x" * 65) is None        # 경계값+1 — 실패

    def test_allowed_characters(self) -> None:
        pattern = re.compile(ACTOR_REGEX)
        valid_actors = ["a", "A", "0", ".", "_", "-", "joel.noru", "A-B.C_1"]
        for actor in valid_actors:
            assert pattern.match(actor), f"expected match: {actor!r}"

    def test_disallowed_characters(self) -> None:
        pattern = re.compile(ACTOR_REGEX)
        invalid_actors = ["", " ", "@", "/", "\\", "조엘", "joel noru", "joel@noru"]
        for actor in invalid_actors:
            assert not pattern.match(actor), f"expected no match: {actor!r}"


class TestValidateActor:
    @pytest.mark.parametrize(
        "actor",
        [
            "joel.noru",
            "admin",
            "user_01",
            "A-B.C_1",
            "x" * 64,
        ],
    )
    def test_valid_actors_pass(self, actor: str) -> None:
        result = validate_actor(actor)
        assert result == actor

    @pytest.mark.parametrize(
        "actor",
        [
            "",
            "x" * 65,
            "joel noru",
            "joel@noru",
            "조엘",
            "joel/noru",
        ],
    )
    def test_invalid_actors_raise(self, actor: str) -> None:
        with pytest.raises(ValueError, match="invalid actor"):
            validate_actor(actor)

    def test_non_string_raises(self) -> None:
        with pytest.raises(ValueError, match="invalid actor"):
            validate_actor(123)  # type: ignore[arg-type]

    def test_none_raises(self) -> None:
        with pytest.raises(ValueError, match="invalid actor"):
            validate_actor(None)  # type: ignore[arg-type]
