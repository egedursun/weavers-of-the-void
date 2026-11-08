from dataclasses import dataclass, field

from pydantic import BaseModel, Field
from sqlalchemy import func, select

from aerona.catalog.entity_types import entity_type_spec
from aerona.catalog.rarities import build_rarity_table, name_similarity_policy
from aerona.catalog.stats import max_essence, max_hp
from aerona.constants.player import PERSONALITY_FIELD_MAX_LENGTH, SON_NAME_MAX_LENGTH, SON_PLAN_MAX_LENGTH
from aerona.constants.schema import TITLE_MAX_LENGTH
from aerona.core.errors import ValidationFailedError
from aerona.core.grammar import an
from aerona.db.repositories.bonds import BondDraft, BondRepository
from aerona.db.repositories.entities import EntityDraft, EntityRepository
from aerona.db.repositories.names import NameRepository, normalize_name
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.cosmic_state import ResourceMechanicRow
from aerona.db.tables.entities import EntityRow, EntityTraitRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.entity import AGENT_TYPES, COMMUNITY_TYPES, EngineKind, EntityFlag, EntityOrigin, EntityStatus, EntityType
from aerona.domain.enums.foreign_god import ForeignGodStatus
from aerona.domain.enums.limits import MAX_STARS, MIN_STARS, PERCENT_MAX, PERCENT_MIN
from aerona.domain.enums.rarity import Rarity
from aerona.domain.enums.society import CreatureTrait, NaturalLaw, ResourceMechanic
from aerona.domain.enums.son import Passion, SonStatus, Stat
from aerona.domain.enums.world import Discovery, SonDistribution
from aerona.domain.models.entity_stats import LegendStats
from aerona.domain.models.stats import PASSION_CEILING, PASSION_FLOOR, STAT_CEILING, STAT_FLOOR
from aerona.engine.context import TickContext
from aerona.engine.cosmos.resources import set_mechanics
from aerona.engine.gods.progress import star_requirement
from aerona.engine.phases.world_balance import balance_sons
from aerona.engine.primitives.faith import worship_creator
from aerona.engine.primitives.numbers import clamp_percent
from aerona.engine.primitives.renames import rewrite_name
from aerona.engine.primitives.stats import set_stats, stat
from aerona.events.kinds import EventKind
from aerona.services.player import guards
from aerona.services.player.chronicle import hand, tell
from aerona.services.player.lines import (
    ASCENDED,
    ASCENSION_MYTH,
    ENTITY_MOVED,
    PATRON_CREATOR,
    PATRON_FOREIGN,
    PATRON_NONE,
    PATRON_SON,
    SON_DISTRIBUTED,
    SON_EDITED,
    SON_IMAGE_PROMPT,
    SON_PROTECTION_CLEARED,
    SON_RARITY,
    SON_RENAMED,
    SON_SENT,
    STAR_ADDED,
    STAT_SET,
    TAGS_SET,
)
from aerona.services.player.scope import Command, Effect, PlayerScope, player_action

ASSIGNABLE_FLAGS = frozenset(
    {
        EntityFlag.WONDER,
        EntityFlag.CURSED,
        EntityFlag.GODLESS,
        EntityFlag.RUIN,
        EntityFlag.MEGAFAUNA,
        EntityFlag.INVASIVE,
        EntityFlag.ORIGINAL_RESOURCE,
        EntityFlag.CHOSEN,
        EntityFlag.NATIVE,
        EntityFlag.COLONY,
        EntityFlag.INDEPENDENT,
        EntityFlag.EMPIRE,
        EntityFlag.OUTER_CULT,
        EntityFlag.FAIRY_TALE,
        EntityFlag.IMMORTAL,
        EntityFlag.WORSHIPS_PLANET,
        EntityFlag.SOUL_BOUND,
        EntityFlag.OATHBREAKER,
        EntityFlag.EXILE,
        EntityFlag.SOUL_HARVESTER,
        EntityFlag.TWO_TIMED,
        EntityFlag.FEDERATION,
    }
)
WORSHIPPER_TYPES = frozenset(COMMUNITY_TYPES | {EntityType.MORTAL})
SELECTABLE_AGENT_TYPES = frozenset(AGENT_TYPES - {EntityType.ARMY})
PERSONALITY_FIELDS = ("appearance", "temperament", "obsession", "fear", "speech_style", "secret")
ASCENSION_SUBTYPE = "ascension myth"


