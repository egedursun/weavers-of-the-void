from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.units import PERCENT
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.disease import DiseaseProfileRow, OutbreakRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.evolution import CureResearchRow, PlagueResponseRow
from aerona.db.write_guard import held
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.disease import OutbreakStatus
from aerona.domain.enums.entity import SOCIETY_TYPES
from aerona.domain.enums.evolution import PlagueResponse
from aerona.domain.enums.faith import FuneralRite
from aerona.domain.enums.mind import ValueAxis
from aerona.engine.context import TickContext
from aerona.engine.disease.control import quarantine
from aerona.engine.disease.research import institutions
from aerona.engine.disease.stigma import values_for
from aerona.engine.faith.judgement import funeral_custom
from aerona.engine.notes import note
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.primitives.queries import canon
from aerona.engine.primitives.stats import shift_bounded

R = PlagueResponse
STABILITY = "stability"
UNBURNED = frozenset({FuneralRite.BURIAL, FuneralRite.EXPOSURE, FuneralRite.NAMELESS})
LEANINGS: dict[PlagueResponse, tuple[ValueAxis, ...]] = {
    R.CLOSE_BORDERS: (ValueAxis.TRADITION, ValueAxis.LOYALTY),
    R.QUARANTINE: (ValueAxis.LAW, ValueAxis.KNOWLEDGE),
    R.BURN_DEAD: (ValueAxis.PURITY,),
    R.EXPEL_SICK: (ValueAxis.PURITY, ValueAxis.HIERARCHY),
    R.PRAYER: (ValueAxis.PIETY, ValueAxis.SUPERSTITION),
    R.SEEK_CURE: (ValueAxis.KNOWLEDGE, ValueAxis.MERCY),
}
RESPONSE_WORDS = {
    R.CLOSE_BORDERS: "closed its borders",
    R.QUARANTINE: "shut its sick away",
    R.BURN_DEAD: "burned its dead",
    R.EXPEL_SICK: "drove out its sick",
    R.PRAYER: "gathered to pray",
    R.SEEK_CURE: "set its learned to seek a cure",
}


@dataclass
class ResponseTally:
    taken: int = 0
    lifted: int = 0
    riots: int = 0


def leaning(values: dict[ValueAxis, int], response: PlagueResponse) -> float:
    held_values = LEANINGS.get(response, ())
    return 1 + sum(values.get(axis, 0) for axis in held_values) / PERCENT


def resentment(values: dict[ValueAxis, int]) -> float:
    return max(0.0, 1 + (values.get(ValueAxis.KINSHIP, 0) + values.get(ValueAxis.MERCY, 0) - 2 * values.get(ValueAxis.LAW, 0)) / (2 * PERCENT))


async def institutions_in(session: AsyncSession, community_id: int) -> list[int]:
    return [row.id for row in await institutions(session) if row.location_id == community_id]


async def options_for(ctx: TickContext, community: EntityRow) -> list[PlagueResponse]:
    options = [R.CLOSE_BORDERS, R.QUARANTINE, R.EXPEL_SICK]
    if await funeral_custom(ctx, community.id) not in UNBURNED:
        options.append(R.BURN_DEAD)
    worships = await ctx.session.scalar(
        select(BondRow.id).where(BondRow.source_node_id == community.id, BondRow.kind == BondKind.WORSHIPS, BondRow.state == BondState.ACTIVE).limit(1)
    )
    if worships is not None:
        options.append(R.PRAYER)
    if await institutions_in(ctx.session, community.id):
        options.append(R.SEEK_CURE)
    return options


async def take_up(ctx: TickContext, community: EntityRow, disease_id: int, response: PlagueResponse, *, strength: int | None = None) -> PlagueResponseRow:
    table = ctx.rules.plague_responses
    row = await ctx.session.get(PlagueResponseRow, (community.id, disease_id, response))
    if row is None:
        row = PlagueResponseRow(community_entity_id=community.id, disease_entity_id=disease_id, response=response, since_epoch=ctx.epoch, locked=[])
        ctx.session.add(row)
    if "strength" not in row.locked:
        row.strength = strength if strength is not None else row.strength or PERCENT * 6 // 10
    if "until_epoch" not in row.locked:
        row.until_epoch = ctx.epoch + table.length
    if response is R.QUARANTINE:
        region = (await RegionAtlas.load(ctx.session)).top_region(community.id)
        if region is not None:
            await quarantine(ctx, region, epochs=table.length, son_id=None)
    await ctx.session.flush()
    return row


