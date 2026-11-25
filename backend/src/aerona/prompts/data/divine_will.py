from dataclasses import dataclass

from aerona.domain.enums.divine_will import DivineWillMode
from aerona.prompts.ids import PromptId


@dataclass(frozen=True)
class ModeText:
    name: str
    purpose: str
    prompt_id: PromptId
    changes_world: bool


M = DivineWillMode
MODE_TEXTS: dict[DivineWillMode, ModeText] = {
    M.COMMAND: ModeText(
        "Command", "Acts on the world now, through the same acts the app offers; a costly or destructive act asks first.", PromptId.DIVINE_WILL_COMMAND, True
    ),
    M.PLAN: ModeText("Plan", "Writes a plan of acts that runs only once it is approved and started.", PromptId.DIVINE_WILL_PLAN, True),
    M.ASK_LORE: ModeText("Ask Lore", "Answers questions about the world from its record; changes nothing.", PromptId.DIVINE_WILL_ASK_LORE, False),
    M.CREATIVE_WORK: ModeText(
        "Creative Work", "Writes works about the world and helps think ideas through; changes nothing.", PromptId.DIVINE_WILL_CREATIVE_WORK, False
    ),
    M.MECHANICS_GUIDE: ModeText("Mechanics Guide", "Explains the game's rules and mechanics; changes nothing.", PromptId.DIVINE_WILL_MECHANICS_GUIDE, False),
    M.FORESIGHT: ModeText("Foresight", "Shows where acts may lead by living a copy of the world; changes nothing.", PromptId.DIVINE_WILL_FORESIGHT, False),
}