class SonWorld(Command):
    son_id: int
    world_id: int


class SonTarget(Command):
    son_id: int


class SonImagePrompt(Command):
    son_id: int
    image_prompt: str = ""


class MoveEntity(Command):
    entity_id: int
    location_id: int


class AssignPatron(Command):
    entity_id: int
    son_id: int | None = None
    creator: bool = False
    foreign_god_id: int | None = None


class SetStat(Command):
    entity_id: int
    stat: str
    value: float


class SetTags(Command):
    entity_id: int
    add_flags: tuple[EntityFlag, ...] = ()
    remove_flags: tuple[EntityFlag, ...] = ()
    add_traits: tuple[CreatureTrait, ...] = ()
    remove_traits: tuple[CreatureTrait, ...] = ()
    add_mechanics: tuple[ResourceMechanic, ...] = ()
    remove_mechanics: tuple[ResourceMechanic, ...] = ()
    law: NaturalLaw | None = None


class SelectAgent(Command):
    entity_id: int
    selected: bool = True


class SonPersonality(Command):
    appearance: str | None = None
    temperament: str | None = None
    obsession: str | None = None
    fear: str | None = None
    speech_style: str | None = None
    secret: str | None = None


class SonResources(Command):
    essence: int | None = None
    hp: int | None = None
    fame: int | None = None
    faith: int | None = None
    level: int | None = None
    stars: int | None = None
    existence: int | None = None
    xp: int | None = None
    sanity: int | None = None


class EditSon(Command):
    son_id: int
    name: str | None = None
    title: str | None = None
    plan: str | None = None
    personality: SonPersonality | None = None
    passions: dict[Passion, float] = Field(default_factory=dict)
    stats: dict[Stat, float] = Field(default_factory=dict)
    rarity: Rarity | None = None
    resources: SonResources | None = None


class DistributionCandidate(BaseModel):
    son_id: int
    name: str
    world_id: int | None
    score: int
    protected: bool


class DistributionPreview(BaseModel):
    candidates: list[DistributionCandidate]
    next_son_id: int | None
    godless_world_ids: list[int]


def protected(protection_epochs: int, son: SonRow, epoch: int) -> bool:
    return son.manually_assigned_epoch is not None and epoch - son.manually_assigned_epoch < protection_epochs


@player_action("son:world", ActionKind.EDIT_RECORD)
async def assign_son_world(scope: PlayerScope, command: SonWorld) -> Effect:
    son = await guards.living_son(scope.session, command.son_id)
    world = await guards.open_world(scope.session, command.world_id)
    if son.current_world_id == world.id:
        raise ValidationFailedError(f"{son.name} is already in the world {world.name}.")
    epoch = await scope.epoch()
    son.current_world_id = world.id
    son.manually_assigned_epoch = epoch
    creator = await scope.creator()
    ctx = await scope.context("son_world")
    message = await hand(ctx, creator, SON_SENT, son_id=son.id, world_id=world.id, son=son.name, world=world.name)
    return Effect(message, son.id, values={"protected_until": epoch + scope.rules.god_hand.assignment_protection_epochs})


@player_action("son:protection", ActionKind.EDIT_RECORD)
async def clear_son_protection(scope: PlayerScope, command: SonTarget) -> Effect:
    son = await guards.son(scope.session, command.son_id)
    if son.manually_assigned_epoch is None:
        raise ValidationFailedError(f"{son.name} is not protected from the distribution of sons.")
    son.manually_assigned_epoch = None
    ctx = await scope.context("son_protection")
    return Effect(await tell(ctx, SON_PROTECTION_CLEARED, son_id=son.id, son=son.name), son.id)


