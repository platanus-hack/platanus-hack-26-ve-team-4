from agent_zero.shared.classification import DataClassification


def test_levels_are_ordered() -> None:
    ordered = [
        DataClassification.PUBLIC,
        DataClassification.INTERNAL,
        DataClassification.CONFIDENTIAL,
        DataClassification.RESTRICTED,
    ]
    assert sorted(reversed(ordered)) == ordered
    assert DataClassification.INTERNAL < DataClassification.RESTRICTED
    assert DataClassification.RESTRICTED >= DataClassification.RESTRICTED
    assert DataClassification.PUBLIC <= DataClassification.INTERNAL
    assert DataClassification.CONFIDENTIAL > DataClassification.INTERNAL


def test_covers_compares_levels() -> None:
    assert DataClassification.CONFIDENTIAL.covers(DataClassification.INTERNAL)
    assert not DataClassification.INTERNAL.covers(DataClassification.RESTRICTED)
