from agent_zero.armor.threat_pattern import ThreatPattern, pattern


def test_pattern_builds_multiline_regex() -> None:
    built = pattern("etiqueta", r"^system:")
    assert isinstance(built, ThreatPattern)
    assert built.regex.search("hola\nsystem: x")
    assert built.label == "etiqueta"
