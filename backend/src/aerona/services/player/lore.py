from pydantic import Field

from aerona.core.grammar import several
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.body import DamageType
from aerona.domain.enums.culture import BoostTrigger, CustomCatalog, IdeologyTenet, MagicSchool, RiteEffectKind, SpeakerKind, SummonForm, Technique
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.society import KnowledgeBranch
from aerona.engine.lore import control, kinds, learning_control, research_control
from aerona.services.player.scope import Command, Effect, PlayerScope, player_action


class EditLore(Command):
    entity_id: int
    values: dict[str, int | str | bool | dict[str, int | str] | list[int] | None] = Field(default_factory=dict)
    release: list[str] = Field(default_factory=list)


LoreValue = int | str | bool | dict[str, int | str] | list[int] | list[str] | None


class CreateLore(Command):
    entity_type: EntityType
    name: str
    description: str = ""
    world_id: int | None = None
    location_id: int | None = None
    power: int = 3
    values: dict[str, LoreValue] = Field(default_factory=dict)


class CreateKind(Command):
    catalog: CustomCatalog
    base: str
    name: str
    description: str = ""
    params: dict[str, int | str | list[str] | dict[str, int] | None] = Field(default_factory=dict)
    world_id: int | None = None


class EditKind(Command):
    kind_id: int
    values: dict[str, int | str | dict[str, int | str | list[str] | dict[str, int] | None] | None] = Field(default_factory=dict)


class KindTarget(Command):
    kind_id: int


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


class ResearchFocus(Command):
    holder_id: int
    technique: Technique | None = None
    options: list[Technique] | None = None
    hold: bool = True


class Institution(Command):
    community_id: int
    technique: Technique
    present: bool = True
    values: dict[str, int | bool] = Field(default_factory=dict)
    release: list[str] = Field(default_factory=list)


class GrantBoost(Command):
    holder_id: int
    technique: Technique
    trigger: BoostTrigger
    progress: int


class EditBoost(Command):
    boost_id: int
    values: dict[str, int | str] = Field(default_factory=dict)


class BoostTarget(Command):
    boost_id: int


class EditHolder(Command):
    holder_id: int
    branch: KnowledgeBranch
    values: dict[str, int | bool] = Field(default_factory=dict)
    release: list[str] = Field(default_factory=list)


class HolderCustomTechnique(Command):
    holder_id: int
    kind_id: int
    held: bool = True
    secret: bool = False


class CreedCustomTenet(Command):
    ideology_id: int
    kind_id: int
    held: bool = True


class SuppressCreed(Command):
    ideology_id: int
    authority_id: int | None = None


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
    damage_type: DamageType | None = None
    summon_form: SummonForm | None = None
    custom_kind_id: int | None = None


class TeachRite(Command):
    rite_id: int
    holder_id: int
    taught: bool = True


class ForbidRite(Command):
    rite_id: int
    authority_id: int
    forbidden: bool = True


class RiteTarget(Command):
    rite_id: int


class RiteRequirements(Command):
    rite_id: int
    requirements: dict[str, int | str | bool] = Field(default_factory=dict)


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


@player_action("research:focus", ActionKind.EDIT_RECORD)
async def set_focus(scope: PlayerScope, command: ResearchFocus) -> Effect:
    ctx = await scope.context("research_focus")
    row = await research_control.set_focus(ctx, command.holder_id, command.technique, command.options, hold=command.hold)
    if row is None:
        return Effect("Their scholars are free to choose their own work.", command.holder_id)
    return Effect(f"Their scholars turn to {row.technique.value.replace('_', ' ')}.", command.holder_id)


@player_action("research:institution", ActionKind.EDIT_RECORD)
async def set_institution(scope: PlayerScope, command: Institution) -> Effect:
    ctx = await scope.context("research_institution")
    row = await research_control.set_institution(ctx, command.community_id, command.technique, command.values, command.release, present=command.present)
    label = command.technique.value.replace("_", " ")
    if row is None:
        return Effect(f"{label.capitalize()} is gone from there.", command.community_id)
    return Effect(f"{label.capitalize()} is {'embraced' if row.embraced else 'known but refused'} there.", command.community_id)


@player_action("research:boost", ActionKind.EDIT_RECORD)
async def grant_boost(scope: PlayerScope, command: GrantBoost) -> Effect:
    row = await research_control.grant_boost(await scope.context("research_boost"), command.holder_id, command.technique, command.trigger, command.progress)
    return Effect(f"A boost pushes their {row.technique.value.replace('_', ' ')} {row.progress}% closer.", command.holder_id)


@player_action("research:boost_edit", ActionKind.EDIT_RECORD)
async def edit_boost(scope: PlayerScope, command: EditBoost) -> Effect:
    row = await research_control.edit_boost(await scope.context("research_boost_edit"), command.boost_id, command.values)
    return Effect("The boost is rewritten.", row.holder_entity_id)


