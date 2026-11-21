from dataclasses import dataclass
from enum import StrEnum

from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.core.total import total
from aerona.db.tables.cosmos import CreatorRow
from aerona.db.tables.divine_conceptions import DivineConceptionRow, GodReadingRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.faith import CultOfficeRow
from aerona.db.tables.interconnect import IncidentParticipantRow, IncidentRow
from aerona.db.tables.mind import SkillRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.divine_conceptions import ConceptionAxis, CreatorPlace, DivineCount, DivineNearness, DivinePersonhood, GodReading
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.mind import SkillKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.models.entity_stats import CultStats
from aerona.engine.context import TickContext
from aerona.engine.divine_conceptions.conception import conceive_all, faiths, read_gods
from aerona.engine.faith.book import FaithBook
from aerona.engine.faith.zealotry import record_heresy
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.primitives.queries import connect
from aerona.engine.primitives.records import RecordSpec, create_record
from aerona.engine.primitives.stats import stat_or
from aerona.engine.recording.record import record

A = ConceptionAxis
AXIS_ENUM: dict[ConceptionAxis, type[StrEnum]] = dict(
    total(ConceptionAxis, {A.COUNT: DivineCount, A.NEARNESS: DivineNearness, A.PERSONHOOD: DivinePersonhood, A.CREATOR: CreatorPlace})
)
AXIS_FIELD = total(ConceptionAxis, {A.COUNT: "count", A.NEARNESS: "nearness", A.PERSONHOOD: "personhood", A.CREATOR: "creator_place"})
DOUBTED = frozenset({GodReading.DEMON, GodReading.UNKNOWN})
P = DivinePersonhood
PERSON_WEIGHT = total(DivinePersonhood, {P.PERSONS: 1.0, P.FORCES: 0.5, P.PRINCIPLE: 0.25, P.MIXED: 0.75})
CP = CreatorPlace
CREATOR_WEIGHT = total(CreatorPlace, {CP.ACKNOWLEDGED: -0.5, CP.UNKNOWN: 0.0, CP.DENIED: 1.0, CP.RIVAL: 0.5})
THEOLOGIAN_SKILL = 30
STRAIN_EASE = 10
SECT = "heresy"


@dataclass
class ConceptionTally:
    conceived: int = 0
    shifted: int = 0
    tested: int = 0
    split: int = 0


def value_of(axis: ConceptionAxis, value: str) -> StrEnum | None:
    kind = AXIS_ENUM[axis]
    return kind(value) if value in {member.value for member in kind} else None


async def set_axis(ctx: TickContext, row: DivineConceptionRow, axis: ConceptionAxis, value: StrEnum, *, by: int | None = None) -> bool:
    field = AXIS_FIELD[axis]
    if field in row.locked or getattr(row, field) == value:
        return False
    setattr(row, field, value)
    row.since_epoch = ctx.epoch
    if axis is A.COUNT:
        await read_gods(ctx, row)
    roles = {IncidentRole.SUBJECT: row.cult_entity_id, IncidentRole.ACTOR: by}
    await record(ctx, "faith.conception_changed", roles=roles, facts={"axis": axis, "value": value.value})
    return True


async def theologians(ctx: TickContext, cult_id: int) -> int:
    clergy = select(CultOfficeRow.holder_entity_id).where(CultOfficeRow.cult_entity_id == cult_id, CultOfficeRow.holder_entity_id.is_not(None))
    skilled = select(SkillRow.id).where(SkillRow.holder_node_id.in_(clergy), SkillRow.skill == SkillKind.THEOLOGY, SkillRow.level >= THEOLOGIAN_SKILL)
    return len(list(await ctx.session.scalars(skilled)))


async def drift(ctx: TickContext, row: DivineConceptionRow, tally: ConceptionTally) -> None:
    table = ctx.rules.divine_conceptions
    chance = table.drift_per_epoch_pct + table.theologian_pull_pct * await theologians(ctx, row.cult_entity_id)
    rng = ctx.rng(f"conception.drift.{row.cult_entity_id}.{ctx.epoch}")
    if not rng.chance(min(PERCENT, chance)):
        return
    axis = rng.pick(list(ConceptionAxis))
    members = list(AXIS_ENUM[axis])
    current = members.index(getattr(row, AXIS_FIELD[axis]))
    step = rng.pick([offset for offset in (-1, 1) if 0 <= current + offset < len(members)])
    if await set_axis(ctx, row, axis, members[current + step]):
        tally.shifted += 1


async def acting_gods(ctx: TickContext, places: list[int]) -> set[int]:
    if not places:
        return set()
    sons = select(SonRow.id)
    acted = (
        select(IncidentParticipantRow.node_id)
        .join(IncidentRow, IncidentRow.id == IncidentParticipantRow.incident_id)
        .where(
            IncidentRow.epoch == ctx.epoch,
            IncidentParticipantRow.role == IncidentRole.ACTOR,
            IncidentParticipantRow.node_id.in_(sons),
            IncidentRow.place_entity_id.in_(places),
        )
    )
    return set(await ctx.session.scalars(acted))


