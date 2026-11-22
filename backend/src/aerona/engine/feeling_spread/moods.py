from collections import defaultdict
from dataclasses import dataclass

from sqlalchemy import func, select

from aerona.catalog.life_traits import EMOTION_TRAITS, having
from aerona.constants.units import PERCENT
from aerona.db.tables.collective import CrowdMoodRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.feeling_spread import FeelingSpreadRow
from aerona.db.tables.households import HouseholdMemberRow
from aerona.db.tables.mind import ThoughtRow
from aerona.db.write_guard import held
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.life_traits import EmotionTrait
from aerona.domain.enums.mind import Emotion, ThoughtKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.context import TickContext
from aerona.engine.mind.thoughts import think
from aerona.engine.primitives.folk import present_among
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import active_bonds
from aerona.engine.primitives.stats import stat
from aerona.engine.recording.record import record

SPREAD_BONDS = (BondKind.PARENT_OF, BondKind.SPOUSE_OF, BondKind.LOVES, BondKind.COMPANION, BondKind.SWORN_KIN, BondKind.APPRENTICE_OF, BondKind.ADHERENT_OF)
ANGRY = having(EMOTION_TRAITS, EmotionTrait.ANGRY)
AFRAID = having(EMOTION_TRAITS, EmotionTrait.AFRAID)
STIRRED = having(EMOTION_TRAITS, EmotionTrait.STIRRED)
KEPT = 3
FADED = 10


@dataclass
class MoodTally:
    places: int = 0
    households: int = 0
    caught: int = 0
    spread: int = 0
    faded: int = 0


def emotion_of(value: str) -> Emotion | None:
    known = {item.value: item for item in Emotion}
    return known.get(value)


async def mood_of(ctx: TickContext, *, settlement: int | None = None, household: int | None = None) -> FeelingSpreadRow:
    query = select(FeelingSpreadRow).where(FeelingSpreadRow.settlement_entity_id == settlement, FeelingSpreadRow.household_id == household)
    found = await ctx.session.scalar(query.order_by(FeelingSpreadRow.id).limit(1))
    if found is not None:
        return found
    row = FeelingSpreadRow(settlement_entity_id=settlement, household_id=household, feelings={}, locked=[])
    ctx.session.add(row)
    await ctx.session.flush()
    return row


def blended(ctx: TickContext, before: dict[str, int], measured: dict[Emotion, float]) -> dict[str, int]:
    keep = PERCENT - ctx.rules.feeling_spread.fade_per_epoch
    mixed: dict[str, float] = {key: value * keep / PERCENT for key, value in before.items()}
    for emotion, value in measured.items():
        mixed[emotion.value] = mixed.get(emotion.value, 0.0) + value
    ranked = sorted(mixed.items(), key=lambda item: (-item[1], item[0]))[:KEPT]
    return {key: clamp_int(round_half_up(value), 0, PERCENT) for key, value in ranked if round_half_up(value) > 0}


async def settle(ctx: TickContext, row: FeelingSpreadRow, measured: dict[Emotion, float], tally: MoodTally, subject: int) -> None:
    if "feelings" in (row.locked or []):
        return
    table = ctx.rules.feeling_spread
    before_top = max((row.feelings or {}).values(), default=0)
    row.feelings = blended(ctx, dict(row.feelings or {}), measured)
    row.updated_epoch = ctx.epoch
    leading = max(row.feelings.items(), key=lambda item: (item[1], item[0]), default=None)
    row.leading = emotion_of(leading[0]) if leading is not None else None
    top = leading[1] if leading is not None else 0
    if top >= table.told_at > before_top and row.leading is not None:
        tally.spread += 1
        await record(ctx, "mood.spread", roles={IncidentRole.SUBJECT: subject}, facts={"feeling": row.leading, "strength": top})
    elif top < FADED <= before_top:
        tally.faded += 1
        await record(ctx, "mood.faded", roles={IncidentRole.SUBJECT: subject}, facts={"strength": top})


async def measured_by_place(ctx: TickContext) -> tuple[dict[int, dict[Emotion, float]], dict[int, int]]:
    people = (
        select(EntityRow.location_id, func.count())
        .where(EntityRow.entity_type == EntityType.MORTAL, EntityRow.status == EntityStatus.CANON)
        .group_by(EntityRow.location_id)
    )
    counts = {place: count for place, count in await ctx.session.execute(people) if place is not None}
    felt = (
        select(EntityRow.location_id, ThoughtRow.emotion, func.sum(ThoughtRow.intensity))
        .join(EntityRow, EntityRow.id == ThoughtRow.holder_node_id)
        .where(ThoughtRow.epoch == ctx.epoch, EntityRow.status == EntityStatus.CANON)
        .group_by(EntityRow.location_id, ThoughtRow.emotion)
    )
    found: dict[int, dict[Emotion, float]] = defaultdict(dict)
    for place, emotion, total in await ctx.session.execute(felt):
        if place is not None and counts.get(place):
            found[place][emotion] = float(total or 0) / counts[place]
    return found, counts