async def _worshippers_in(scope: PlayerScope, son: SonRow) -> int:
    if son.current_world_id is None:
        return 0
    statement = (
        select(func.count())
        .select_from(BondRow)
        .join(EntityRow, EntityRow.id == BondRow.source_node_id)
        .where(
            BondRow.target_node_id == son.id,
            BondRow.kind == BondKind.WORSHIPS,
            BondRow.state == BondState.ACTIVE,
            EntityRow.world_id == son.current_world_id,
            EntityRow.status == EntityStatus.CANON,
        )
    )
    return int(await scope.session.scalar(statement) or 0)


async def distribution_candidates(scope: PlayerScope) -> list[DistributionCandidate]:
    hand_rules = scope.rules.god_hand
    epoch = await scope.epoch()
    active = list(await scope.session.scalars(select(SonRow).where(SonRow.status == SonStatus.ACTIVE).order_by(SonRow.id)))
    per_world: dict[int | None, int] = {}
    for son in active:
        per_world[son.current_world_id] = per_world.get(son.current_world_id, 0) + 1
    worlds = {world.id: world for world in await scope.session.scalars(select(WorldRow))}
    found: list[DistributionCandidate] = []
    for son in active:
        if per_world.get(son.current_world_id, 0) < hand_rules.dispatch_donor_min_sons:
            continue
        home = worlds.get(son.current_world_id) if son.current_world_id is not None else None
        guardian = home is not None and home.patron_son_id == son.id
        score = await _worshippers_in(scope, son) + (hand_rules.protector_bond_weight if guardian else 0)
        found.append(
            DistributionCandidate(
                son_id=son.id,
                name=son.name,
                world_id=son.current_world_id,
                score=score,
                protected=protected(hand_rules.assignment_protection_epochs, son, epoch),
            )
        )
    return sorted(found, key=lambda item: (item.score, item.son_id))


async def _godless_worlds(scope: PlayerScope) -> list[WorldRow]:
    worlds = list(await scope.session.scalars(select(WorldRow).where(WorldRow.discovery != Discovery.FORGOTTEN).order_by(WorldRow.id)))
    found: list[WorldRow] = []
    for world in worlds:
        has_son = await scope.session.scalar(select(SonRow.id).where(SonRow.current_world_id == world.id, SonRow.status == SonStatus.ACTIVE).limit(1))
        if has_son is not None:
            continue
        inhabited = await scope.session.scalar(
            select(EntityRow.id)
            .where(EntityRow.world_id == world.id, EntityRow.status == EntityStatus.CANON, EntityRow.entity_type.in_(list(WORSHIPPER_TYPES)))
            .limit(1)
        )
        if inhabited is not None:
            found.append(world)
    return found


async def distribution_preview(scope: PlayerScope) -> DistributionPreview:
    candidates = await distribution_candidates(scope)
    movable = [item for item in candidates if not item.protected]
    return DistributionPreview(
        candidates=candidates,
        next_son_id=movable[0].son_id if movable else None,
        godless_world_ids=[world.id for world in await _godless_worlds(scope)],
    )


async def distribute_sons(scope: PlayerScope, ctx: TickContext) -> int:
    moved = 0
    for world in await _godless_worlds(scope):
        candidates = [item for item in await distribution_candidates(scope) if not item.protected]
        if not candidates:
            break
        son = await guards.son(scope.session, candidates[0].son_id)
        son.current_world_id = world.id
        await scope.session.flush()
        text = await tell(ctx, SON_DISTRIBUTED, son_id=son.id, world_id=world.id, kind=ChronicleKind.COSMIC, son=son.name, world=world.name)
        scope.publish(EventKind.SON_DISTRIBUTED, {"son_id": son.id, "world_id": world.id, "text": text})
        moved += 1
    return moved


async def auto_distribute(scope: PlayerScope, ctx: TickContext) -> int:
    if (await scope.cosmos()).son_distribution is not SonDistribution.AUTO:
        return 0
    return await distribute_sons(scope, ctx) + await balance_sons(ctx)


