from typing import Literal

from pydantic import Field

from aerona.constants.player import ENTITY_TEXT_MAX_LENGTH
from aerona.constants.schema import NAME_MAX_LENGTH, TITLE_MAX_LENGTH
from aerona.db.repositories.entities import EntityRepository
from aerona.db.repositories.names import normalize_name
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.demography import SexKind
from aerona.domain.enums.entity import EntityType, MortalRole
from aerona.domain.enums.limits import PERCENT_MAX
from aerona.domain.enums.society import NaturalLaw
from aerona.engine.lore.creation import RecordShape, shape_record
from aerona.engine.phases.births import order_village
from aerona.engine.phases.exploration import shape_region
from aerona.engine.phases.heroes import MortalShape, shape_mortal
from aerona.engine.phases.horror import order_outer_being
from aerona.engine.primitives.renames import rewrite_name
from aerona.services.player import guards
from aerona.services.player.scope import Command, Effect, PlayerScope, player_action

Share = int | None


class Shaped(Command):
    name: str | None = None
    title: str | None = None
    description: str | None = None


class MortalDraft(Shaped):
    community_id: int
    role: MortalRole = MortalRole.COMMONER
    sex: SexKind | None = None
    power: int = Field(default=3, ge=1, le=10)
    strength: Share = Field(default=None, ge=0, le=PERCENT_MAX)
    agility: Share = Field(default=None, ge=0, le=PERCENT_MAX)
    intellect: Share = Field(default=None, ge=0, le=PERCENT_MAX)
    charisma: Share = Field(default=None, ge=0, le=PERCENT_MAX)
    endurance: Share = Field(default=None, ge=0, le=PERCENT_MAX)
    willpower: Share = Field(default=None, ge=0, le=PERCENT_MAX)
    perception: Share = Field(default=None, ge=0, le=PERCENT_MAX)
    wisdom: Share = Field(default=None, ge=0, le=PERCENT_MAX)
    creativity: Share = Field(default=None, ge=0, le=PERCENT_MAX)
    beauty: Share = Field(default=None, ge=0, le=PERCENT_MAX)
    age: int | None = Field(default=None, ge=0)
    lifespan: int | None = Field(default=None, ge=1)


class RegionDraft(Shaped):
    world_id: int
    near_id: int | None = None
    water: bool = False
    breadth: Share = Field(default=None, ge=0, le=PERCENT_MAX)
    danger: Share = Field(default=None, ge=0, le=PERCENT_MAX)
    fertility: Share = Field(default=None, ge=0, le=PERCENT_MAX)
    magic: Share = Field(default=None, ge=0, le=PERCENT_MAX)


class RecordDraft(Shaped):
    entity_type: Literal[EntityType.CELESTIAL, EntityType.SPIRIT, EntityType.NATURAL_LAW, EntityType.CULT]
    god_id: int | None = None
    world_id: int | None = None
    location_id: int | None = None
    power: int = Field(default=3, ge=1, le=10)
    natural_law: NaturalLaw | None = None
    brightness: Share = Field(default=None, ge=0, le=PERCENT_MAX)
    influence: Share = Field(default=None, ge=0, le=PERCENT_MAX)
    visibility: Share = Field(default=None, ge=0, le=PERCENT_MAX)
    cycle: int | None = Field(default=None, ge=1)
    strength: Share = Field(default=None, ge=0, le=PERCENT_MAX)
    unrest: Share = Field(default=None, ge=0, le=PERCENT_MAX)
    followers: int | None = Field(default=None, ge=1)
    zeal: Share = Field(default=None, ge=0, le=PERCENT_MAX)


RECORD_STATS: dict[EntityType, tuple[str, ...]] = {
    EntityType.CELESTIAL: ("brightness", "influence", "visibility", "cycle"),
    EntityType.SPIRIT: ("strength", "unrest"),
    EntityType.NATURAL_LAW: (),
    EntityType.CULT: ("followers", "zeal", "influence"),
}
MORTAL_STATS = ("strength", "agility", "intellect", "charisma", "endurance", "willpower", "perception", "wisdom", "creativity", "beauty", "age", "lifespan")
REGION_STATS = ("breadth", "danger", "fertility", "magic")


async def shape_after(scope: PlayerScope, entity_id: int, draft: Shaped) -> None:
    record = await guards.entity(scope.session, entity_id)
    name = (draft.name or "").strip()
    if name and normalize_name(name) != normalize_name(record.name):
        old = record.name
        await EntityRepository(scope.session).rename(record, name[:NAME_MAX_LENGTH])
        await rewrite_name(scope.session, record.id, old, record.name)
    if draft.title is not None:
        record.title = draft.title.strip()[:TITLE_MAX_LENGTH] or None
    if draft.description is not None and draft.description.strip():
        record.description = draft.description.strip()[:ENTITY_TEXT_MAX_LENGTH]


@player_action("mortal:shape", ActionKind.CREATE_ENTITY)
async def mortal(scope: PlayerScope, draft: MortalDraft) -> Effect:
    stats: dict[str, object] = {key: getattr(draft, key) for key in MORTAL_STATS}
    stats["sex"] = draft.sex.value if draft.sex is not None else None
    shape = MortalShape(draft.name, draft.title, draft.description, draft.role, stats, draft.power)
    born = await shape_mortal(await scope.context("mortal_shape"), draft.community_id, shape)
    return Effect(f"{born.name} is born by your will.", born.id, created_ids=(born.id,))


@player_action("region:shape", ActionKind.CREATE_ENTITY)
async def region(scope: PlayerScope, draft: RegionDraft) -> Effect:
    land = await shape_region(
        await scope.context("region_shape"), draft.world_id, draft.near_id, draft.water, {key: getattr(draft, key) for key in REGION_STATS}
    )
    await shape_after(scope, land.id, draft)
    return Effect(f"{land.name} rises by your will.", land.id, created_ids=(land.id,))


@player_action("record:shape", ActionKind.CREATE_ENTITY)
async def made_record(scope: PlayerScope, draft: RecordDraft) -> Effect:
    shape = RecordShape(
        entity_type=draft.entity_type,
        name=draft.name or "",
        description=draft.description or "",
        title=draft.title,
        world_id=draft.world_id,
        location_id=draft.location_id,
        power=draft.power,
        stats={key: getattr(draft, key) for key in RECORD_STATS.get(draft.entity_type, ())},
        natural_law=draft.natural_law,
        god_id=draft.god_id,
    )
    made = await shape_record(await scope.context("record_shape"), shape)
    return Effect(f"{made.name} comes into being by your will.", made.id, created_ids=(made.id,))


class VillageDraft(Shaped):
    people_id: int
    settlers: int | None = Field(default=None, ge=1)


class OuterBeingDraft(Shaped):
    world_id: int


@player_action("people:village", ActionKind.FOUND_SETTLEMENT)
async def village(scope: PlayerScope, draft: VillageDraft) -> Effect:
    town = await order_village(await scope.context("found_village"), draft.people_id, draft.settlers)
    await shape_after(scope, town.id, draft)
    return Effect(f"{town.name} was founded.", town.id, created_ids=(town.id,))


@player_action("horror:outer_being", ActionKind.SUMMON_OUTER_BEING)
async def outer_being(scope: PlayerScope, draft: OuterBeingDraft) -> Effect:
    being = await order_outer_being(scope.session, scope.rules, draft.world_id)
    await shape_after(scope, being.id, draft)
    return Effect(f"{being.name} entered the world.", being.id, created_ids=(being.id,))
