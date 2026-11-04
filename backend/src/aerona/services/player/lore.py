from pydantic import Field

from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.culture import IdeologyTenet, MagicSchool, RiteEffectKind, SpeakerKind, Technique
from aerona.domain.enums.society import KnowledgeBranch
from aerona.engine.lore import control
from aerona.services.player.scope import Command, Effect, PlayerScope, player_action


class EditLore(Command):
    entity_id: int
    values: dict[str, int | str | bool | dict[str, int | str] | list[int] | None] = Field(default_factory=dict)
    release: list[str] = Field(default_factory=list)


class Intelligibility(Command):
    first_id: int
    second_id: int
    value: int


class Speakers(Command):
    community_id: int
    language_id: int
    kind: SpeakerKind = SpeakerKind.SECOND
    share: int


class HolderLevel(Command):
    holder_id: int
    branch: KnowledgeBranch
    level: int


class HolderTechnique(Command):
    holder_id: int
    technique: Technique
    held: bool = True
    secret: bool = False


class CreedTenet(Command):
    ideology_id: int
    tenet: IdeologyTenet
    held: bool = True


class Adherent(Command):
    ideology_id: int
    community_id: int
    strength: int
    state: bool = False


class FoundCreed(Command):
    founder_id: int


class DeviseRite(Command):
    school: MagicSchool
    inventor_id: int


class RiteEffect(Command):
    rite_id: int
    effect: RiteEffectKind
    magnitude: int
    detail: str | None = None


class CastRite(Command):
    rite_id: int
    caster_id: int
    target_id: int | None = None


class ResolveProphecy(Command):
    prophecy_id: int
    fulfilled: bool


class Enchantment(Command):
    item_id: int
    effect: RiteEffectKind
    strength: int


class Participation(Command):
    tradition_id: int
    community_id: int
    participation: int


@player_action("lore:edit", ActionKind.EDIT_RECORD)
async def edit_lore(scope: PlayerScope, command: EditLore) -> Effect:
    await control.edit_profile(await scope.context("lore_edit"), command.entity_id, command.values, release=command.release)
    return Effect("The record is rewritten.", command.entity_id)


@player_action("language:intelligibility", ActionKind.EDIT_RECORD)
async def set_intelligibility(scope: PlayerScope, command: Intelligibility) -> Effect:
    row = await control.set_intelligibility(await scope.context("language_intelligibility"), command.first_id, command.second_id, command.value)
    return Effect(f"The two tongues now understand each other {row.value}%.", command.first_id)


@player_action("language:speakers", ActionKind.EDIT_RECORD)
async def set_speakers(scope: PlayerScope, command: Speakers) -> Effect:
    row = await control.set_speakers(await scope.context("language_speakers"), command.community_id, command.language_id, command.kind, command.share)
    return Effect(f"{row.share}% speak it." if row is not None else "No one there speaks it any more.", command.community_id)


@player_action("research:level", ActionKind.EDIT_RECORD)
async def set_level(scope: PlayerScope, command: HolderLevel) -> Effect:
    row = await control.set_level(await scope.context("research_level"), command.holder_id, command.branch, command.level)
    return Effect(f"Their {row.branch.value.replace('_', ' ')} stands at level {row.level}.", command.holder_id)


@player_action("research:technique", ActionKind.EDIT_RECORD)
async def set_technique(scope: PlayerScope, command: HolderTechnique) -> Effect:
    ctx = await scope.context("research_technique")
    row = await control.set_technique(ctx, command.holder_id, command.technique, held=command.held, secret=command.secret)
    label = command.technique.value.replace("_", " ")
    return Effect(f"They know {label}." if row is not None else f"They forget {label}.", command.holder_id)


@player_action("creed:tenet", ActionKind.EDIT_RECORD)
async def set_creed_tenet(scope: PlayerScope, command: CreedTenet) -> Effect:
    row = await control.set_creed_tenet(await scope.context("creed_tenet"), command.ideology_id, command.tenet, held=command.held)
    label = command.tenet.value.replace("_", " ")
    return Effect(f"The creed teaches {label}." if row is not None else f"The creed casts off {label}.", command.ideology_id)


@player_action("creed:adherent", ActionKind.EDIT_RECORD)
async def set_adherent(scope: PlayerScope, command: Adherent) -> Effect:
    ctx = await scope.context("creed_adherent")
    row = await control.set_adherent(ctx, command.ideology_id, command.community_id, command.strength, state=command.state)
    return Effect(f"They hold to it {row.strength}%." if row is not None else "They turn from the creed.", command.community_id)


@player_action("creed:found", ActionKind.OTHER)
async def found_creed(scope: PlayerScope, command: FoundCreed) -> Effect:
    creed = await control.found_creed(await scope.context("creed_found"), command.founder_id)
    return Effect(f"{creed.name} is taught.", creed.id, created_ids=(creed.id,))


@player_action("rite:devise", ActionKind.OTHER)
async def devise_rite(scope: PlayerScope, command: DeviseRite) -> Effect:
    rite = await control.devise_rite(await scope.context("rite_devise"), command.school, command.inventor_id)
    return Effect(f"{rite.name} is devised.", rite.id, created_ids=(rite.id,))


@player_action("rite:effect", ActionKind.EDIT_RECORD)
async def set_rite_effect(scope: PlayerScope, command: RiteEffect) -> Effect:
    row = await control.set_rite_effect(await scope.context("rite_effect"), command.rite_id, command.effect, command.magnitude, command.detail)
    label = command.effect.value.replace("_", " ")
    return Effect(f"The rite works {label} at {row.magnitude}." if row is not None else f"The rite no longer works {label}.", command.rite_id)


@player_action("rite:cast", ActionKind.OTHER)
async def cast_rite(scope: PlayerScope, command: CastRite) -> Effect:
    row = await control.cast_rite(await scope.context("rite_cast"), command.rite_id, command.caster_id, command.target_id)
    return Effect(row.effect or "The rite is worked.", command.rite_id)


@player_action("prophecy:resolve", ActionKind.OTHER)
async def resolve_prophecy(scope: PlayerScope, command: ResolveProphecy) -> Effect:
    await control.resolve_prophecy(await scope.context("prophecy_resolve"), command.prophecy_id, fulfilled=command.fulfilled)
    return Effect("What was foretold came to pass." if command.fulfilled else "The prophecy failed.", command.prophecy_id)


@player_action("item:enchant", ActionKind.EDIT_RECORD)
async def set_enchantment(scope: PlayerScope, command: Enchantment) -> Effect:
    row = await control.set_enchantment(await scope.context("item_enchant"), command.item_id, command.effect, command.strength)
    label = command.effect.value.replace("_", " ")
    return Effect(f"It holds {label} at {row.strength}." if row is not None else f"The {label} fades from it.", command.item_id)


@player_action("tradition:participation", ActionKind.EDIT_RECORD)
async def set_participation(scope: PlayerScope, command: Participation) -> Effect:
    row = await control.set_participation(await scope.context("tradition_participation"), command.tradition_id, command.community_id, command.participation)
    return Effect(f"{row.participation}% keep it.", command.tradition_id)
