from agent_zero.runtime.models import TERMINAL_STATUSES, RunStatus


def test_terminal_statuses() -> None:
    assert RunStatus.SUCCEEDED.terminal
    assert RunStatus.FAILED.terminal
    assert RunStatus.CANCELLED.terminal
    assert not RunStatus.QUEUED.terminal
    assert not RunStatus.WAITING.terminal
    assert len(TERMINAL_STATUSES) == 3
