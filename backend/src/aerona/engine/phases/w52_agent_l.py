from dataclasses import dataclass

from sqlalchemy import select

from aerona.catalog.world_thoughts import WORLD_THOUGHTS
from aerona.constants.units import PERCENT
from aerona.db.tables.customs import TimeBudgetRow
from aerona.db.tables.demography import PeopleCultureRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.interconnect import IncidentParticipantRow, IncidentRow
from aerona.db.tables.mind import GriefRow
from aerona.db.write_guard import held
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.mind import GriefStage
from aerona.domain.enums.mortal import LifeStage
from aerona.domain.enums.society import SocialClass
from aerona.engine.context import TickContext
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.mind.thoughts import think
from aerona.engine.phase import Phase
from aerona.engine.primitives.folk import folk_among
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.recording.terms import explaining, term


@dataclass
class WorldThoughtTally:
    thought: int = 0


@dataclass
class ShareTally:
    cohered: int = 0
    eased: int = 0


async def witnesses(ctx: TickContext, incident: IncidentRow) -> list[int]:
    actors = list(
        await ctx.session.scalars(
            select(IncidentParticipantRow.node_id).where(IncidentParticipantRow.incident_id == incident.id).order_by(IncidentParticipantRow.node_id)
        )
    )
    statement = select(EntityRow.id).where(EntityRow.entity_type == EntityType.MORTAL, EntityRow.status == EntityStatus.CANON)
    places = [node for node in [incident.place_entity_id, *actors] if node is not None]
    present = list(
        await ctx.session.scalars(statement.where(await folk_among(ctx.session, places)).order_by(EntityRow.id).limit(ctx.rules.mind.world_thought_cap))
    )
    mortals = set(await ctx.session.scalars(statement.where(EntityRow.id.in_(actors))))
    return sorted(set(present) | mortals)


async def think_on_the_world(ctx: TickContext, tally: WorldThoughtTally) -> None:
    incidents = await ctx.session.scalars(
        select(IncidentRow).where(IncidentRow.epoch == ctx.epoch, IncidentRow.kind.in_(sorted(WORLD_THOUGHTS))).order_by(IncidentRow.id)
    )
    for incident in list(incidents):
        kind = WORLD_THOUGHTS[incident.kind]
        for mortal_id in await witnesses(ctx, incident):
            if held(mortal_id):
                continue
            await think(ctx.session, ctx.rules, mortal_id, kind, ctx.epoch, subject_id=incident.place_entity_id)
            tally.thought += 1


@reads(
    "table.entities",
    "table.incident_participants",
    "table.incidents",
    "table.mind_facets",
    "table.mortal_profiles",
    "table.nodes",
    "table.personality_values",
    "table.thoughts",
)
@writes("table.memories", "table.mind_facets", "table.mortal_profiles", "table.personality_values", "table.thoughts")
async def world_thoughts(ctx: TickContext) -> None:
    tally = WorldThoughtTally()
    await think_on_the_world(ctx, tally)
    ctx.count("world_thoughts", tally.thought)


async def share_of(ctx: TickContext, people_id: int, field: str) -> int:
    row = await ctx.session.get(TimeBudgetRow, (people_id, SocialClass.FARMER, LifeStage.ADULT))
    return int(getattr(row, field)) if row is not None else 0


async def cohere_by_company(ctx: TickContext, people: EntityRow, tally: ShareTally) -> None:
    culture = await ctx.session.get(PeopleCultureRow, people.id)
    share = await share_of(ctx, people.id, "socialising")
    if culture is None or share <= 0 or held(people.id) or "cohesion" in (culture.locked or []):
        return
    with explaining():
        term("time_budget.socialising", share, source_node_id=people.id)
        term("time_shares.socialising_cohesion_pct", ctx.rules.time.socialising_cohesion_pct)
        culture.cohesion = clamp_int(culture.cohesion + round_half_up(share * ctx.rules.time.socialising_cohesion_pct / PERCENT), 0, PERCENT)
    tally.cohered += 1


async def ease_mourning(ctx: TickContext, people: EntityRow, tally: ShareTally) -> None:
    share = await share_of(ctx, people.id, "mourning")
    if share <= 0:
        return
    mourners = select(EntityRow.id).where(EntityRow.entity_type == EntityType.MORTAL, await folk_among(ctx.session, [people.id]))
    rows = await ctx.session.scalars(
        select(GriefRow).where(GriefRow.mourner_node_id.in_(mourners), GriefRow.stage == GriefStage.MOURNING).order_by(GriefRow.id)
    )
    for row in list(rows):
        if held(row.mourner_node_id):
            continue
        with explaining():
            term("time_budget.mourning", share, source_node_id=people.id)
            term("time_shares.mourning_ease_pct", ctx.rules.time.mourning_ease_pct)
            row.strength = clamp_int(row.strength - round_half_up(share * ctx.rules.time.mourning_ease_pct / PERCENT), 0, PERCENT)
        tally.eased += 1


@reads("table.entities", "table.griefs", "table.nodes", "table.people_culture", "table.time_budgets")
@writes("table.griefs", "table.people_culture")
async def time_shares(ctx: TickContext) -> None:
    tally = ShareTally()
    peoples = await ctx.session.scalars(
        select(EntityRow).where(EntityRow.entity_type == EntityType.PEOPLE, EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id)
    )
    for people in list(peoples):
        await cohere_by_company(ctx, people, tally)
        await ease_mourning(ctx, people, tally)
    ctx.count("time_shares_cohered", tally.cohered)
    ctx.count("time_shares_eased", tally.eased)


PHASES = (Phase("world_thoughts", world_thoughts), Phase("time_shares", time_shares))
