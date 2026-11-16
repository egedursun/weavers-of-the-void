from dataclasses import dataclass

from sqlalchemy import select

from aerona.catalog.laws import CRIME_TERMS, penal_cruelty
from aerona.constants.units import PERCENT
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.law_depth import OutlawRow, PrisonerRow, PrisonRow
from aerona.db.tables.polity import PolityMemberRow
from aerona.db.tables.structures import StructureProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.body import HarmCause
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.mind import SkillKind, SkillSource
from aerona.domain.enums.polity import LawKind
from aerona.domain.enums.society import Commodity
from aerona.domain.enums.structure import ConstructionState, StructureKind
from aerona.engine.belonging.refuge import sheltered
from aerona.engine.body.hits import Harm
from aerona.engine.context import TickContext
from aerona.engine.lifecycle.wounds import apply_hits
from aerona.engine.mind.book import set_skill, skill_level
from aerona.engine.mortal.standing import add_infamy
from aerona.engine.notes import note
from aerona.engine.polity.laws import law_param
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import living_entity
from aerona.engine.primitives.society import stock
from aerona.engine.primitives.stats import stat_or

FED = 80
STARVED = 20
FOOD_STEP = 10
TORTURE_TERM = "torture"


@dataclass
class PrisonTally:
    kept: int = 0
    hungry: int = 0
    sick: int = 0
    escaped: int = 0
    released: int = 0


async def prison_in(ctx: TickContext, town_id: int | None) -> StructureProfileRow | None:
    if town_id is None:
        return None
    rows = await ctx.session.scalars(
        select(StructureProfileRow)
        .where(
            StructureProfileRow.kind == StructureKind.PRISON,
            StructureProfileRow.host_entity_id == town_id,
            StructureProfileRow.construction_state == ConstructionState.COMPLETE,
        )
        .order_by(StructureProfileRow.level.desc(), StructureProfileRow.structure_entity_id)
        .limit(1)
    )
    return rows.first()


async def ensure_prison(ctx: TickContext, structure_id: int) -> PrisonRow:
    row = await ctx.session.get(PrisonRow, structure_id)
    if row is None:
        row = PrisonRow(structure_entity_id=structure_id, food=FED, crowding=0, cruelty=30, gang_strength=0, locked=[])
        ctx.session.add(row)
        await ctx.session.flush()
    return row


async def imprison(ctx: TickContext, mortal: EntityRow, *, case_id: int | None = None, term: int | None = None) -> PrisonerRow | None:
    if held(mortal.id) or await ctx.session.get(PrisonerRow, mortal.id) is not None or await sheltered(ctx.session, mortal.id):
        return None
    structure = await prison_in(ctx, mortal.location_id)
    if structure is None:
        return None
    await ensure_prison(ctx, structure.structure_entity_id)
    row = PrisonerRow(
        mortal_entity_id=mortal.id,
        prison_entity_id=structure.structure_entity_id,
        case_id=case_id,
        term=term if term is not None else ctx.rules.prisons.term,
        gang_rank=0,
        since_epoch=ctx.epoch,
        locked=[],
    )
    ctx.session.add(row)
    await ctx.session.flush()
    return row


async def prisoners_of(ctx: TickContext, prison_id: int) -> list[PrisonerRow]:
    return list(await ctx.session.scalars(select(PrisonerRow).where(PrisonerRow.prison_entity_id == prison_id).order_by(PrisonerRow.mortal_entity_id)))


async def code_cruelty(ctx: TickContext, town_id: int) -> int:
    terms = {key: await law_param(ctx.session, town_id, LawKind.PENAL_CODE, key) for key in (*CRIME_TERMS, TORTURE_TERM)}
    return penal_cruelty({key: value for key, value in terms.items() if value is not None})


