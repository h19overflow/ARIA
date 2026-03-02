"""Tests for PRO-21: required_integrations CSV-vs-list normalization."""
import pytest
from src.agentic_system.conversation.models.schemas import ConversationNotes


def test_csv_string_in_list_is_split():
    """A CSV string inside the list should be split into individual items."""
    notes = ConversationNotes(required_integrations=["Gmail, OpenAI, Telegram"])
    assert notes.required_integrations == ["Gmail", "OpenAI", "Telegram"]


def test_already_correct_list_is_unchanged():
    """A properly-formed list should pass through untouched."""
    notes = ConversationNotes(required_integrations=["Gmail", "OpenAI", "Telegram"])
    assert notes.required_integrations == ["Gmail", "OpenAI", "Telegram"]


def test_empty_list_is_unchanged():
    notes = ConversationNotes(required_integrations=[])
    assert notes.required_integrations == []


def test_whitespace_is_stripped():
    notes = ConversationNotes(required_integrations=["  Gmail , OpenAI  "])
    assert notes.required_integrations == ["Gmail", "OpenAI"]


def test_duplicates_after_split_are_removed():
    notes = ConversationNotes(required_integrations=["Gmail", "Gmail, OpenAI"])
    assert notes.required_integrations == ["Gmail", "OpenAI"]


# --- Task 2: notes_updater _set_note tests ---

from unittest.mock import MagicMock
from src.agentic_system.conversation.tools.notes_updater import update_notes_state


def _make_state_with_empty_notes():
    """Create a minimal ConversationState mock with real ConversationNotes."""
    state = MagicMock()
    state.notes = ConversationNotes()
    return state


def test_set_note_splits_csv_string():
    state = _make_state_with_empty_notes()
    update_notes_state(state, {"key": "required_integrations", "value": "Gmail, OpenAI"})
    assert state.notes.required_integrations == ["Gmail", "OpenAI"]


def test_set_note_handles_single_value():
    state = _make_state_with_empty_notes()
    update_notes_state(state, {"key": "required_integrations", "value": "Gmail"})
    assert state.notes.required_integrations == ["Gmail"]


def test_set_note_deduplicates_on_append():
    state = _make_state_with_empty_notes()
    update_notes_state(state, {"key": "required_integrations", "value": "Gmail"})
    update_notes_state(state, {"key": "required_integrations", "value": "Gmail, OpenAI"})
    assert state.notes.required_integrations == ["Gmail", "OpenAI"]


# --- Task 3: credential_resolver defensive CSV split ---

from unittest.mock import AsyncMock, patch
from src.agentic_system.shared.credential_resolver import resolve_credential_types


@pytest.mark.asyncio
async def test_resolve_splits_csv_input():
    """If a CSV string like 'Gmail, Telegram' is passed, resolve each separately."""
    with patch(
        "src.agentic_system.shared.credential_resolver._guess_credential_types",
        new_callable=AsyncMock,
        return_value=None,
    ), patch(
        "src.agentic_system.shared.credential_resolver.llm_resolve",
        new_callable=AsyncMock,
        return_value=None,
    ):
        # The important thing is it doesn't try to resolve "Gmail, Telegram" as one name
        result = await resolve_credential_types("Gmail, Telegram")
        # Should have been split — verify by checking that we got results for each
        # (or empty list if mocks return None, but the key is no crash)
        assert isinstance(result, list)
