from agent_zero.walkthrough.report import Report


def test_report_is_ok_only_when_every_check_passes() -> None:
    report = Report()
    assert not report.ok

    report.add("Registry", "publicar", True)
    report.add("Runtime", "run", False, "falló")

    assert not report.ok
    assert "FALLA [Runtime] run -> falló" in report.render()
    assert "1/2 comprobaciones pasaron" in report.render()
