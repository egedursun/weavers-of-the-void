from dataclasses import dataclass

from sqlalchemy import func, select

from aerona.constants.units import PERCENT
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.crafts import InsurancePolicyRow, InsurerRow
from aerona.db.tables.customs import CooperativeRow
from aerona.db.tables.entities import EntityRow
from aerona.db.write_guard import held
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.crafts import InsuranceCover
from aerona.domain.enums.culture import Technique
from aerona.domain.enums.customs import CoopPurpose
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.mind import MemoryKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.body.customs import people_of
from aerona.engine.context import TickContext
from aerona.engine.economy.purse import points_of, shift_points
from aerona.engine.lore.research import has_technique
from aerona.engine.primitives.naming import seed_of
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.recording.record import record
from aerona.engine.services.community_relations import change_relation

POOLING = frozenset({CoopPurpose.INSURANCE, CoopPurpose.BURIAL})


@dataclass
class InsuranceTally:
    founded: int = 0
    written: int = 0
    lapsed: int = 0
    ruined: int = 0


async def knows_insurance(ctx: TickContext, faction: EntityRow) -> bool:
    town = await ctx.session.get(EntityRow, faction.location_id) if faction.location_id is not None else None
    if town is None:
        return False
    people = await people_of(ctx.session, town)
    return await has_technique(ctx.session, town.id, Technique.INSURANCE) or (
        people is not None and await has_technique(ctx.session, people.id, Technique.INSURANCE)
    )


async def found_insurers(ctx: TickContext, tally: InsuranceTally) -> None:
    table = ctx.rules.insurance
    known = set(await ctx.session.scalars(select(InsurerRow.insurer_entity_id)))
    pooling = set(await ctx.session.scalars(select(CooperativeRow.faction_entity_id).where(CooperativeRow.purpose.in_(POOLING))))
    factions = await ctx.session.scalars(
        select(EntityRow).where(EntityRow.entity_type == EntityType.FACTION, EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id)
    )
    for faction in list(factions):
        if faction.id in known or held(faction.id):
            continue
        rolled = ctx.rng(seed_of("insurer", faction.id, ctx.epoch)).chance(table.found_chance)
        if faction.id not in pooling and not (rolled and await knows_insurance(ctx, faction)):
            continue
        members = await ctx.session.scalar(
            select(func.count(BondRow.id)).where(BondRow.target_node_id == faction.id, BondRow.kind == BondKind.MEMBER_OF, BondRow.state == BondState.ACTIVE)
        )
        pool = table.seed_pool + table.seed_pool_per_member * (members or 0)
        ctx.session.add(InsurerRow(insurer_entity_id=faction.id, pool=pool, locked=[]))
        tally.founded += 1
        await record(
            ctx,
            "insurance.founded",
            roles={IncidentRole.ACTOR: faction.id},
            facts={"pool": pool, "pooled": int(faction.id in pooling)},
            place=faction.location_id,
        )
    await ctx.session.flush()


async def candidates(ctx: TickContext, insurer: EntityRow) -> list[tuple[int, InsuranceCover]]:
    found: list[tuple[int, InsuranceCover]] = []
    if insurer.location_id is not None:
        found += [(insurer.location_id, InsuranceCover.CARGO), (insurer.location_id, InsuranceCover.HOUSE)]
    members = await ctx.session.scalars(
        select(BondRow.source_node_id)
        .where(BondRow.target_node_id == insurer.id, BondRow.kind == BondKind.MEMBER_OF, BondRow.state == BondState.ACTIVE)
        .order_by(BondRow.source_node_id)
    )
    found += [(member, InsuranceCover.LIFE) for member in members]
    return found


