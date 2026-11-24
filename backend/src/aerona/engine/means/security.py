from dataclasses import dataclass

from sqlalchemy import select

from aerona.catalog.life.means import ATTEMPT_THEFT_SKILL_KINDS
from aerona.catalog.means import LOCKS
from aerona.constants.units import PERCENT
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.means import SecurityRow
from aerona.db.tables.mind import SkillRow
from aerona.db.tables.networks import NetworkNodeRow, NetworkOutageRow
from aerona.db.tables.structures import StructureProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.body import HarmCause
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.means import LockKind
from aerona.domain.enums.mind import SkillKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.society import KnowledgeBranch
from aerona.domain.enums.structure import StructureKind
from aerona.engine.body.book import capacity_lean
from aerona.engine.body.hits import Harm
from aerona.engine.context import TickContext
from aerona.engine.eras.effects import era_techniques
from aerona.engine.lifecycle.wounds import apply_hits
from aerona.engine.mortal.standing import add_infamy
from aerona.engine.primitives.folk import present_in
from aerona.engine.primitives.knowledge import branch_level
from aerona.engine.primitives.naming import seed_of
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.primitives.stats import stat_or
from aerona.engine.recording.record import record
from aerona.rules.registry import Rules

TEN_THOUSAND = 10000
STORES = frozenset(
    {StructureKind.TEMPLE, StructureKind.LIBRARY, StructureKind.WAREHOUSE, StructureKind.GRANARY, StructureKind.BANK, StructureKind.MINT, StructureKind.ARCHIVE}
)


@dataclass
class SecurityTally:
    secured: int = 0
    improved: int = 0
    locked: int = 0


@dataclass(frozen=True)
class Attempt:
    thwarted: bool
    betrayed: bool
    trapped: bool


def difficulty(rules: Rules, kind: LockKind) -> int:
    return int(getattr(rules.locks, LOCKS[kind].difficulty))


def best_lock(rules: Rules, level: int, known: frozenset[object]) -> LockKind | None:
    fitting = [kind for kind, spec in LOCKS.items() if spec.level <= level and all(need in known for need in spec.needs)]
    return max(fitting, key=lambda kind: (difficulty(rules, kind), kind.value), default=None)


async def lock_for(ctx: TickContext, town: EntityRow) -> LockKind | None:
    level = await branch_level(ctx.session, town.id, KnowledgeBranch.METALLURGY)
    return best_lock(ctx.rules, level, await era_techniques(ctx.session, town.id)) if level >= ctx.rules.security.metal_level else None


async def secure_stores(ctx: TickContext, tally: SecurityTally) -> None:
    table = ctx.rules.security
    known = set(await ctx.session.scalars(select(SecurityRow.holder_entity_id)))
    for profile, town in (
        await ctx.session.execute(
            select(StructureProfileRow, EntityRow)
            .join(EntityRow, EntityRow.id == StructureProfileRow.host_entity_id)
            .where(StructureProfileRow.kind.in_(list(STORES)), EntityRow.status == EntityStatus.CANON)
            .order_by(StructureProfileRow.structure_entity_id)
        )
    ).all():
        if profile.structure_entity_id in known or held(profile.structure_entity_id) or held(town.id):
            continue
        lock = await lock_for(ctx, town)
        sealed = await branch_level(ctx.session, town.id, KnowledgeBranch.WRITING) > 0
        ctx.session.add(
            SecurityRow(
                holder_entity_id=profile.structure_entity_id,
                lock=lock,
                lock_quality=min(difficulty(ctx.rules, lock), table.seed_quality) if lock is not None else 0,
                sealed=sealed,
                guards=table.seed_guards + table.guards_per_ten_thousand * stat_or(town, "population", 0) // TEN_THOUSAND,
                since_epoch=ctx.epoch,
                locked=[],
            )
        )
        tally.secured += 1
    await ctx.session.flush()


async def master_smith(ctx: TickContext, town: EntityRow) -> bool:
    here = await present_in(ctx.session, town)
    found = await ctx.session.scalar(
        select(SkillRow.holder_node_id)
        .join(EntityRow, EntityRow.id == SkillRow.holder_node_id)
        .where(here, EntityRow.entity_type == EntityType.MORTAL, SkillRow.skill == SkillKind.SMITHING, SkillRow.level >= ctx.rules.security.smith_skill)
        .limit(1)
    )
    return found is not None


async def improve_locks(ctx: TickContext, tally: SecurityTally) -> None:
    table = ctx.rules.security
    for row in list(await ctx.session.scalars(select(SecurityRow).order_by(SecurityRow.holder_entity_id))):
        holder = await ctx.session.get(StructureProfileRow, row.holder_entity_id)
        town = await ctx.session.get(EntityRow, holder.host_entity_id) if holder is not None and holder.host_entity_id is not None else None
        if town is None or held(row.holder_entity_id):
            continue
        if row.lock is None and "lock" not in row.locked:
            row.lock = await lock_for(ctx, town)
            if row.lock is not None and "lock_quality" not in row.locked:
                row.lock_quality = min(difficulty(ctx.rules, row.lock), table.seed_quality)
                tally.locked += 1
        if row.lock is None or "lock_quality" in row.locked:
            continue
        if await master_smith(ctx, town):
            row.lock_quality = clamp_int(row.lock_quality + table.smith_gain, 0, difficulty(ctx.rules, row.lock))
            tally.improved += 1


