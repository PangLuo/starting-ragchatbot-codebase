import pytest
from unittest.mock import MagicMock, patch
from rag_system import RAGSystem


@pytest.fixture
def rag_mocks():
    """Construct a RAGSystem with all sub-components replaced by MagicMocks."""
    with (
        patch("rag_system.DocumentProcessor") as mock_dp,
        patch("rag_system.VectorStore") as mock_vs,
        patch("rag_system.AIGenerator") as mock_ai,
        patch("rag_system.SessionManager") as mock_sm,
        patch("rag_system.ToolManager") as mock_tm,
        patch("rag_system.CourseSearchTool") as mock_cst,
        patch("rag_system.CourseOutlineTool") as mock_cot,
    ):
        config = MagicMock()
        rag = RAGSystem(config)
        yield {
            "rag": rag,
            "mock_ai": mock_ai,
            "mock_sm": mock_sm,
            "mock_tm": mock_tm,
        }


class TestRAGSystemQuery:

    # --- Prompt construction ---

    def test_query_wraps_user_query_in_prompt(self, rag_mocks):
        rag = rag_mocks["rag"]
        rag.ai_generator.generate_response.return_value = "some answer"
        rag.tool_manager.get_last_sources.return_value = []

        rag.query("What is Python?")

        call_kwargs = rag.ai_generator.generate_response.call_args.kwargs
        assert call_kwargs["query"] == "Answer this question about course materials: What is Python?"

    def test_query_passes_tool_definitions_to_ai_generator(self, rag_mocks):
        rag = rag_mocks["rag"]
        rag.ai_generator.generate_response.return_value = "answer"
        expected_tools = [{"name": "search_course_content"}]
        rag.tool_manager.get_tool_definitions.return_value = expected_tools
        rag.tool_manager.get_last_sources.return_value = []

        rag.query("test query")

        call_kwargs = rag.ai_generator.generate_response.call_args.kwargs
        assert call_kwargs["tools"] == expected_tools

    # --- Return values ---

    def test_query_returns_response_from_ai_generator(self, rag_mocks):
        rag = rag_mocks["rag"]
        rag.ai_generator.generate_response.return_value = "the AI answer"
        rag.tool_manager.get_last_sources.return_value = []

        response, sources = rag.query("test query")

        assert response == "the AI answer"

    def test_query_retrieves_sources_from_tool_manager(self, rag_mocks):
        rag = rag_mocks["rag"]
        rag.ai_generator.generate_response.return_value = "answer"
        rag.tool_manager.get_last_sources.return_value = ["<a href='...'>Source 1</a>"]

        response, sources = rag.query("test query")

        assert sources == ["<a href='...'>Source 1</a>"]

    def test_query_resets_sources_after_retrieval(self, rag_mocks):
        rag = rag_mocks["rag"]
        rag.ai_generator.generate_response.return_value = "answer"
        rag.tool_manager.get_last_sources.return_value = []

        rag.query("test query")

        rag.tool_manager.reset_sources.assert_called_once()

    # --- Session history ---

    def test_query_with_session_id_fetches_history(self, rag_mocks):
        rag = rag_mocks["rag"]
        rag.ai_generator.generate_response.return_value = "answer"
        rag.session_manager.get_conversation_history.return_value = "User: Hi\nAssistant: Hello"
        rag.tool_manager.get_last_sources.return_value = []

        rag.query("test query", session_id="session_1")

        rag.session_manager.get_conversation_history.assert_called_once_with("session_1")

    def test_query_with_session_id_stores_exchange(self, rag_mocks):
        rag = rag_mocks["rag"]
        rag.ai_generator.generate_response.return_value = "the response"
        rag.tool_manager.get_last_sources.return_value = []

        rag.query("original query", session_id="session_1")

        # Current behavior: original query (not the wrapped prompt) is stored.
        # Bug D: the AI received the wrapped prompt, so history will misrepresent
        # what was actually sent to the model in previous turns.
        rag.session_manager.add_exchange.assert_called_once_with(
            "session_1", "original query", "the response"
        )

    def test_query_without_session_id_skips_history_calls(self, rag_mocks):
        rag = rag_mocks["rag"]
        rag.ai_generator.generate_response.return_value = "answer"
        rag.tool_manager.get_last_sources.return_value = []

        rag.query("test query", session_id=None)

        rag.session_manager.get_conversation_history.assert_not_called()
        rag.session_manager.add_exchange.assert_not_called()