class DistributeSons(Command):
    pass


@player_action("son:distribute", ActionKind.EDIT_RECORD)
async def distribute_now(scope: PlayerScope, command: DistributeSons) -> Effect:
    ctx = await scope.context("distribute_sons")
    moved = await distribute_sons(scope, ctx)
    return Effect(f"{moved} sons turned to godless worlds.", values={"moved": moved})


async def _descendants(scope: PlayerScope, root_id: int) -> list[EntityRow]:
    found: list[EntityRow] = []
    frontier = [root_id]
    seen = {root_id}
    while frontier:
        children = list(await scope.session.scalars(select(EntityRow).where(EntityRow.location_id.in_(frontier)).order_by(EntityRow.id)))
        frontier = []
        for child in children:
            if child.id not in seen:
                seen.add(child.id)
                found.append(child)
                frontier.append(child.id)
    return found


@player_action("entity:move", ActionKind.EDIT_RECORD)
async def move_entity(scope: PlayerScope, command: MoveEntity) -> Effect:
    target = await guards.entity(scope.session, command.entity_id)
    location = await guards.entity(scope.session, command.location_id)
    if target.id == location.id:
        raise ValidationFailedError("A thing cannot be moved inside itself.")
    spec = entity_type_spec(target.entity_type)
    if location.entity_type not in spec.containers:
        allowed = ", ".join(sorted(item.value for item in spec.containers)) or "nowhere"
        raise ValidationFailedError(
            f"{an(target.entity_type.value, capital=True)} cannot be placed inside {an(location.entity_type.value)}; possible: {allowed}."
        )
    epoch = await scope.epoch()
    await EntityRepository(scope.session).move(target, location.id, epoch)
    target.map_x = None
    target.map_y = None
    for child in await _descendants(scope, target.id):
        child.world_id = target.world_id
        child.map_x = None
        child.map_y = None
    cosmos = await scope.cosmos()
    cosmos.map_version += 1
    creator = await scope.creator()
    ctx = await scope.context("move")
    message = await hand(ctx, creator, ENTITY_MOVED, ids=[target.id, location.id], entity=target.name, location=location.name)
    return Effect(message, target.id)


async def _close_worship(scope: PlayerScope, entity_id: int, epoch: int) -> int:
    worship = await BondRepository(scope.session).outgoing(entity_id, BondKind.WORSHIPS)
    for bond in worship:
        await BondRepository(scope.session).deactivate(bond, epoch, "the god's command")
    return len(worship)


@player_action("entity:patron", ActionKind.WORSHIP)
async def assign_patron(scope: PlayerScope, command: AssignPatron) -> Effect:
    target = await guards.canon_entity(scope.session, command.entity_id)
    if target.entity_type not in WORSHIPPER_TYPES:
        raise ValidationFailedError("Only communities and mortals worship.")
    creator = await scope.creator()
    epoch = await scope.epoch()
    entities = EntityRepository(scope.session)
    ctx = await scope.context("patron")
    if command.foreign_god_id is not None:
        god = await guards.foreign_god(scope.session, command.foreign_god_id)
        if god.status is ForeignGodStatus.DEAD:
            raise ValidationFailedError(f"{god.name} is dead; nobody worships a dead god.")
        await _close_worship(scope, target.id, epoch)
        await BondRepository(scope.session).connect(BondDraft(target.id, god.id, BondKind.WORSHIPS, epoch, "the god's command"))
        await entities.remove_flag(target.id, EntityFlag.GODLESS)
        return Effect(await hand(ctx, creator, PATRON_FOREIGN, ids=[target.id], entity=target.name, god=god.name), target.id)
    if command.creator:
        await _close_worship(scope, target.id, epoch)
        await worship_creator(scope.session, target, epoch, "the god's command")
        await entities.remove_flag(target.id, EntityFlag.GODLESS)
        return Effect(await hand(ctx, creator, PATRON_CREATOR, ids=[target.id], entity=target.name), target.id)
    if command.son_id is not None:
        son = await guards.son(scope.session, command.son_id)
        if not son.alive:
            raise ValidationFailedError(f"{son.name} is dead; only a resurrection order worships them.")
        await _close_worship(scope, target.id, epoch)
        await BondRepository(scope.session).connect(BondDraft(target.id, son.id, BondKind.WORSHIPS, epoch, "the god's command"))
        await entities.remove_flag(target.id, EntityFlag.GODLESS)
        return Effect(await hand(ctx, creator, PATRON_SON, ids=[target.id], son_id=son.id, entity=target.name, son=son.name), target.id)
    await _close_worship(scope, target.id, epoch)
    await entities.add_flag(target.id, EntityFlag.GODLESS, epoch)
    return Effect(await hand(ctx, creator, PATRON_NONE, ids=[target.id], entity=target.name), target.id)


