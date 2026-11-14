from aerona.catalog.image_styles import CUSTOM_STYLE_MAX_LENGTH, style_label
from aerona.core.errors import ValidationFailedError
from aerona.core.grammar import several
from aerona.db.tables.cosmos import CosmosRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.world import FateMode, ImageStyle, SonDistribution
from aerona.services.player.chronicle import tell
from aerona.services.player.lines import SETTINGS
from aerona.services.player.scope import Command, Effect, PlayerScope, player_action

MIN_PARALLELISM = 1


class WorldSettings(Command):
    fate_mode: FateMode | None = None
    son_distribution: SonDistribution | None = None
    mortal_agents_per_epoch: int | None = None
    automatic_mortal_agents: bool = False
    council_every_epochs: int | None = None
    mortal_agent_parallelism: int | None = None
    image_style: ImageStyle | None = None
    image_style_custom: str | None = None


def _set_image_style(cosmos: CosmosRow, command: WorldSettings) -> str:
    style = command.image_style or cosmos.image_style
    custom = (command.image_style_custom if command.image_style_custom is not None else cosmos.image_style_custom).strip()
    if len(custom) > CUSTOM_STYLE_MAX_LENGTH:
        raise ValidationFailedError(f"The custom image style is limited to {several(CUSTOM_STYLE_MAX_LENGTH, 'character', 'characters')}.")
    if style is ImageStyle.CUSTOM and not custom:
        raise ValidationFailedError("Describe the custom image style.")
    cosmos.image_style = style
    cosmos.image_style_custom = custom
    return f"images in the {style_label(style, custom)} style"


@player_action("settings", ActionKind.OTHER)
async def update_settings(scope: PlayerScope, command: WorldSettings) -> Effect:
    cosmos = await scope.cosmos()
    fields: list[str] = []
    if command.fate_mode is not None:
        cosmos.fate_mode = command.fate_mode
        fields.append(f"Fate {command.fate_mode.value}")
    if command.son_distribution is not None:
        cosmos.son_distribution = command.son_distribution
        fields.append(f"sons distributed {command.son_distribution.value}")
    if command.automatic_mortal_agents:
        cosmos.mortal_agents_per_epoch = None
        fields.append("mortal agents chosen automatically")
    elif command.mortal_agents_per_epoch is not None:
        if command.mortal_agents_per_epoch < 0:
            raise ValidationFailedError("The number of mortal agents cannot be negative.")
        cosmos.mortal_agents_per_epoch = command.mortal_agents_per_epoch
        fields.append(f"{command.mortal_agents_per_epoch} mortal agents each epoch")
    if command.council_every_epochs is not None:
        if command.council_every_epochs < 0:
            raise ValidationFailedError("The council interval cannot be negative (0 turns the automatic council off).")
        cosmos.council_every_epochs = command.council_every_epochs
        fields.append(f"council every {several(command.council_every_epochs, 'epoch', 'epochs')}" if command.council_every_epochs else "no automatic council")
    if command.mortal_agent_parallelism is not None:
        if command.mortal_agent_parallelism < MIN_PARALLELISM:
            raise ValidationFailedError("At least one mortal agent must be able to act at a time.")
        cosmos.mortal_agent_parallelism = command.mortal_agent_parallelism
        fields.append(f"{command.mortal_agent_parallelism} mortal agents at once")
    if command.image_style is not None or command.image_style_custom is not None:
        fields.append(_set_image_style(cosmos, command))
    if not fields:
        raise ValidationFailedError("Nothing to change in the settings.")
    ctx = await scope.context("settings")
    return Effect(await tell(ctx, SETTINGS, kind=ChronicleKind.SYSTEM, fields="; ".join(fields)))