@player_action("research:boost_remove", ActionKind.EDIT_RECORD)
async def remove_boost(scope: PlayerScope, command: BoostTarget) -> Effect:
    await research_control.remove_boost(await scope.context("research_boost_remove"), command.boost_id)
    return Effect("The boost is struck from the record.")


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
    shape = control.EffectShape(command.detail, command.damage_type, command.summon_form, command.custom_kind_id)
    row = await control.set_rite_effect(await scope.context("rite_effect"), command.rite_id, command.effect, command.magnitude, shape)
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


@player_action("lore:create", ActionKind.OTHER)
async def create_lore(scope: PlayerScope, command: CreateLore) -> Effect:
    entity = await control.create_lore(
        await scope.context("lore_create"),
        command.entity_type,
        name=command.name,
        description=command.description,
        world_id=command.world_id,
        location_id=command.location_id,
        power=command.power,
        values=command.values,
    )
    return Effect(f"{entity.name} enters the world.", entity.id, created_ids=(entity.id,))


@player_action("kind:create", ActionKind.EDIT_RECORD)
async def create_kind(scope: PlayerScope, command: CreateKind) -> Effect:
    ctx = await scope.context("kind_create")
    row = await kinds.create_kind(
        ctx, command.catalog, command.base, command.name, description=command.description, params=command.params, world_id=command.world_id
    )
    return Effect(f"A new {command.catalog.value.replace('_', ' ')} is named: {row.name}.", None)


@player_action("kind:edit", ActionKind.EDIT_RECORD)
async def edit_kind(scope: PlayerScope, command: EditKind) -> Effect:
    row = await kinds.edit_kind(await scope.context("kind_edit"), command.kind_id, command.values)
    return Effect(f"{row.name} is reshaped.", None)


@player_action("kind:delete", ActionKind.EDIT_RECORD)
async def delete_kind(scope: PlayerScope, command: KindTarget) -> Effect:
    row = await kinds.delete_kind(await scope.context("kind_delete"), command.kind_id)
    return Effect(f"{row.name} is no more.", None)


@player_action("rite:teach", ActionKind.EDIT_RECORD)
async def teach_rite(scope: PlayerScope, command: TeachRite) -> Effect:
    taught = await control.teach_rite(await scope.context("rite_teach"), command.rite_id, command.holder_id, taught=command.taught)
    return Effect("The rite is taught." if taught else "The rite is forgotten.", command.rite_id)


@player_action("rite:forbid", ActionKind.EDIT_RECORD)
async def forbid_rite(scope: PlayerScope, command: ForbidRite) -> Effect:
    held = await control.forbid_rite(await scope.context("rite_forbid"), command.rite_id, command.authority_id, forbidden=command.forbidden)
    return Effect(f"The rite is forbidden in {several(len(held), 'place', 'places')}." if held else "The rite is free again.", command.rite_id)


@player_action("rite:dispel", ActionKind.OTHER)
async def dispel_rite(scope: PlayerScope, command: RiteTarget) -> Effect:
    casting = await control.dispel_rite(await scope.context("rite_dispel"), command.rite_id)
    return Effect(f"Undone: {casting.effect}", command.rite_id)


@player_action("rite:requirements", ActionKind.EDIT_RECORD)
async def set_rite_requirements(scope: PlayerScope, command: RiteRequirements) -> Effect:
    row = await control.set_requirements(await scope.context("rite_requirements"), command.rite_id, command.requirements)
    return Effect(f"The rite now asks {several(len(row.requirements), 'thing', 'things')} of its caster.", command.rite_id)


@player_action("research:holder", ActionKind.EDIT_RECORD)
async def edit_holder(scope: PlayerScope, command: EditHolder) -> Effect:
    row = await learning_control.edit_holder(await scope.context("research_holder"), command.holder_id, command.branch, command.values, command.release)
    return Effect(f"Their {row.branch.value.replace('_', ' ')} stands at level {row.level}, {row.progress}% toward the next.", command.holder_id)


@player_action("research:custom_technique", ActionKind.EDIT_RECORD)
async def set_custom_technique(scope: PlayerScope, command: HolderCustomTechnique) -> Effect:
    ctx = await scope.context("research_custom_technique")
    row = await learning_control.set_custom_technique(ctx, command.holder_id, command.kind_id, held=command.held, secret=command.secret)
    return Effect("They learn your technique." if row is not None else "They forget your technique.", command.holder_id)


@player_action("creed:custom_tenet", ActionKind.EDIT_RECORD)
async def set_custom_tenet(scope: PlayerScope, command: CreedCustomTenet) -> Effect:
    row = await learning_control.set_custom_tenet(await scope.context("creed_custom_tenet"), command.ideology_id, command.kind_id, held=command.held)
    return Effect("The creed takes up your tenet." if row is not None else "The creed casts off your tenet.", command.ideology_id)


@player_action("creed:suppress", ActionKind.EDIT_RECORD)
async def suppress_creed(scope: PlayerScope, command: SuppressCreed) -> Effect:
    count = await learning_control.suppress_creed(await scope.context("creed_suppress"), command.ideology_id, command.authority_id)
    return Effect(f"The creed is hunted down among {count} of its followers.", command.ideology_id)
