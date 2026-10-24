import pytest

from agent_zero.runtime.admission import AdmissionDeniedError
from tests.runtime.support import FakeAdmission


async def test_fake_admission_follows_protocol() -> None:
    admission = FakeAdmission({"malo": "deprecado"})
    principal = await admission.admit("bueno", "1.0.0")
    assert principal.agent_id == "bueno"
    with pytest.raises(AdmissionDeniedError) as denied:
        await admission.admit("malo", "1.0.0")
    assert denied.value.reason == "deprecado"
    assert "Admisión denegada" in str(denied.value)
