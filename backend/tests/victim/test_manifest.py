from agent_zero.armor.model_armor import ModelArmor
from agent_zero.armor.models import ArmorAction, Surface
from agent_zero.victim.manifest import SUPPORT_AGENT_ID, support_manifest


def test_support_manifest_grants_only_read_tools_and_memory() -> None:
    manifest = support_manifest()

    assert manifest.agent_id == SUPPORT_AGENT_ID
    assert {tool.name for tool in manifest.tools} == {"get_order", "search_knowledge"}
    assert "tool:request_refund" not in manifest.scopes


def test_support_prompt_passes_model_armor() -> None:
    verdict = ModelArmor().screen(support_manifest().system_prompt, Surface.SYSTEM_PROMPT)

    assert verdict.action is ArmorAction.ALLOW
