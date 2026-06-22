"""Tests for the env-driven company-glossary prepend helper."""

from __future__ import annotations

import pytest

from lfx.base.models.company_glossary import (
    EXAMPLE_COMPANY_GLOSSARY,
    get_company_glossary,
    prepend_company_glossary,
)


@pytest.fixture(autouse=True)
def _clear_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Each test starts with the glossary env var unset so the default-off
    behavior is the explicit baseline."""
    monkeypatch.delenv("LANGFLOW_COMPANY_GLOSSARY", raising=False)


class TestGetCompanyGlossary:
    def test_returns_empty_when_unset(self) -> None:
        assert get_company_glossary() == ""

    def test_returns_value_when_set(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("LANGFLOW_COMPANY_GLOSSARY", "ACME glossary")
        assert get_company_glossary() == "ACME glossary"

    def test_strips_surrounding_whitespace(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # YAML pipe-block literals frequently leave a trailing newline; the
        # env path should normalize it so a glossary doesn't pick up a
        # spurious "\n" at the boundary with the user system prompt.
        monkeypatch.setenv("LANGFLOW_COMPANY_GLOSSARY", "  \n  glossary body  \n  ")
        assert get_company_glossary() == "glossary body"

    def test_empty_string_treated_as_unset(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("LANGFLOW_COMPANY_GLOSSARY", "   ")
        assert get_company_glossary() == ""


class TestPrependCompanyGlossary:
    def test_noop_when_env_unset(self) -> None:
        assert prepend_company_glossary("user prompt") == "user prompt"

    def test_returns_none_unchanged_when_env_unset(self) -> None:
        assert prepend_company_glossary(None) is None

    def test_prepends_to_non_empty_prompt(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("LANGFLOW_COMPANY_GLOSSARY", "G")
        assert prepend_company_glossary("P") == "G\n\nP"

    def test_returns_glossary_when_prompt_is_none(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("LANGFLOW_COMPANY_GLOSSARY", "G")
        assert prepend_company_glossary(None) == "G"

    def test_returns_glossary_when_prompt_is_empty_string(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("LANGFLOW_COMPANY_GLOSSARY", "G")
        assert prepend_company_glossary("") == "G"

    def test_glossary_is_first_in_output(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # Order matters: identity/persona before task instructions. The LLM
        # should see the glossary before any flow-author system prompt.
        monkeypatch.setenv("LANGFLOW_COMPANY_GLOSSARY", "GLOSSARY_TOKEN")
        out = prepend_company_glossary("USER_TOKEN")
        assert out is not None
        assert out.index("GLOSSARY_TOKEN") < out.index("USER_TOKEN")

    def test_example_glossary_is_non_trivial(self) -> None:
        # Sanity-check the published example so a stray edit can't reduce it
        # to a placeholder that doesn't actually demonstrate the format.
        assert "PULSE" in EXAMPLE_COMPANY_GLOSSARY
        assert "Nimbus" in EXAMPLE_COMPANY_GLOSSARY
