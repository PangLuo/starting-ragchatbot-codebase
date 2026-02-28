from unittest.mock import MagicMock
from search_tools import CourseSearchTool
from vector_store import SearchResults


def make_results(documents=None, metadata=None):
    docs = documents or []
    metas = metadata or []
    return SearchResults(documents=docs, metadata=metas, distances=[0.5] * len(docs))


class TestCourseSearchToolExecute:

    def setup_method(self):
        self.mock_store = MagicMock()
        self.tool = CourseSearchTool(self.mock_store)

    # --- Error and empty result handling ---

    def test_execute_returns_error_message(self):
        self.mock_store.search.return_value = SearchResults.empty("search failed")
        result = self.tool.execute(query="test query")
        assert result == "search failed"

    def test_execute_returns_no_content_when_empty_no_filters(self):
        self.mock_store.search.return_value = make_results()
        result = self.tool.execute(query="test query")
        assert result == "No relevant content found."

    def test_execute_returns_no_content_with_course_filter_info(self):
        self.mock_store.search.return_value = make_results()
        result = self.tool.execute(query="test query", course_name="Python 101")
        assert "in course 'Python 101'" in result

    def test_execute_returns_no_content_with_lesson_filter_info(self):
        self.mock_store.search.return_value = make_results()
        result = self.tool.execute(query="test query", lesson_number=3)
        assert "in lesson 3" in result

    # --- store.search call verification ---

    def test_execute_passes_query_to_store_search(self):
        self.mock_store.search.return_value = make_results()
        self.tool.execute(query="my query", course_name="CS50", lesson_number=2)
        self.mock_store.search.assert_called_once_with(
            query="my query",
            course_name="CS50",
            lesson_number=2,
        )

    # --- Result header formatting ---

    def test_format_results_header_with_lesson_number(self):
        results = make_results(
            documents=["chunk content"],
            metadata=[{"course_title": "Python Course", "lesson_number": 5}],
        )
        self.mock_store.search.return_value = results
        self.mock_store.get_lesson_link.return_value = None

        result = self.tool.execute(query="test")
        assert "[Python Course - Lesson 5]" in result

    def test_format_results_header_without_lesson_number(self):
        # metadata has no 'lesson_number' key at all
        results = make_results(
            documents=["chunk content"],
            metadata=[{"course_title": "Python Course"}],
        )
        self.mock_store.search.return_value = results

        result = self.tool.execute(query="test")
        assert "[Python Course]" in result
        assert "Lesson" not in result

    # --- Source link generation ---

    def test_execute_sets_last_sources_with_link(self):
        results = make_results(
            documents=["content"],
            metadata=[{"course_title": "My Course", "lesson_number": 2}],
        )
        self.mock_store.search.return_value = results
        self.mock_store.get_lesson_link.return_value = "https://example.com/lesson"

        self.tool.execute(query="test")

        assert len(self.tool.last_sources) == 1
        assert 'href="https://example.com/lesson"' in self.tool.last_sources[0]
        assert "My Course - Lesson 2" in self.tool.last_sources[0]

    def test_execute_sets_last_sources_without_link(self):
        results = make_results(
            documents=["content"],
            metadata=[{"course_title": "My Course", "lesson_number": 2}],
        )
        self.mock_store.search.return_value = results
        self.mock_store.get_lesson_link.return_value = None

        self.tool.execute(query="test")

        assert len(self.tool.last_sources) == 1
        assert self.tool.last_sources[0] == "My Course - Lesson 2"

    # --- Source overwriting ---

    def test_execute_overwrites_last_sources_on_each_call(self):
        # First call produces two sources
        results1 = make_results(
            documents=["doc1", "doc2"],
            metadata=[
                {"course_title": "Course A", "lesson_number": 1},
                {"course_title": "Course B", "lesson_number": 2},
            ],
        )
        self.mock_store.search.return_value = results1
        self.mock_store.get_lesson_link.return_value = None
        self.tool.execute(query="first query")
        assert len(self.tool.last_sources) == 2

        # Second call produces one source — should replace, not append
        results2 = make_results(
            documents=["doc3"],
            metadata=[{"course_title": "Course C", "lesson_number": 3}],
        )
        self.mock_store.search.return_value = results2
        self.tool.execute(query="second query")

        assert len(self.tool.last_sources) == 1
        assert "Course C" in self.tool.last_sources[0]

    # --- Tool definition structure ---

    def test_tool_definition_contains_required_fields(self):
        definition = self.tool.get_tool_definition()
        assert "name" in definition
        assert "description" in definition
        assert "input_schema" in definition
        assert "query" in definition["input_schema"]["required"]
