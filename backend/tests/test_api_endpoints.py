"""API endpoint tests for the FastAPI application.

Module-level patches are applied BEFORE importing app.py to avoid two
import-time failures that cannot be worked around with per-test fixtures:

  1. StaticFiles raises RuntimeError when the ../frontend directory is absent
     in the test environment.
  2. RAGSystem instantiates real ChromaDB / Anthropic clients, which require
     credentials and disk state that tests should not touch.
"""

import sys
import pytest
from unittest.mock import MagicMock, patch

# Drop any cached copy so the patched import below starts clean.
sys.modules.pop("app", None)

# --- module-level patches (must be active before `import app`) ---

_sf_patcher = patch("fastapi.staticfiles.StaticFiles")
_mock_sf_class = _sf_patcher.start()
_mock_sf_class.return_value = MagicMock()

_rag_patcher = patch("rag_system.RAGSystem")
_mock_rag_class = _rag_patcher.start()
_mock_rag = MagicMock()
_mock_rag.add_course_folder.return_value = (0, 0)
_mock_rag_class.return_value = _mock_rag

from fastapi.testclient import TestClient  # noqa: E402
import app as app_module  # noqa: E402  intentional late import after patches

_sf_patcher.stop()
_rag_patcher.stop()

_client = TestClient(app_module.app, raise_server_exceptions=False)


# --- shared fixtures ---


@pytest.fixture
def client():
    """Return the shared TestClient bound to the patched app."""
    return _client


@pytest.fixture(autouse=True)
def reset_rag_mock():
    """Reset the shared RAGSystem mock before every test."""
    _mock_rag.reset_mock()
    # Restore the default needed by the startup event's tuple-unpack.
    _mock_rag.add_course_folder.return_value = (0, 0)
    yield


# --- /api/query ---


class TestQueryEndpoint:

    # -- successful responses --

    def test_returns_200_for_valid_request(self, client):
        _mock_rag.session_manager.create_session.return_value = "sess-1"
        _mock_rag.query.return_value = ("An answer", [])

        response = client.post("/api/query", json={"query": "What is Python?"})

        assert response.status_code == 200

    def test_response_body_contains_answer(self, client):
        _mock_rag.session_manager.create_session.return_value = "sess-1"
        _mock_rag.query.return_value = ("This is the answer", [])

        data = client.post("/api/query", json={"query": "What is Python?"}).json()

        assert data["answer"] == "This is the answer"

    def test_response_body_contains_sources(self, client):
        _mock_rag.session_manager.create_session.return_value = "sess-1"
        _mock_rag.query.return_value = ("Answer", ["<a href='...'>Source 1</a>"])

        data = client.post("/api/query", json={"query": "test"}).json()

        assert data["sources"] == ["<a href='...'>Source 1</a>"]

    def test_response_body_contains_session_id(self, client):
        _mock_rag.session_manager.create_session.return_value = "new-session-id"
        _mock_rag.query.return_value = ("Answer", [])

        data = client.post("/api/query", json={"query": "test"}).json()

        assert data["session_id"] == "new-session-id"

    # -- session handling --

    def test_creates_new_session_when_none_provided(self, client):
        _mock_rag.session_manager.create_session.return_value = "auto-sess"
        _mock_rag.query.return_value = ("Answer", [])

        client.post("/api/query", json={"query": "test"})

        _mock_rag.session_manager.create_session.assert_called_once()

    def test_uses_provided_session_id_without_creating_one(self, client):
        _mock_rag.query.return_value = ("Answer", [])

        client.post("/api/query", json={"query": "test", "session_id": "existing-session"})

        _mock_rag.session_manager.create_session.assert_not_called()

    def test_passes_provided_session_id_to_rag_query(self, client):
        _mock_rag.query.return_value = ("Answer", [])

        client.post("/api/query", json={"query": "test", "session_id": "my-session"})

        _mock_rag.query.assert_called_once_with("test", "my-session")

    def test_passes_generated_session_id_to_rag_query(self, client):
        _mock_rag.session_manager.create_session.return_value = "generated-sess"
        _mock_rag.query.return_value = ("Answer", [])

        client.post("/api/query", json={"query": "What is ML?"})

        _mock_rag.query.assert_called_once_with("What is ML?", "generated-sess")

    # -- error handling --

    def test_returns_500_when_rag_system_raises(self, client):
        _mock_rag.session_manager.create_session.return_value = "sess-err"
        _mock_rag.query.side_effect = Exception("RAG failure")

        response = client.post("/api/query", json={"query": "test"})

        assert response.status_code == 500

    def test_returns_422_for_missing_query_field(self, client):
        response = client.post("/api/query", json={})

        assert response.status_code == 422

    def test_returns_422_for_empty_body(self, client):
        response = client.post("/api/query", json=None)

        assert response.status_code == 422


# --- /api/courses ---


class TestCoursesEndpoint:

    def test_returns_200(self, client):
        _mock_rag.get_course_analytics.return_value = {
            "total_courses": 2,
            "course_titles": ["Course A", "Course B"],
        }

        response = client.get("/api/courses")

        assert response.status_code == 200

    def test_returns_correct_total_count(self, client):
        _mock_rag.get_course_analytics.return_value = {
            "total_courses": 5,
            "course_titles": ["A", "B", "C", "D", "E"],
        }

        data = client.get("/api/courses").json()

        assert data["total_courses"] == 5

    def test_returns_correct_course_titles(self, client, sample_course_analytics):
        _mock_rag.get_course_analytics.return_value = sample_course_analytics

        data = client.get("/api/courses").json()

        assert data["course_titles"] == sample_course_analytics["course_titles"]

    def test_returns_500_when_analytics_raises(self, client):
        _mock_rag.get_course_analytics.side_effect = Exception("DB unavailable")

        response = client.get("/api/courses")

        assert response.status_code == 500

    def test_calls_rag_get_course_analytics(self, client):
        _mock_rag.get_course_analytics.return_value = {
            "total_courses": 0,
            "course_titles": [],
        }

        client.get("/api/courses")

        _mock_rag.get_course_analytics.assert_called_once()


# --- /api/session/{session_id} ---


class TestDeleteSessionEndpoint:

    def test_returns_200(self, client):
        response = client.delete("/api/session/some-session")

        assert response.status_code == 200

    def test_returns_cleared_status(self, client):
        data = client.delete("/api/session/some-session").json()

        assert data["status"] == "cleared"

    def test_calls_clear_session_with_correct_id(self, client):
        client.delete("/api/session/target-session")

        _mock_rag.session_manager.clear_session.assert_called_once_with("target-session")
