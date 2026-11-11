import pytest

from app import sessions


@pytest.fixture(autouse=True)
def _clean_sessions():
    sessions.clear_all_sessions()
    yield
    sessions.clear_all_sessions()