@player_action("entity:stat", ActionKind.EDIT_RECORD)
async def set_stat(scope: PlayerScope, command: SetStat) -> Effect:
    target = await guards.entity(scope.session, command.entity_id)
    key = command.stat.strip()
    if key == "sanity":
        old = target.sanity
        target.sanity = clamp_percent(command.value)
        new: int | None = target.sanity
    else:
        field = entity_type_spec(target.entity_type).stat(key)
        high: int | None
        if field is None and key == "devotion" and "devotion" in type(target.stats).model_fields:
            low, high = 0, scope.rules.death.devotion_cap
        elif field is not None and key in type(target.stats).model_fields:
            low, high = field.bounds(scope.rules)
        else:
            raise ValidationFailedError(f'There is no stat "{key}" for {an(target.entity_type.value)}.')
        old = stat(target, key)
        value = max(low, round(command.value))
        new = min(high, value) if high is not None else value
        set_stats(target, **{key: new})
    creator = await scope.creator()
    ctx = await scope.context("stat")
    message = await hand(ctx, creator, STAT_SET, ids=[target.id], entity=target.name, stat=key, old="-" if old is None else old, new=new)
    return Effect(message, target.id)


async def _mechanics_of(scope: PlayerScope, resource: EntityRow) -> list[ResourceMechanic]:
    extra = list(await scope.session.scalars(select(ResourceMechanicRow.mechanic).where(ResourceMechanicRow.entity_id == resource.id)))
    return [*([resource.resource_mechanic] if resource.resource_mechanic else []), *extra]


@dataclass
class MarkChanges:
    added: list[str] = field(default_factory=list)
    removed: list[str] = field(default_factory=list)

    def text(self) -> str:
        return ", ".join([*(f"+{item}" for item in self.added), *(f"-{item}" for item in self.removed)])


async def _change_flags(scope: PlayerScope, target: EntityRow, command: SetTags, changes: MarkChanges) -> None:
    refused = sorted(flag.value for flag in (*command.add_flags, *command.remove_flags) if flag not in ASSIGNABLE_FLAGS)
    if refused:
        allowed = ", ".join(sorted(flag.value for flag in ASSIGNABLE_FLAGS))
        raise ValidationFailedError(f"These marks cannot be assigned by hand: {', '.join(refused)}. Assignable: {allowed}.")
    entities = EntityRepository(scope.session)
    epoch = await scope.epoch()
    changes.added += [flag.value for flag in command.add_flags if await entities.add_flag(target.id, flag, epoch)]
    changes.removed += [flag.value for flag in command.remove_flags if await entities.remove_flag(target.id, flag)]


async def _change_traits(scope: PlayerScope, target: EntityRow, command: SetTags, changes: MarkChanges) -> None:
    entities = EntityRepository(scope.session)
    changes.added += [f"trait:{trait.value}" for trait in command.add_traits if await entities.add_trait(target.id, trait)]
    for trait in command.remove_traits:
        row = await scope.session.get(EntityTraitRow, (target.id, trait))
        if row is not None:
            await scope.session.delete(row)
            changes.removed.append(f"trait:{trait.value}")


