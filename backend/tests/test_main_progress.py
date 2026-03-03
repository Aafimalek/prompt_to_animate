from backend.main import should_emit_progress


def test_should_emit_progress_first_event():
    emit, signature = should_emit_progress(None, {"step": 2, "status": "composing", "message": "A"})
    assert emit is True
    assert signature == (2, "composing", "A")


def test_should_emit_progress_same_signature_is_suppressed():
    last_signature = (4, "validating", "Checking...")
    emit, signature = should_emit_progress(
        last_signature,
        {"step": 4, "status": "validating", "message": "Checking..."},
    )
    assert emit is False
    assert signature == last_signature


def test_should_emit_progress_when_message_changes_same_step():
    last_signature = (4, "validating", "Checking...")
    emit, signature = should_emit_progress(
        last_signature,
        {"step": 4, "status": "repairing", "message": "Repair attempt 1"},
    )
    assert emit is True
    assert signature == (4, "repairing", "Repair attempt 1")