async def guard_of(ctx: TickContext, owner: EntityRow, item: EntityRow) -> SecurityRow | None:
    places = [holder for holder in (item.location_id, owner.id, owner.location_id) if holder is not None]
    for holder in places:
        row = await ctx.session.get(SecurityRow, holder)
        if row is not None:
            return row
    stores = select(StructureProfileRow.structure_entity_id).where(StructureProfileRow.host_entity_id.in_(places), StructureProfileRow.kind.in_(list(STORES)))
    found = await ctx.session.scalar(
        select(SecurityRow).where(SecurityRow.holder_entity_id.in_(stores)).order_by(SecurityRow.lock_quality.desc(), SecurityRow.holder_entity_id).limit(1)
    )
    return found


async def best_skill(ctx: TickContext, holder_id: int, skills: tuple[SkillKind, ...]) -> int:
    if not skills:
        return 0
    found = await ctx.session.scalar(
        select(SkillRow.level).where(SkillRow.holder_node_id == holder_id, SkillRow.skill.in_(list(skills))).order_by(SkillRow.level.desc()).limit(1)
    )
    return int(found or 0)


async def dark_holder(ctx: TickContext, holder_id: int) -> bool:
    work = await ctx.session.get(StructureProfileRow, holder_id)
    town = work.host_entity_id if work is not None else holder_id
    networks = select(NetworkNodeRow.network_entity_id).where(NetworkNodeRow.member_node_id == town)
    found = await ctx.session.scalar(
        select(NetworkOutageRow.id)
        .where(
            NetworkOutageRow.network_entity_id.in_(networks), NetworkOutageRow.epoch <= ctx.epoch, NetworkOutageRow.epoch + NetworkOutageRow.epochs > ctx.epoch
        )
        .limit(1)
    )
    return found is not None


async def attempt_theft(ctx: TickContext, thief: EntityRow, owner: EntityRow, item: EntityRow) -> Attempt:
    table = ctx.rules.security
    row = await guard_of(ctx, owner, item)
    if row is None or held(row.holder_entity_id):
        return Attempt(False, False, False)
    rng = ctx.rng(seed_of("theft", thief.id, item.id, ctx.epoch))
    craft = await ctx.session.scalar(
        select(SkillRow.level)
        .where(SkillRow.holder_node_id == thief.id, SkillRow.skill.in_(ATTEMPT_THEFT_SKILL_KINDS))
        .order_by(SkillRow.level.desc())
        .limit(1)
    )
    picked = max(0.0, 1 - int(craft or 0) * table.thief_pct / PERCENT)
    spec = LOCKS[row.lock] if row.lock is not None else None
    if spec is not None and not spec.picked:
        opener = await best_skill(ctx, thief.id, spec.opened_by)
        dark = spec.fails_in_outage and await dark_holder(ctx, row.holder_entity_id)
        picked = 0.0 if dark else (max(0.0, 1 - opener * table.thief_pct / PERCENT) if opener else 1.0)
        if not opener and not dark:
            picked = float(PERCENT)
    odds = row.lock_quality * table.lock_pct / PERCENT * picked + row.guards * table.guard_pct
    odds *= max(0.0, 1 - await capacity_lean(ctx.session, [thief.id], "stealth", ctx.rules.capacities.stealth_theft_pct))
    thwarted = rng.chance(min(PERCENT, odds))
    if not thwarted and row.lock is not None:
        await record(
            ctx,
            "theft.lock_beaten",
            roles={IncidentRole.ACTOR: thief.id, IncidentRole.VICTIM: owner.id, IncidentRole.TARGET: row.holder_entity_id},
            facts={"lock": row.lock},
        )
    betrayed = row.sealed and rng.chance(table.seal_pct)
    trapped = row.traps and thief.entity_type is EntityType.MORTAL and not held(thief.id)
    if thwarted and "thwarted" not in row.locked:
        row.thwarted += 1
    if trapped:
        await apply_hits(ctx, thief, Harm(damage=table.trap_harm, cause=HarmCause.ACCIDENT, death_cause="was killed by a trap guarding a store"), lethal=False)
    if betrayed and thief.entity_type is EntityType.MORTAL and not held(thief.id):
        await add_infamy(ctx.session, thief.id, table.seal_pct // 10, ctx.epoch, rules=ctx.rules)
    return Attempt(thwarted, betrayed, trapped)


async def keep_security(ctx: TickContext, tally: SecurityTally) -> None:
    await secure_stores(ctx, tally)
    await improve_locks(ctx, tally)
    await ctx.session.flush()