async def _change_mechanics(scope: PlayerScope, target: EntityRow, command: SetTags, changes: MarkChanges) -> None:
    if not command.add_mechanics and not command.remove_mechanics:
        return
    current = await _mechanics_of(scope, target)
    wanted = [item for item in dict.fromkeys([*current, *command.add_mechanics]) if item not in command.remove_mechanics]
    await set_mechanics(scope.session, target, wanted, target.sacred_to_son_id)
    changes.added += [f"mechanic:{item.value}" for item in wanted if item not in current]
    changes.removed += [f"mechanic:{item.value}" for item in current if item not in wanted]


def _change_law(target: EntityRow, law: NaturalLaw | None, changes: MarkChanges) -> None:
    if law is None:
        return
    if target.entity_type is not EntityType.NATURAL_LAW:
        raise ValidationFailedError("Only a natural law record carries a law.")
    if target.natural_law is not law:
        target.natural_law = law
        changes.added.append(f"law:{law.value}")


@player_action("entity:tags", ActionKind.EDIT_RECORD)
async def set_tags(scope: PlayerScope, command: SetTags) -> Effect:
    target = await guards.entity(scope.session, command.entity_id)
    changes = MarkChanges()
    await _change_flags(scope, target, command, changes)
    await _change_traits(scope, target, command, changes)
    await _change_mechanics(scope, target, command, changes)
    _change_law(target, command.law, changes)
    await scope.session.flush()
    if not changes.added and not changes.removed:
        raise ValidationFailedError(f"Nothing changed on {target.name}.")
    creator = await scope.creator()
    ctx = await scope.context("tags")
    return Effect(await hand(ctx, creator, TAGS_SET, ids=[target.id], entity=target.name, changes=changes.text()), target.id)


@player_action("entity:agent", ActionKind.EDIT_RECORD)
async def select_agent(scope: PlayerScope, command: SelectAgent) -> Effect:
    target = await guards.entity(scope.session, command.entity_id)
    if target.entity_type not in SELECTABLE_AGENT_TYPES:
        raise ValidationFailedError("This entity cannot act as an agent.")
    entities = EntityRepository(scope.session)
    if command.selected:
        await entities.add_flag(target.id, EntityFlag.AGENT_SELECTED, await scope.epoch())
        return Effect(f"{target.name} will act as a mortal agent next epoch.", target.id)
    await entities.remove_flag(target.id, EntityFlag.AGENT_SELECTED)
    return Effect(f"{target.name} is no longer singled out as an agent.", target.id)


@player_action("son:image_prompt", ActionKind.EDIT_RECORD)
async def set_son_image_prompt(scope: PlayerScope, command: SonImagePrompt) -> Effect:
    son = await guards.son(scope.session, command.son_id)
    son.image_prompt = command.image_prompt.strip() or None
    ctx = await scope.context("son_prompt")
    return Effect(await tell(ctx, SON_IMAGE_PROMPT, son_id=son.id, son=son.name), son.id)


async def _rename_son(scope: PlayerScope, son: SonRow, requested: str) -> str | None:
    name = requested.strip()[:SON_NAME_MAX_LENGTH]
    if not name:
        raise ValidationFailedError("A son's name cannot be empty.")
    if normalize_name(name) == normalize_name(son.name):
        return None
    names = NameRepository(scope.session)
    if await names.is_taken(name, ignore_node_id=son.id):
        raise ValidationFailedError(f'"{name}" already exists (in an entity or son). Choose an original name.')
    close = await names.similar_name(name, name_similarity_policy(scope.rules), ignore_node_id=son.id)
    if close is not None:
        raise ValidationFailedError(
            f'"{name}" is too similar to the existing "{close}"; mortals would confuse them. Choose a name that sounds clearly different.'
        )
    old = son.name
    await names.rename(son.id, name)
    await rewrite_name(scope.session, son.id, old, son.name)
    return old