async def split(ctx: TickContext, row: DivineConceptionRow, god: int, tally: ConceptionTally) -> None:
    cult = await ctx.session.get(EntityRow, row.cult_entity_id)
    if cult is None:
        return
    sect = await create_record(
        ctx,
        RecordSpec(
            entity_type=EntityType.CULT,
            name=f"Those apart from {cult.name}",
            body=f"Those of {cult.name} who could no longer deny a god that acted among them gathered apart.",
            stats=CultStats(
                followers=max(1, stat_or(cult, "followers", 2) // 2), zeal=stat_or(cult, "zeal", 50), influence=stat_or(cult, "influence", 20) // 2
            ),
            power=max(1, cult.power_level),
            location_id=cult.location_id,
            world_id=cult.world_id,
            subtype=SECT,
        ),
    )
    await record_heresy(ctx, sect, cult.id)
    await connect(ctx.session, sect.id, god, BondKind.WORSHIPS, ctx.epoch, description="the god that acted among them")
    ctx.session.add(
        DivineConceptionRow(
            cult_entity_id=sect.id,
            count=DivineCount.MANY if row.count is not DivineCount.MANY else row.count,
            nearness=DivineNearness.PRESENT,
            personhood=row.personhood,
            creator_place=row.creator_place,
            since_epoch=ctx.epoch,
            locked=[],
        )
    )
    ctx.session.add(GodReadingRow(cult_entity_id=sect.id, god_node_id=god, reading=GodReading.TRUE, locked=[]))
    roles = {IncidentRole.SUBJECT: cult.id, IncidentRole.PRODUCT: sect.id, IncidentRole.ACTOR: god}
    await record(ctx, "faith.conception_split", roles=roles, facts={"count": row.count})
    tally.split += 1


async def yield_to(ctx: TickContext, row: DivineConceptionRow, god: int) -> None:
    reading = await ctx.session.get(GodReadingRow, (row.cult_entity_id, god))
    if reading is not None and "reading" not in reading.locked:
        reading.reading = GodReading.TRUE if row.count in {DivineCount.MANY, DivineCount.ALL_IS_DIVINE} else GodReading.SERVANT
    if row.count is DivineCount.ONE:
        await set_axis(ctx, row, A.COUNT, DivineCount.ONE_ABOVE_MANY, by=god)


async def tried_by_acts(ctx: TickContext, row: DivineConceptionRow, places: list[int], tally: ConceptionTally) -> None:
    table = ctx.rules.divine_conceptions
    for god in sorted(await acting_gods(ctx, places)):
        reading = await ctx.session.get(GodReadingRow, (row.cult_entity_id, god))
        if reading is None or reading.reading not in DOUBTED:
            continue
        if "strain" not in row.locked:
            row.strain = clamp_int(row.strain + round(table.denied_god_crisis_pct * PERSON_WEIGHT[row.personhood]), 0, PERCENT)
        roles = {IncidentRole.SUBJECT: row.cult_entity_id, IncidentRole.ACTOR: god}
        await record(ctx, "faith.conception_tested", roles=roles, facts={"reading": reading.reading, "strain": row.strain})
        tally.tested += 1
        if row.strain < PERCENT:
            continue
        row.strain = 0
        if ctx.rng(f"conception.split.{row.cult_entity_id}.{god}.{ctx.epoch}").chance(table.split_pct):
            await split(ctx, row, god, tally)
        else:
            await yield_to(ctx, row, god)


async def creator_acted(ctx: TickContext, places: list[int]) -> bool:
    if not places:
        return False
    creators = select(CreatorRow.id)
    acted = (
        select(IncidentParticipantRow.node_id)
        .join(IncidentRow, IncidentRow.id == IncidentParticipantRow.incident_id)
        .where(IncidentRow.epoch == ctx.epoch, IncidentParticipantRow.role == IncidentRole.ACTOR)
        .where(IncidentParticipantRow.node_id.in_(creators), IncidentRow.place_entity_id.in_(places))
    )
    return await ctx.session.scalar(acted.limit(1)) is not None


async def tried_by_creator(ctx: TickContext, row: DivineConceptionRow, places: list[int], tally: ConceptionTally) -> None:
    if not await creator_acted(ctx, places):
        return
    if row.creator_place is CP.UNKNOWN:
        await set_axis(ctx, row, A.CREATOR, CP.ACKNOWLEDGED)
        return
    if "strain" not in row.locked:
        shift = ctx.rules.divine_conceptions.denied_god_crisis_pct * CREATOR_WEIGHT[row.creator_place] * PERSON_WEIGHT[row.personhood]
        row.strain = clamp_int(row.strain + round(shift), 0, PERCENT)
    roles = {IncidentRole.SUBJECT: row.cult_entity_id}
    await record(ctx, "faith.creator_tested", roles=roles, facts={"place": row.creator_place, "strain": row.strain})
    tally.tested += 1
    if row.strain >= PERCENT and "creator_place" not in row.locked:
        row.strain = 0
        await set_axis(ctx, row, A.CREATOR, CP.ACKNOWLEDGED)


async def tend_conceptions(ctx: TickContext) -> ConceptionTally:
    tally = ConceptionTally(conceived=await conceive_all(ctx))
    book = await FaithBook.load(ctx.session)
    for cult in await faiths(ctx):
        row = await ctx.session.get(DivineConceptionRow, cult.id)
        if row is None:
            continue
        if "strain" not in row.locked:
            row.strain = clamp_int(row.strain - STRAIN_EASE, 0, PERCENT)
        church = book.churches.get(cult.id)
        places = sorted({member.id for member in church.members} | ({cult.location_id} if cult.location_id is not None else set())) if church else []
        await tried_by_acts(ctx, row, places, tally)
        await tried_by_creator(ctx, row, places, tally)
        await drift(ctx, row, tally)
    return tally
