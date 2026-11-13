from dataclasses import dataclass

from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.db.tables.cosmic_state import VesselProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.intrigue import SchemeRow
from aerona.db.tables.operations import AdmiraltyRow
from aerona.db.tables.polity import PolityProfileRow, TreatyClauseRow, TreatyProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.entity import EntityStatus
from aerona.domain.enums.intrigue import PlotKind
from aerona.domain.enums.mind import SkillKind, ValueAxis
from aerona.domain.enums.polity import ClauseKind, OfficeKind, PartyRole, TreatyKind, TreatyStatus
from aerona.engine.context import TickContext
from aerona.engine.economy.purse import take_coin
from aerona.engine.intrigue.schemes import begin_scheme
from aerona.engine.military.orders import create_vessel
from aerona.engine.military.shipyard import Commission
from aerona.engine.military.vessels import best_hull
from aerona.engine.mind.book import skill_level, values_for
from aerona.engine.notes import note
from aerona.engine.operations.fields import keep
from aerona.engine.operations.limits import cap_of, fleet_of, owners_of, tonnage_of, tonnage_under
from aerona.engine.operations.theatres import folk_of
from aerona.engine.polity.accords import Clause, sign
from aerona.engine.polity.treaties import breach
from aerona.engine.primitives.knowledge import KnowledgeMap
from aerona.engine.primitives.naming import Namer, seed_of
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.primitives.stats import stat_or
from aerona.engine.relations.persuasion import office_holder
from aerona.engine.services.war import current_war
from aerona.language.generator import NameKind

TEN_THOUSAND = 10_000
MIDPOINT = 50


@dataclass
class AdmiraltyTally:
    admiralties: int = 0
    commissioned: int = 0
    treaties: int = 0
    schemes: int = 0
    discovered: int = 0


async def yard_of(ctx: TickContext, polity: EntityRow) -> EntityRow | None:
    profile = await ctx.session.get(PolityProfileRow, polity.id)
    if profile is not None and profile.capital_entity_id is not None:
        capital = await ctx.session.get(EntityRow, profile.capital_entity_id)
        if capital is not None and capital.status is EntityStatus.CANON:
            return capital
    members = [item for member in (await owners_of(ctx, polity.id))[1:] if (item := await ctx.session.get(EntityRow, member)) is not None]
    return max(members, key=lambda item: stat_or(item, "population", 0), default=None)


async def limits_on(ctx: TickContext, polity_id: int) -> list[TreatyClauseRow]:
    rows = await ctx.session.scalars(
        select(TreatyClauseRow)
        .join(TreatyProfileRow, TreatyProfileRow.treaty_entity_id == TreatyClauseRow.treaty_entity_id)
        .where(
            TreatyClauseRow.kind == ClauseKind.FLEET_LIMIT,
            TreatyClauseRow.obligor_node_id == polity_id,
            TreatyProfileRow.status == TreatyStatus.IN_FORCE,
        )
        .order_by(TreatyClauseRow.id)
    )
    return list(rows)


async def admiralty_of(ctx: TickContext, polity_id: int) -> AdmiraltyRow:
    row = await ctx.session.get(AdmiraltyRow, polity_id)
    if row is None:
        share = ctx.rules.admiralty.base_share
        row = AdmiraltyRow(polity_entity_id=polity_id, budget_share=share, requested=share, updated_epoch=ctx.epoch, locked=[])
        ctx.session.add(row)
        await ctx.session.flush()
    return row