def _apply_resources(scope: PlayerScope, son: SonRow, resources: SonResources) -> list[str]:
    changed: list[str] = []
    rules = scope.rules
    if resources.essence is not None:
        son.essence = max(0, min(max_essence(rules, son.might), resources.essence))
        changed.append("essence")
    if resources.hp is not None:
        son.hp = max(0, min(max_hp(rules, son.endurance), resources.hp))
        changed.append("health")
    if resources.fame is not None:
        son.fame = max(0, resources.fame)
        changed.append("fame")
    if resources.faith is not None:
        son.faith = max(0, resources.faith)
        changed.append("faith")
    if resources.level is not None:
        son.level = max(1, resources.level)
        changed.append("level")
    if resources.stars is not None:
        son.stars = max(MIN_STARS, min(MAX_STARS, resources.stars))
        changed.append("stars")
    if resources.existence is not None:
        son.existence = max(PERCENT_MIN, min(PERCENT_MAX, resources.existence))
        changed.append("existence")
    if resources.xp is not None:
        son.xp = max(0, resources.xp)
        changed.append("experience")
    if resources.sanity is not None:
        son.sanity = clamp_percent(resources.sanity)
        changed.append("sanity")
    return changed


def _apply_texts(son: SonRow, command: EditSon, epoch: int) -> list[str]:
    changed: list[str] = []
    if command.title is not None:
        if not command.title.strip():
            raise ValidationFailedError("A son's title cannot be empty.")
        son.title = command.title.strip()[:TITLE_MAX_LENGTH]
        changed.append("title")
    if command.plan is not None:
        son.plan = command.plan.strip()[:SON_PLAN_MAX_LENGTH] or None
        son.plan_epoch = epoch if son.plan else None
        changed.append("plan")
    if command.personality is not None:
        updates = {
            name: (getattr(command.personality, name) or "").strip()[:PERSONALITY_FIELD_MAX_LENGTH]
            for name in PERSONALITY_FIELDS
            if getattr(command.personality, name) is not None
        }
        son.personality = son.personality.model_copy(update=updates)
        changed.append("personality")
    return changed


def _apply_numbers(scope: PlayerScope, son: SonRow, command: EditSon) -> list[str]:
    changed: list[str] = []
    for passion, value in command.passions.items():
        setattr(son, passion.value, max(PASSION_FLOOR, min(PASSION_CEILING, round(value))))
        changed.append(passion.value)
    for item, value in command.stats.items():
        setattr(son, item.value, max(STAT_FLOOR, min(STAT_CEILING, round(value))))
        changed.append(item.value)
    if command.stats:
        son.hp = min(son.hp, max_hp(scope.rules, son.endurance))
        son.essence = min(son.essence, max_essence(scope.rules, son.might))
    if command.resources is not None:
        changed += _apply_resources(scope, son, command.resources)
    return changed


@player_action("son:edit", ActionKind.EDIT_RECORD)
async def edit_son(scope: PlayerScope, command: EditSon) -> Effect:
    son = await guards.son(scope.session, command.son_id)
    ctx = await scope.context("edit_son")
    messages: list[str] = []
    if command.name is not None:
        old = await _rename_son(scope, son, command.name)
        if old is not None:
            messages.append(await tell(ctx, SON_RENAMED, son_id=son.id, old=old, new=son.name))
    changed = _apply_texts(son, command, await scope.epoch()) + _apply_numbers(scope, son, command)
    if command.rarity is not None and command.rarity is not son.rarity:
        son.rarity = command.rarity
        messages.append(await tell(ctx, SON_RARITY, son_id=son.id, son=son.name, rarity=command.rarity.value))
    if not changed and not messages:
        raise ValidationFailedError(f"Nothing to change on {son.name}.")
    if changed:
        messages.append(await tell(ctx, SON_EDITED, son_id=son.id, son=son.name, fields=", ".join(dict.fromkeys(changed))))
    return Effect(" ".join(messages), son.id)