async def condition_prison(ctx: TickContext, prison: PrisonRow, structure: StructureProfileRow, crowd: int) -> None:
    table = ctx.rules.prisons
    if "crowding" not in prison.locked:
        prison.crowding = clamp_int(round_half_up(crowd * PERCENT / max(1, table.capacity * structure.level)), 0, PERCENT)
    if "cruelty" not in prison.locked and structure.host_entity_id is not None:
        prison.cruelty = await code_cruelty(ctx, structure.host_entity_id)
    stored = structure.host_entity_id is None or await stock(ctx.session, ctx.rules, structure.host_entity_id, Commodity.FOOD) > 0
    aim = max(0, (FED if stored else STARVED) - prison.crowding // 2)
    if "food" not in prison.locked:
        step = FOOD_STEP if aim > prison.food else -FOOD_STEP if aim < prison.food else 0
        prison.food = clamp_int(prison.food + step if abs(aim - prison.food) > FOOD_STEP else aim, 0, PERCENT)


async def suffer(ctx: TickContext, prison: PrisonRow, mortal: EntityRow, tally: PrisonTally) -> None:
    table = ctx.rules.prisons
    harsh = (PERCENT + prison.cruelty) / PERCENT
    if prison.food < table.food_at:
        await apply_hits(ctx, mortal, Harm(round_half_up(table.hunger_hp * harsh), HarmCause.EXPOSURE, "went hungry in prison"), lethal=False)
        tally.hungry += 1
    rng = ctx.rng(f"prison.sick.{mortal.id}")
    if rng.chance(table.sickness_pct * prison.crowding / PERCENT):
        await apply_hits(ctx, mortal, Harm(round_half_up(table.sickness_hp * harsh), HarmCause.EXPOSURE, "fell sick in a crowded prison"), lethal=False)
        tally.sick += 1


async def rise_in_gangs(ctx: TickContext, row: PrisonerRow, mortal: EntityRow) -> None:
    if "gang_rank" not in row.locked:
        row.gang_rank = clamp_int(row.gang_rank + round_half_up(ctx.rules.prisons.gang_gain * stat_or(mortal, "strength", 0) / PERCENT), 0, PERCENT)
    learned = await skill_level(ctx.session, mortal.id, SkillKind.INTRIGUE)
    await set_skill(ctx.session, mortal.id, SkillKind.INTRIGUE, learned + ctx.rules.prisons.intrigue_gain, epoch=ctx.epoch, source=SkillSource.PRACTICE)


async def realm_of_town(ctx: TickContext, town_id: int | None) -> int | None:
    if town_id is None:
        return None
    return await ctx.session.scalar(select(PolityMemberRow.polity_entity_id).where(PolityMemberRow.member_entity_id == town_id).limit(1))


async def escape(ctx: TickContext, row: PrisonerRow, mortal: EntityRow, structure: StructureProfileRow, tally: PrisonTally) -> None:
    await ctx.session.delete(row)
    polity = await realm_of_town(ctx, structure.host_entity_id)
    if await ctx.session.get(OutlawRow, mortal.id) is None:
        ctx.session.add(
            OutlawRow(
                mortal_entity_id=mortal.id,
                polity_entity_id=polity,
                bounty=ctx.rules.outlaws.bounty,
                renown=0,
                declared_epoch=ctx.epoch,
                locked=[],
            )
        )
    tally.escaped += 1
    await note(ctx, f"{mortal.name} broke out of prison and was declared an outlaw.", key="prison.escaped", ids=[mortal.id], kind=ChronicleKind.CIVILIZATION)


async def release(ctx: TickContext, row: PrisonerRow, mortal: EntityRow, tally: PrisonTally) -> None:
    await ctx.session.delete(row)
    await add_infamy(ctx.session, mortal.id, ctx.rules.prisons.stigma, ctx.epoch, rules=ctx.rules)
    tally.released += 1
    await note(ctx, f"{mortal.name} served their term and was let out of prison.", key="prison.released", ids=[mortal.id], kind=ChronicleKind.CIVILIZATION)


async def keep_prison(ctx: TickContext, structure: StructureProfileRow, tally: PrisonTally) -> None:
    prison = await ensure_prison(ctx, structure.structure_entity_id)
    rows = await prisoners_of(ctx, structure.structure_entity_id)
    await condition_prison(ctx, prison, structure, len(rows))
    ranks: list[int] = []
    for row in rows:
        mortal = await living_entity(ctx.session, row.mortal_entity_id)
        if mortal is None:
            await ctx.session.delete(row)
            continue
        if held(mortal.id) or row.since_epoch == ctx.epoch:
            ranks.append(row.gang_rank)
            continue
        if mortal.location_id != structure.host_entity_id:
            await escape(ctx, row, mortal, structure, tally)
            continue
        await suffer(ctx, prison, mortal, tally)
        await rise_in_gangs(ctx, row, mortal)
        ranks.append(row.gang_rank)
        if "term" not in row.locked:
            row.term = max(0, row.term - 1)
        if row.term <= 0:
            await release(ctx, row, mortal, tally)
        elif ctx.rng(f"prison.escape.{mortal.id}").chance(ctx.rules.prisons.escape_pct * (prison.crowding + prison.gang_strength) / (2 * PERCENT)):
            await escape(ctx, row, mortal, structure, tally)
    if "gang_strength" not in prison.locked:
        prison.gang_strength = clamp_int(round_half_up(sum(ranks) / len(ranks)) if ranks else 0, 0, PERCENT)
    tally.kept += 1


async def keep_prisons(ctx: TickContext, tally: PrisonTally) -> None:
    structures = await ctx.session.scalars(
        select(StructureProfileRow)
        .where(StructureProfileRow.kind == StructureKind.PRISON, StructureProfileRow.construction_state == ConstructionState.COMPLETE)
        .order_by(StructureProfileRow.structure_entity_id)
    )
    for structure in list(structures):
        if held(structure.structure_entity_id, structure.host_entity_id):
            continue
        await keep_prison(ctx, structure, tally)
    await ctx.session.flush()
