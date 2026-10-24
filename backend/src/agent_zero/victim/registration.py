from agent_zero.fleet.fleet_builder import Fleet
from agent_zero.llm.gateway import LlmGateway
from agent_zero.llm.models import ModelRole
from agent_zero.victim.reply_composer import ReplyComposer
from agent_zero.victim.store_tools import register_store_tools
from agent_zero.victim.support_handler import SupportConversationHandler


def register_victim(fleet: Fleet, llm: LlmGateway) -> None:
    register_store_tools(fleet.tools)
    composer = ReplyComposer(llm.model(ModelRole.VICTIM), fleet.armor)
    fleet.handlers.register(SupportConversationHandler(fleet, composer))