@player_action("son:star", ActionKind.ADD_STAR)
async def add_star(scope: PlayerScope, command: SonTarget) -> Effect:
    son = await guards.living_son(scope.session, command.son_id)
    target = son.stars + 1
    if target > MAX_STARS:
        raise ValidationFailedError(f"{son.name} already wears every star ({MAX_STARS}).")
    requirement = star_requirement(scope.rules, target)
    level, fame, cost = requirement.level, requirement.fame, requirement.essence
    if son.level < level or son.fame < fame:
        raise ValidationFailedError(
            f"Star {target} needs level {level} and fame {fame}; {son.name} has level {son.level} and fame {son.fame} "
            "(world rules core_rules.star_level_step and core_rules.star_renown_step)."
        )
    creator = await scope.creator()
    spent = guards.charge(creator, cost, "core_rules.star_essence_base")
    son.stars = target
    for item in Stat:
        setattr(son, item.value, max(STAT_FLOOR, min(STAT_CEILING, son.stat(item) + scope.rules.god_actions.star_stat_gain)))
    son.hp = max_hp(scope.rules, son.endurance)
    ctx = await scope.context("star")
    message = await tell(ctx, STAR_ADDED, son_id=son.id, kind=ChronicleKind.STAR, creator=creator.name, son=son.name, stars=target)
    return Effect(message, son.id, essence_spent=spent)


@player_action("son:ascend", ActionKind.ASCEND)
async def ascend(scope: PlayerScope, command: SonTarget) -> Effect:
    son = await guards.living_son(scope.session, command.son_id)
    rules = scope.rules
    following = son.rarity.next()
    if following is None:
        raise ValidationFailedError(f"{son.name} is already in the highest class.")
    if son.stars < MAX_STARS or son.level < rules.ascension.level or son.fame < rules.ascension.renown:
        raise ValidationFailedError(
            f"Ascension needs {MAX_STARS} stars, level {rules.ascension.level} and fame {rules.ascension.renown}; "
            f"{son.name} has {son.stars} stars, level {son.level} and fame {son.fame} (world rules ascension.level and ascension.renown)."
        )
    creator = await scope.creator()
    spent = guards.charge(creator, rules.ascension.essence_cost, "ascension.essence_cost")
    ctx = await scope.context("ascend")
    rng = ctx.rng(f"ascend.{son.id}")
    profile = build_rarity_table(rules)[following]
    for item in Stat:
        setattr(son, item.value, max(son.stat(item), rng.integer(profile.stat_min, profile.stat_max)))
    old = son.rarity
    son.rarity = following
    son.stars = MIN_STARS
    son.hp = max_hp(rules, son.endurance)
    son.essence = max_essence(rules, son.might)
    son.existence = clamp_percent(son.existence + rules.god_actions.ascension_existence)
    cosmos = await scope.cosmos()
    legend = await EntityRepository(scope.session).create(
        EntityDraft(
            name=await NameRepository(scope.session).unique_name(f"Ascension of {son.name}"),
            entity_type=EntityType.LEGEND,
            description=ASCENSION_MYTH.render(son=son.name, old=old.value, new=following.value),
            stats=LegendStats(spread=rules.god_actions.ascension_myth_spread),
            power_level=profile.power_cap,
            origin=EntityOrigin.ENGINE,
            birth_epoch=ctx.epoch,
            world_id=son.current_world_id or cosmos.primary_world_id,
            subtype=ASCENSION_SUBTYPE,
            engine_kind=EngineKind.ASCENSION_MYTH,
            pending_name=True,
            split_title=False,
        )
    )
    await BondRepository(scope.session).connect(BondDraft(legend.id, son.id, BondKind.TELLS_OF, ctx.epoch))
    message = await tell(ctx, ASCENDED, ids=[legend.id], son_id=son.id, kind=ChronicleKind.ASCENSION, son=son.name, old=old.value, new=following.value)
    scope.publish(EventKind.SON_ASCENDED, {"son_id": son.id, "rarity": following.value})
    return Effect(message, son.id, essence_spent=spent, created_ids=(legend.id,))
