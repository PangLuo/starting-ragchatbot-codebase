import sys
import os
import pytest
from unittest.mock import MagicMock

# Add the backend directory to sys.path so test files can import backend modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture
def mock_rag_system():
    """Return a MagicMock that mimics the RAGSystem interface."""
    mock = MagicMock()
    mock.add_course_folder.return_value = (0, 0)
    mock.query.return_value = ("Mock answer", [])
    mock.get_course_analytics.return_value = {
        "total_courses": 0,
        "course_titles": [],
    }
    return mock


@pytest.fixture
def sample_course_analytics():
    """Sample course analytics payload for use across tests."""
    return {
        "total_courses": 3,
        "course_titles": ["Python Basics", "FastAPI Development", "Machine Learning 101"],
    }
