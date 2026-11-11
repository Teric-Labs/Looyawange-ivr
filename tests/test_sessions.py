from app import sessions


def test_new_session_starts_at_language_gate():
    state = sessions.get_session("s1", "+256700000001")
    assert state["step"] == "language"
    assert state["language"] is None
    assert state["intent"] is None
    assert state["conversation_id"] is None


def test_update_session_persists_language():
    sessions.update_session("s1", "+256700000001", language="lg", step="menu")
    state = sessions.get_session("s1", "+256700000001")
    assert state["language"] == "lg"
    assert state["step"] == "menu"
    assert sessions.has_language(state) is True


def test_language_can_be_reset_to_none():
    sessions.update_session("s1", "caller", language="sw", step="menu")
    sessions.update_session("s1", "caller", language=None, step="language")
    state = sessions.get_session("s1", "caller")
    assert state["language"] is None
    assert state["step"] == "language"
    assert sessions.has_language(state) is False


def test_sessions_isolated_by_caller():
    sessions.update_session("same", "a", language="en")
    sessions.update_session("same", "b", language="lg")
    assert sessions.get_session("same", "a")["language"] == "en"
    assert sessions.get_session("same", "b")["language"] == "lg"


def test_clear_session_removes_language_choice():
    sessions.update_session("s9", "c", language="nyn", step="menu")
    sessions.clear_session("s9", "c")
    state = sessions.get_session("s9", "c")
    assert state["language"] is None
    assert state["step"] == "language"