async def measured_by_household(ctx: TickContext) -> dict[int, dict[Emotion, float]]:
    members = select(HouseholdMemberRow.household_id, func.count()).group_by(HouseholdMemberRow.household_id)
    counts = {household: count for household, count in await ctx.session.execute(members)}
    felt = (
        select(HouseholdMemberRow.household_id, ThoughtRow.emotion, func.sum(ThoughtRow.intensity))
        .join(ThoughtRow, ThoughtRow.holder_node_id == HouseholdMemberRow.member_node_id)
        .where(ThoughtRow.epoch == ctx.epoch)
        .group_by(HouseholdMemberRow.household_id, ThoughtRow.emotion)
    )
    found: dict[int, dict[Emotion, float]] = defaultdict(dict)
    for household, emotion, total in await ctx.session.execute(felt):
        if counts.get(household):
            found[household][emotion] = float(total or 0) / counts[household]
    return found


async def catch(ctx: TickContext, holder: int, emotion: Emotion, strength: float, *, source: int | None, tally: MoodTally) -> None:
    if strength <= 0 or held(holder):
        return
    if await think(ctx.session, ctx.rules, holder, ThoughtKind.CAUGHT_FEELING, ctx.epoch, subject_id=source, intensity=strength, emotion=emotion) is not None:
        tally.caught += 1


async def feed_crowd(ctx: TickContext, town: int, feelings: dict[str, int]) -> None:
    crowd = await ctx.session.get(CrowdMoodRow, town)
    if crowd is None or "anger" in (crowd.locked or []):
        return
    share = ctx.rules.feeling_spread.crowd_pct
    of = {emotion_of(key): value for key, value in feelings.items()}
    crowd.anger = clamp_int(crowd.anger + sum(value for key, value in of.items() if key in ANGRY) * share // PERCENT, 0, PERCENT)
    crowd.anxiety = clamp_int(crowd.anxiety + sum(value for key, value in of.items() if key in AFRAID) * share // PERCENT, 0, PERCENT)
    crowd.fervour = clamp_int(crowd.fervour + sum(value for key, value in of.items() if key in STIRRED) * share // PERCENT, 0, PERCENT)


async def spread_in_places(ctx: TickContext, tally: MoodTally) -> None:
    table = ctx.rules.feeling_spread
    measured, _counts = await measured_by_place(ctx)
    towns = select(EntityRow.id).where(EntityRow.entity_type == EntityType.SETTLEMENT, EntityRow.status == EntityStatus.CANON)
    kept = set(await ctx.session.scalars(select(FeelingSpreadRow.settlement_entity_id)))
    for town in sorted(set(await ctx.session.scalars(towns)) & (set(measured) | kept)):
        if held(town):
            continue
        row = await mood_of(ctx, settlement=town)
        await settle(ctx, row, measured.get(town, {}), tally, town)
        tally.places += 1
        await feed_crowd(ctx, town, dict(row.feelings or {}))
        strength = max((row.feelings or {}).values(), default=0)
        if row.leading is None or strength < table.spread_floor:
            continue
        residents = select(EntityRow.id).where(
            await present_among(ctx.session, [town]), EntityRow.entity_type == EntityType.MORTAL, EntityRow.status == EntityStatus.CANON
        )
        for holder in list(await ctx.session.scalars(residents.order_by(EntityRow.id).limit(table.caught_per_place))):
            await catch(ctx, holder, row.leading, strength * table.per_place_pct / PERCENT, source=None, tally=tally)


async def spread_in_households(ctx: TickContext, tally: MoodTally) -> None:
    measured = await measured_by_household(ctx)
    kept = {household for household in await ctx.session.scalars(select(FeelingSpreadRow.household_id)) if household is not None}
    for household in sorted(set(measured) | kept):
        row = await mood_of(ctx, household=household)
        await settle(ctx, row, measured.get(household, {}), tally, household)
        tally.households += 1


async def spread_along_bonds(ctx: TickContext, tally: MoodTally) -> None:
    table = ctx.rules.feeling_spread
    strong = (
        select(ThoughtRow)
        .where(ThoughtRow.epoch == ctx.epoch, ThoughtRow.intensity >= table.spread_floor, ThoughtRow.kind != ThoughtKind.CAUGHT_FEELING)
        .order_by(ThoughtRow.intensity.desc(), ThoughtRow.id)
        .limit(table.spreaders)
    )
    for thought in list(await ctx.session.scalars(strong)):
        source = await ctx.session.get(EntityRow, thought.holder_node_id)
        if source is None or source.status is not EntityStatus.CANON:
            continue
        reach = 1 + (stat(source, "charisma") or 0) * table.charisma_reach_pct / (PERCENT * PERCENT)
        strength = thought.intensity * table.per_bond_pct / PERCENT * reach
        kin = {bond.target_node_id for bond in await active_bonds(ctx.session, SPREAD_BONDS, sources=[source.id])}
        kin |= {bond.source_node_id for bond in await active_bonds(ctx.session, SPREAD_BONDS, targets=[source.id])}
        for other in sorted(kin - {source.id}):
            await catch(ctx, other, thought.emotion, strength, source=source.id, tally=tally)


async def tend_moods(ctx: TickContext) -> MoodTally:
    tally = MoodTally()
    await spread_along_bonds(ctx, tally)
    await spread_in_places(ctx, tally)
    await spread_in_households(ctx, tally)
    return tally