async def sway(ctx: TickContext, holder_id: int | None, skill: SkillKind) -> int:
    weight = ctx.rules.admiralty.influence_skill_pct
    level = await skill_level(ctx.session, holder_id, skill) if holder_id is not None else 0
    return clamp_int(level * weight // PERCENT + (PERCENT - weight) // 2, 0, PERCENT)


async def disregard(ctx: TickContext, holder_id: int | None) -> int:
    if holder_id is None:
        return 0
    values = await values_for(ctx.session, holder_id)
    return clamp_int(MIDPOINT + (values.get(ValueAxis.MARTIAL, 0) - values.get(ValueAxis.LAW, 0)) // 2, 0, PERCENT)


async def at_sea_war(ctx: TickContext, polity_id: int, rivals: list[int]) -> bool:
    for rival in rivals:
        if rival != polity_id and await current_war(ctx.session, polity_id, rival) is not None:
            return True
    return False


async def commission_ships(ctx: TickContext, polity: EntityRow, row: AdmiraltyRow, count: int, tally: AdmiraltyTally) -> None:
    yard = await yard_of(ctx, polity)
    if yard is None or held(yard.id) or count <= 0:
        return
    knowledge = await KnowledgeMap.load(ctx.session)
    namer = Namer(ctx.session, ctx.rules)
    laid = 0
    for index in range(count):
        if not await take_coin(ctx.session, ctx.rules, polity, ctx.rules.admiralty.ship_cost):
            break
        name = await namer.from_speaker(polity.id, seed_of(polity.id, ctx.epoch, "ship", index), NameKind.GENERAL) or f"{polity.name} {ctx.epoch}-{index + 1}"
        await create_vessel(ctx, yard.id, name, Commission(frame=best_hull(knowledge, yard.id, 0)))
        laid += 1
    tally.commissioned += laid
    if laid:
        keep(row, "commissioned", row.commissioned + laid)
        await note(ctx, f"The admiralty of {polity.name} laid down {laid} new ships.", key="admiralty.commissioned", ids=[polity.id])


async def room_for(ctx: TickContext, polity: EntityRow, fleet: list[VesselProfileRow]) -> int:
    people = sum(stat_or(item, "population", 0) for item in await folk_of(ctx, polity))
    return max(0, max(1, people * ctx.rules.admiralty.ships_per_ten_thousand // TEN_THOUSAND) - len(fleet))


async def keep_admiralty(ctx: TickContext, polity: EntityRow, rivals: list[int], tally: AdmiraltyTally) -> None:
    table = ctx.rules.admiralty
    row = await admiralty_of(ctx, polity.id)
    admiral = await office_holder(ctx.session, polity.id, OfficeKind.ADMIRAL)
    marshal = await office_holder(ctx.session, polity.id, OfficeKind.MARSHAL)
    keep(row, "admiral_entity_id", admiral)
    keep(row, "influence", await sway(ctx, admiral, SkillKind.NAVAL_COMBAT))
    rival_sway = await sway(ctx, marshal, SkillKind.STRATEGY)
    step = table.request_step if await at_sea_war(ctx, polity.id, rivals) else -(table.request_step // 2)
    keep(row, "requested", clamp_int(row.budget_share + step, 0, PERCENT))
    pull = (row.requested - row.budget_share) * row.influence // max(1, row.influence + rival_sway)
    keep(row, "budget_share", clamp_int(row.budget_share + pull, 0, PERCENT))
    fleet = await fleet_of(ctx, polity.id)
    keep(row, "tonnage", sum(tonnage_of(ship) for ship in fleet))
    clauses = await limits_on(ctx, polity.id)
    keep(row, "limit_tonnage", min((cap_of(ctx, clause) for clause in clauses), default=None))
    reached = [clause for clause in clauses if await tonnage_under(ctx, clause) >= cap_of(ctx, clause)]
    over = bool(reached)
    if over and await disregard(ctx, admiral) >= table.cheat_share:
        await hide_fleet(ctx, polity, admiral, reached[0], tally)
        over = False
    count = 0 if over else min(table.max_commissions, row.budget_share // table.commission_share, await room_for(ctx, polity, fleet))
    await commission_ships(ctx, polity, row, count, tally)
    await expose(ctx, polity, row, clauses, tally)
    row.updated_epoch = ctx.epoch
    tally.admiralties += 1


async def hide_fleet(ctx: TickContext, polity: EntityRow, admiral_id: int | None, clause: TreatyClauseRow, tally: AdmiraltyTally) -> None:
    open_scheme = await ctx.session.scalar(
        select(SchemeRow.id).where(
            SchemeRow.kind == PlotKind.HIDE_FLEET, SchemeRow.owner_node_id.in_([polity.id, admiral_id or 0]), SchemeRow.ended_epoch.is_(None)
        )
    )
    beneficiary = await ctx.session.get(EntityRow, clause.beneficiary_node_id) if clause.beneficiary_node_id is not None else None
    owner = await ctx.session.get(EntityRow, admiral_id) if admiral_id is not None else polity
    if open_scheme is not None or owner is None:
        return
    if await begin_scheme(ctx, owner, PlotKind.HIDE_FLEET, beneficiary) is not None:
        tally.schemes += 1


async def expose(ctx: TickContext, polity: EntityRow, row: AdmiraltyRow, clauses: list[TreatyClauseRow], tally: AdmiraltyTally) -> None:
    if row.concealed <= 0 or not clauses or held(polity.id):
        return
    if not ctx.rng(f"hidden_fleet.{polity.id}.{ctx.epoch}").chance(ctx.rules.admiralty.discovery_chance):
        return
    clause = clauses[0]
    profile = await ctx.session.get(TreatyProfileRow, clause.treaty_entity_id)
    keep(row, "concealed", 0)
    tally.discovered += 1
    if profile is not None:
        await breach(ctx, profile, polity.id, clause=clause, reason="it built ships in secret beyond the tonnage it swore to")
    await note(ctx, f"The hidden ships of {polity.name} were found out; it had built past its fleet limit.", key="admiralty.fleet_exposed", ids=[polity.id])


async def limited_pair(ctx: TickContext, first: int, second: int) -> bool:
    found = await ctx.session.scalar(
        select(TreatyClauseRow.id)
        .join(TreatyProfileRow, TreatyProfileRow.treaty_entity_id == TreatyClauseRow.treaty_entity_id)
        .where(
            TreatyClauseRow.kind == ClauseKind.FLEET_LIMIT,
            TreatyClauseRow.obligor_node_id == first,
            TreatyClauseRow.beneficiary_node_id == second,
            TreatyProfileRow.status == TreatyStatus.IN_FORCE,
        )
        .limit(1)
    )
    return found is not None


async def naval_treaties(ctx: TickContext, powers: list[EntityRow], tally: AdmiraltyTally) -> None:
    table = ctx.rules.admiralty
    for index, first in enumerate(powers):
        for second in powers[index + 1 :]:
            if first.world_id != second.world_id or held(first.id, second.id):
                continue
            if await current_war(ctx.session, first.id, second.id) is not None or await limited_pair(ctx, first.id, second.id):
                continue
            if not ctx.rng(f"naval_treaty.{first.id}.{second.id}.{ctx.epoch}").chance(table.treaty_chance):
                continue
            cap = {"tonnage": table.fleet_limit}
            await sign(
                ctx,
                TreatyKind.NAVAL_LIMIT,
                [(first.id, PartyRole.SIGNATORY), (second.id, PartyRole.SIGNATORY)],
                clauses=[Clause(ClauseKind.FLEET_LIMIT, first.id, second.id, dict(cap)), Clause(ClauseKind.FLEET_LIMIT, second.id, first.id, dict(cap))],
            )
            tally.treaties += 1


async def keep_admiralties(ctx: TickContext, tally: AdmiraltyTally) -> None:
    rows = await ctx.session.scalars(
        select(EntityRow)
        .join(PolityProfileRow, PolityProfileRow.polity_entity_id == EntityRow.id)
        .where(EntityRow.status == EntityStatus.CANON)
        .order_by(EntityRow.id)
    )
    polities = list(rows)
    naval = [polity for polity in polities if await fleet_of(ctx, polity.id) or await ctx.session.get(AdmiraltyRow, polity.id) is not None]
    rivals = [polity.id for polity in naval]
    for polity in naval:
        if held(polity.id):
            continue
        await keep_admiralty(ctx, polity, rivals, tally)
    powers = [
        polity for polity in naval if (row := await ctx.session.get(AdmiraltyRow, polity.id)) is not None and row.tonnage >= ctx.rules.admiralty.fleet_limit
    ]
    await naval_treaties(ctx, powers, tally)
