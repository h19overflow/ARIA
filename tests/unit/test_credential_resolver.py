"""Tests for the dynamic credential resolver."""
import pytest
from unittest.mock import AsyncMock, patch

from src.agentic_system.shared.credential_resolver import (
    resolve_credential_types,
    _normalize_to_camel_case,
    _generate_candidates,
    _runtime_cache,
)
from src.agentic_system.shared.node_credential_map import NODE_CREDENTIAL_MAP


class TestNormalizeToCamelCase:
    def test_single_word(self):
        assert _normalize_to_camel_case("zendesk") == "zendesk"

    def test_two_words(self):
        assert _normalize_to_camel_case("google sheets") == "googleSheets"

    def test_three_words(self):
        assert _normalize_to_camel_case("microsoft one drive") == "microsoftOneDrive"

    def test_already_camel(self):
        assert _normalize_to_camel_case("googleSheets") == "googleSheets"

    def test_strips_hyphens(self):
        assert _normalize_to_camel_case("my-service") == "myService"

    def test_strips_whitespace(self):
        assert _normalize_to_camel_case("  slack  ") == "slack"


class TestGenerateCandidates:
    def test_simple_name(self):
        candidates = _generate_candidates("zendesk")
        assert candidates == ["zendeskApi", "zendeskOAuth2Api", "zendeskOAuth2"]

    def test_camel_case_name(self):
        candidates = _generate_candidates("googleSheets")
        assert candidates == ["googleSheetsApi", "googleSheetsOAuth2Api", "googleSheetsOAuth2"]


class TestResolveCredentialTypes:
    @pytest.fixture(autouse=True)
    def clear_cache(self):
        _runtime_cache.clear()
        yield
        _runtime_cache.clear()

    @pytest.mark.asyncio
    async def test_alias_hit(self):
        """Step 1: aliases resolve without any API call."""
        result = await resolve_credential_types("gemini")
        assert result == ["googlePalmApi"]

    @pytest.mark.asyncio
    async def test_hardcoded_map_hit(self):
        """Step 2: hardcoded map resolves without any API call."""
        result = await resolve_credential_types("telegram")
        assert result == ["telegramApi"]

    @pytest.mark.asyncio
    async def test_convention_guess_hit(self):
        """Step 3: convention guessing finds a valid type via n8n API."""
        with patch(
            "src.agentic_system.shared.credential_resolver._validate_credential_type"
        ) as mock_validate:
            async def _check(t):
                return t == "zendeskApi"
            mock_validate.side_effect = _check
            result = await resolve_credential_types("zendesk")
            assert result == ["zendeskApi"]

    @pytest.mark.asyncio
    async def test_convention_guess_caches(self):
        """Convention guess results are cached on second call."""
        with patch(
            "src.agentic_system.shared.credential_resolver._validate_credential_type"
        ) as mock_validate:
            async def _check(t):
                return t == "zendeskApi"
            mock_validate.side_effect = _check
            await resolve_credential_types("zendesk")
            # Second call should NOT hit the validator
            mock_validate.reset_mock()
            result = await resolve_credential_types("zendesk")
            assert result == ["zendeskApi"]
            mock_validate.assert_not_called()

    @pytest.mark.asyncio
    async def test_no_match_returns_empty(self):
        """Step 5: when nothing matches, return empty list."""
        with patch(
            "src.agentic_system.shared.credential_resolver._validate_credential_type",
            new_callable=AsyncMock,
            return_value=False,
        ), patch(
            "src.agentic_system.shared.credential_resolver.llm_resolve",
            new_callable=AsyncMock,
            return_value=None,
        ):
            result = await resolve_credential_types("totallyFakeService123")
            assert result == []


class TestClassifyWithDynamicEntries:
    """Verify _classify_credentials sees resolver-injected map entries."""

    @pytest.fixture(autouse=True)
    def clear_state(self):
        _runtime_cache.clear()
        yield
        _runtime_cache.clear()
        # Clean up any injected entries
        NODE_CREDENTIAL_MAP.pop("zendesk", None)

    @pytest.mark.asyncio
    async def test_classify_sees_resolved_types(self):
        """After resolver runs, _classify_credentials can find the new type."""
        from src.agentic_system.conversation.tools.credential_tools import (
            _classify_credentials,
        )
        from src.agentic_system.shared.node_credential_map import NODE_CREDENTIAL_MAP

        # Simulate resolver injecting a new entry
        with patch(
            "src.agentic_system.shared.credential_resolver._validate_credential_type"
        ) as mock_validate:
            async def _check(t):
                return t == "zendeskApi"
            mock_validate.side_effect = _check
            await resolve_credential_types("zendesk")

        # Now _classify_credentials should see it
        assert "zendesk" in NODE_CREDENTIAL_MAP
        saved = [{"type": "zendeskApi", "id": "abc123", "name": "My Zendesk"}]
        resolved, pending = _classify_credentials(saved, ["zendesk"])
        assert len(resolved) == 1
        assert resolved[0]["id"] == "abc123"
        assert pending == []