async def struck(ctx: TickContext) -> list[tuple[EntityRow, int]]:
    atlas = await RegionAtlas.load(ctx.session)
    sick: dict[int, set[int]] = {}
    for outbreak in await ctx.session.scalars(select(OutbreakRow).where(OutbreakRow.status != OutbreakStatus.ENDED).order_by(OutbreakRow.id)):
        sick.setdefault(outbreak.region_entity_id, set()).add(outbreak.disease_entity_id)
    found: list[tuple[EntityRow, int]] = []
    for community in await canon(ctx.session, SOCIETY_TYPES):
        region = atlas.top_region(community.id)
        for disease_id in sorted(sick.get(region or -1, set())):
            found.append((community, disease_id))
    return found


async def bear(ctx: TickContext, row: PlagueResponseRow, community: EntityRow, tally: ResponseTally) -> None:
    table = ctx.rules.plague_responses
    weight = row.strength / PERCENT
    if row.response is R.CLOSE_BORDERS:
        shift_bounded(ctx.rules, community, STABILITY, -table.border_unrest * weight)
    elif row.response is R.QUARANTINE and ctx.rng(f"plague_riot.{community.id}.{row.disease_entity_id}").chance(
        table.riot_pct * weight * resentment(await values_for(ctx, community))
    ):
        shift_bounded(ctx.rules, community, STABILITY, -table.riot_unrest)
        tally.riots += 1
        await note(ctx, f"The folk of {community.name} rose against the quarantine.", key="disease.quarantine_riot", ids=[community.id])
    elif row.response is R.BURN_DEAD:
        if await funeral_custom(ctx, community.id) in UNBURNED:
            shift_bounded(ctx.rules, community, STABILITY, -table.burn_cohesion * weight)
    elif row.response is R.EXPEL_SICK:
        profile = await ctx.session.get(DiseaseProfileRow, row.disease_entity_id)
        if profile is not None and "stigma" not in profile.locked:
            profile.stigma = clamp_int(profile.stigma + round(table.expel_stigma * weight), 0, PERCENT)
    elif row.response is R.PRAYER:
        shift_bounded(ctx.rules, community, STABILITY, table.prayer_morale * weight)
    elif row.response is R.SEEK_CURE:
        for institution_id in await institutions_in(ctx.session, community.id):
            research = await ctx.session.get(CureResearchRow, (institution_id, row.disease_entity_id))
            if research is None:
                research = CureResearchRow(
                    institution_entity_id=institution_id, disease_entity_id=row.disease_entity_id, points=0, specimens=0, started_epoch=ctx.epoch, locked=[]
                )
                ctx.session.add(research)
            if "points" not in research.locked and research.cured_epoch is None:
                research.points = (research.points or 0) + round(table.cure_points * weight)


async def respond(ctx: TickContext, tally: ResponseTally) -> None:
    table = ctx.rules.plague_responses
    for row in list(await ctx.session.scalars(select(PlagueResponseRow).where(PlagueResponseRow.until_epoch < ctx.epoch))):
        if held(row.community_entity_id, row.disease_entity_id) or "until_epoch" in row.locked:
            continue
        await ctx.session.delete(row)
        tally.lifted += 1
    await ctx.session.flush()
    for community, disease_id in await struck(ctx):
        if held(community.id, disease_id):
            continue
        taken = list(
            await ctx.session.scalars(
                select(PlagueResponseRow.response).where(
                    PlagueResponseRow.community_entity_id == community.id, PlagueResponseRow.disease_entity_id == disease_id
                )
            )
        )
        rng = ctx.rng(f"plague_response.{community.id}.{disease_id}")
        if taken or not rng.chance(table.choose_pct):
            continue
        options = await options_for(ctx, community)
        values = await values_for(ctx, community)
        response = rng.weighted(options, [leaning(values, option) for option in options])
        await take_up(ctx, community, disease_id, response)
        tally.taken += 1
        disease = await ctx.session.get(EntityRow, disease_id)
        if disease is not None:
            await note(
                ctx, f"Against {disease.name}, {community.name} {RESPONSE_WORDS[response]}.", key="disease.plague_response", ids=[community.id, disease_id]
            )
    for row in list(await ctx.session.scalars(select(PlagueResponseRow).order_by(PlagueResponseRow.community_entity_id, PlagueResponseRow.disease_entity_id))):
        bearer = await ctx.session.get(EntityRow, row.community_entity_id)
        if bearer is not None and not held(bearer.id):
            await bear(ctx, row, bearer, tally)
    await ctx.session.flush()