async def write_policies(ctx: TickContext, row: InsurerRow, tally: InsuranceTally) -> None:
    table = ctx.rules.insurance
    insurer = await ctx.session.get(EntityRow, row.insurer_entity_id)
    if insurer is None or row.ruined:
        return
    covered = set(
        await ctx.session.execute(
            select(InsurancePolicyRow.holder_node_id, InsurancePolicyRow.cover).where(
                InsurancePolicyRow.insurer_entity_id == row.insurer_entity_id, InsurancePolicyRow.active.is_(True)
            )
        )
    )
    written = 0
    for holder_id, cover in await candidates(ctx, insurer):
        if written >= table.per_epoch(table.policies_per_epoch) or (holder_id, cover) in covered or held(holder_id):
            continue
        premium = max(1, round(table.sum_insured * row.premium_pct / PERCENT))
        ctx.session.add(
            InsurancePolicyRow(
                insurer_entity_id=row.insurer_entity_id,
                holder_node_id=holder_id,
                cover=cover,
                premium=premium,
                sum_insured=table.sum_insured,
                since_epoch=ctx.epoch,
                locked=[],
            )
        )
        written += 1
    tally.written += written


async def collect(ctx: TickContext, row: InsurerRow, tally: InsuranceTally) -> None:
    policies = await ctx.session.scalars(
        select(InsurancePolicyRow)
        .where(InsurancePolicyRow.insurer_entity_id == row.insurer_entity_id, InsurancePolicyRow.active.is_(True))
        .order_by(InsurancePolicyRow.id)
    )
    for policy in list(policies):
        if held(policy.holder_node_id):
            continue
        holder = await ctx.session.get(EntityRow, policy.holder_node_id)
        if holder is None or await points_of(ctx.session, holder) < policy.premium:
            if "active" not in policy.locked:
                policy.active = False
                tally.lapsed += 1
            continue
        await shift_points(ctx.session, holder, -policy.premium)
        if "pool" not in row.locked:
            row.pool += policy.premium


async def judge(ctx: TickContext, row: InsurerRow, claims: int, tally: InsuranceTally) -> None:
    table = ctx.rules.insurance
    if "risk_belief" not in row.locked:
        row.risk_belief = clamp_int(row.risk_belief + (table.belief_step if claims > 0 else -table.belief_step), 0, PERCENT)
    if "premium_pct" not in row.locked:
        row.premium_pct = clamp_int(max(1, row.risk_belief // 4), 0, PERCENT)
    if row.pool >= 0 or row.ruined or "ruined" in row.locked:
        return
    row.ruined = True
    tally.ruined += 1
    insurer = await ctx.session.get(EntityRow, row.insurer_entity_id)
    holders = set(
        await ctx.session.scalars(
            select(InsurancePolicyRow.holder_node_id).where(InsurancePolicyRow.insurer_entity_id == row.insurer_entity_id, InsurancePolicyRow.active.is_(True))
        )
    )
    for holder_id in sorted(holders):
        if not held(holder_id):
            await change_relation(ctx, holder_id, row.insurer_entity_id, -table.ruin_opinion, MemoryKind.ILL_WILL, note="could not pay what it had promised")
    if insurer is not None:
        await record(
            ctx,
            "insurance.ruined",
            roles={IncidentRole.SUBJECT: insurer.id, IncidentRole.VICTIM: sorted(holders)},
            facts={"pool": row.pool, "holders": len(holders)},
            place=insurer.location_id,
        )


async def claims_total(ctx: TickContext, insurer_id: int) -> int:
    return int(
        await ctx.session.scalar(select(func.coalesce(func.sum(InsurancePolicyRow.claims), 0)).where(InsurancePolicyRow.insurer_entity_id == insurer_id)) or 0
    )


async def keep_insurance(ctx: TickContext, tally: InsuranceTally) -> None:
    await found_insurers(ctx, tally)
    for row in list(await ctx.session.scalars(select(InsurerRow).order_by(InsurerRow.insurer_entity_id))):
        if held(row.insurer_entity_id):
            continue
        total = await claims_total(ctx, row.insurer_entity_id)
        await write_policies(ctx, row, tally)
        await collect(ctx, row, tally)
        await judge(ctx, row, max(0, total - row.claims_seen), tally)
        if "claims_seen" not in row.locked:
            row.claims_seen = total
    await ctx.session.flush()
