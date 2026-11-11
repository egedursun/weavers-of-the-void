from dataclasses import dataclass
from types import MappingProxyType

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.ethics import STANCE_ORDER
from aerona.constants.units import PERCENT
from aerona.core.total import total
from aerona.db.tables.collective import RoleNormRow, SexRatioRow
from aerona.db.tables.cycles import ManumissionRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.mind import MemoryRow
from aerona.db.write_guard import held
from aerona.domain.enums.collective import RoleEligibility, RoleKind
from aerona.domain.enums.cycles import ReproductiveCaste, ReproductiveSystem
from aerona.domain.enums.demography import Sex
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.mind import EthicalStance, MemoryKind, ValueAxis, ValueHolder
from aerona.domain.enums.mortal import CareerPath
from aerona.domain.enums.society import SocialClass
from aerona.engine.body.customs import people_of
from aerona.engine.context import TickContext
from aerona.engine.cycles.lineage import caste_of, sexes_fixed, system_of
from aerona.engine.mind.book import stored_values
from aerona.engine.notes import note
from aerona.engine.polity.book import sex_of
from aerona.engine.primitives.stats import stat_or
from aerona.rules.registry import Rules

FEMALE = "female"
MALE = "male"
LEAN = 40
RANK_PREFERRED = 0
RANK_OPEN = 1
RANK_TOLERATED = 2
MIN_AGES = total(RoleKind, {RoleKind.OFFICE: 16, RoleKind.PROFESSION: 12, RoleKind.COMBAT: 15, RoleKind.PRIESTHOOD: 14, RoleKind.INHERITANCE: 0})
CAREER_ROLES: MappingProxyType[CareerPath, RoleKind] = MappingProxyType(
    {
        CareerPath.ARMY: RoleKind.COMBAT,
        CareerPath.OFFICE: RoleKind.OFFICE,
        CareerPath.APPRENTICE: RoleKind.PROFESSION,
        CareerPath.TRADE: RoleKind.PROFESSION,
        CareerPath.VOWS: RoleKind.PRIESTHOOD,
    }
)
ELITE = (SocialClass.NOBLE, SocialClass.PRIEST, SocialClass.SCRIBE, SocialClass.WARRIOR)
OPENING = {
    RoleEligibility.FEMALE_ONLY: RoleEligibility.FEMALE_PREFERRED,
    RoleEligibility.MALE_ONLY: RoleEligibility.MALE_PREFERRED,
    RoleEligibility.FEMALE_PREFERRED: RoleEligibility.ANY,
    RoleEligibility.MALE_PREFERRED: RoleEligibility.ANY,
    RoleEligibility.ANY: RoleEligibility.ANY,
}
NARROWING = {
    FEMALE: (RoleEligibility.FEMALE_PREFERRED, RoleEligibility.FEMALE_ONLY),
    MALE: (RoleEligibility.MALE_PREFERRED, RoleEligibility.MALE_ONLY),
}


@dataclass
class RoleTally:
    seeded: int = 0
    opened: int = 0
    narrowed: int = 0


def barred(row: RoleNormRow | None, age: int) -> bool:
    return row is not None and (age < row.min_age or row.stance in {EthicalStance.SHAMEFUL, EthicalStance.UNTHINKABLE})


def rank_for(row: RoleNormRow | None, sex: str, age: int) -> int | None:
    if row is None:
        return RANK_OPEN
    if barred(row, age):
        return None
    rule = row.eligibility
    if rule is RoleEligibility.ANY:
        return RANK_OPEN
    favoured = FEMALE if rule in {RoleEligibility.FEMALE_ONLY, RoleEligibility.FEMALE_PREFERRED} else MALE
    if sex == favoured:
        return RANK_PREFERRED
    if rule in {RoleEligibility.FEMALE_ONLY, RoleEligibility.MALE_ONLY}:
        return None
    return RANK_TOLERATED


async def role_norm(session: AsyncSession, mortal: EntityRow, role: RoleKind) -> RoleNormRow | None:
    people = await people_of(session, mortal)
    return await session.get(RoleNormRow, (people.id, role)) if people is not None else None


FREED_HELD_BACK = frozenset({RoleKind.OFFICE, RoleKind.PRIESTHOOD})
CASTE_ROLES: dict[RoleKind, ReproductiveCaste] = {RoleKind.COMBAT: ReproductiveCaste.SOLDIER, RoleKind.INHERITANCE: ReproductiveCaste.BREEDER}


async def caste_rank(session: AsyncSession, mortal: EntityRow, role: RoleKind, rank: int | None) -> int | None:
    wanted = CASTE_ROLES.get(role)
    if rank is None or wanted is None:
        return rank
    return RANK_PREFERRED if await caste_of(session, mortal.id) is wanted else RANK_TOLERATED


async def freed_below(session: AsyncSession, mortal: EntityRow, standing: int) -> bool:
    lowly = await session.scalar(
        select(ManumissionRow.id)
        .join(MemoryRow, MemoryRow.subject_node_id == ManumissionRow.community_entity_id)
        .where(MemoryRow.holder_node_id == mortal.id, MemoryRow.kind == MemoryKind.FREED_US, ManumissionRow.standing < standing)
        .limit(1)
    )
    return lowly is not None


async def freed_rank(session: AsyncSession, rules: Rules, mortal: EntityRow, role: RoleKind, rank: int | None) -> int | None:
    if rank is None or role not in FREED_HELD_BACK:
        return rank
    return max(rank, RANK_TOLERATED) if await freed_below(session, mortal, rules.manumission.office_at) else rank


async def sexed_rank(session: AsyncSession, mortal: EntityRow, role: RoleKind, row: RoleNormRow | None) -> int | None:
    system = await system_of(session, mortal)
    if sexes_fixed(system):
        return rank_for(row, sex_of(mortal), stat_or(mortal, "age", 0))
    if barred(row, stat_or(mortal, "age", 0)):
        return None
    return await caste_rank(session, mortal, role, RANK_OPEN) if system is ReproductiveSystem.CASTE else RANK_OPEN


async def role_rank(session: AsyncSession, mortal: EntityRow, role: RoleKind, social_class: SocialClass | None = None) -> int | None:
    row = await role_norm(session, mortal, role)
    if row is not None and row.classes and social_class is not None and social_class not in row.classes:
        return None
    return await sexed_rank(session, mortal, role, row)


async def career_open(session: AsyncSession, rules: Rules, mortal: EntityRow, path: CareerPath) -> bool:
    role = CAREER_ROLES.get(path)
    if role is None:
        return True
    if role in FREED_HELD_BACK and await freed_below(session, mortal, rules.manumission.office_at):
        return False
    return await role_rank(session, mortal, role) is not None


async def allowed_heirs(session: AsyncSession, dead: EntityRow, heirs: list[EntityRow]) -> list[EntityRow]:
    ranked = [(rank, heir) for heir in heirs if (rank := await role_rank(session, heir, RoleKind.INHERITANCE)) is not None]
    if not ranked:
        return heirs
    best = min(rank for rank, _ in ranked)
    return [heir for rank, heir in ranked if rank == best]


async def combat_sexes(session: AsyncSession, community: EntityRow) -> set[Sex]:
    people = await people_of(session, community)
    row = await session.get(RoleNormRow, (people.id, RoleKind.COMBAT)) if people is not None else None
    if people is not None and not sexes_fixed(await system_of(session, people)):
        return set() if barred(row, PERCENT) else set(Sex)
    return {sex for sex in Sex if rank_for(row, sex.value, PERCENT) is not None}


async def seed_roles(ctx: TickContext, people: EntityRow, tally: RoleTally) -> None:
    if await ctx.session.scalar(select(RoleNormRow.holder_entity_id).where(RoleNormRow.holder_entity_id == people.id).limit(1)) is not None:
        return
    values = await stored_values(ctx.session, ValueHolder.CULTURE, people.id)
    if not values:
        return
    rng = ctx.rng(f"role_norms.{people.id}")
    strict = values.get(ValueAxis.TRADITION, 0) + values.get(ValueAxis.HIERARCHY, 0)
    for role in RoleKind:
        eligibility = RoleEligibility.ANY
        if strict >= LEAN * 2 and rng.chance(strict / 2):
            favoured = FEMALE if rng.chance(PERCENT // 2) else MALE
            eligibility = NARROWING[favoured][1 if strict >= LEAN * 3 else 0]
        classes = [item.value for item in ELITE] if role is RoleKind.OFFICE and values.get(ValueAxis.HIERARCHY, 0) >= LEAN else []
        ctx.session.add(
            RoleNormRow(
                holder_entity_id=people.id,
                role=role,
                eligibility=eligibility,
                min_age=MIN_AGES[role],
                classes=classes,
                stance=EthicalStance.ACCEPTABLE,
                since_epoch=ctx.epoch,
                locked=[],
            )
        )
        tally.seeded += 1
    await ctx.session.flush()


async def open_roles(ctx: TickContext, people: EntityRow, tally: RoleTally) -> None:
    ratio = await ctx.session.get(SexRatioRow, people.id)
    table = ctx.rules.sex_ratio
    if ratio is None or table.skew_at <= ratio.males_per_hundred <= PERCENT * PERCENT // table.skew_at:
        return
    values = await stored_values(ctx.session, ValueHolder.CULTURE, people.id)
    if values.get(ValueAxis.TRADITION, 0) >= LEAN or not ctx.rng(f"role_open.{people.id}.{ctx.epoch}").chance(table.norm_shift_pct):
        return
    scarce = MALE if ratio.males_per_hundred < table.skew_at else FEMALE
    for row in await ctx.session.scalars(select(RoleNormRow).where(RoleNormRow.holder_entity_id == people.id).order_by(RoleNormRow.role)):
        favours_scarce = row.eligibility in NARROWING[scarce]
        if not favours_scarce or "eligibility" in row.locked:
            continue
        row.eligibility, row.since_epoch = OPENING[row.eligibility], ctx.epoch
        tally.opened += 1
        await note(ctx, f"With so few left to fill it, {people.name} opened the {row.role.value} role to all.", key="roles.opened", ids=[people.id])
        return


async def drift_roles(ctx: TickContext, people: EntityRow, tally: RoleTally) -> None:
    rng = ctx.rng(f"role_drift.{people.id}.{ctx.epoch}")
    if not rng.chance(ctx.rules.role_norms.drift_pct):
        return
    values = await stored_values(ctx.session, ValueHolder.CULTURE, people.id)
    strict = values.get(ValueAxis.TRADITION, 0) + values.get(ValueAxis.HIERARCHY, 0)
    rows = [row for row in await ctx.session.scalars(select(RoleNormRow).where(RoleNormRow.holder_entity_id == people.id).order_by(RoleNormRow.role))]
    free = [row for row in rows if "eligibility" not in row.locked]
    if strict < 0:
        closed = [row for row in free if row.eligibility is not RoleEligibility.ANY]
        if closed:
            closed[0].eligibility, closed[0].since_epoch = OPENING[closed[0].eligibility], ctx.epoch
            tally.opened += 1
    elif strict >= LEAN * 2:
        open_rows = [row for row in free if row.eligibility is RoleEligibility.ANY]
        if open_rows:
            row = rng.pick(open_rows)
            row.eligibility, row.since_epoch = NARROWING[FEMALE if rng.chance(PERCENT // 2) else MALE][0], ctx.epoch
            tally.narrowed += 1


async def keep_roles(ctx: TickContext, tally: RoleTally) -> None:
    peoples = await ctx.session.scalars(
        select(EntityRow).where(EntityRow.entity_type == EntityType.PEOPLE, EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id)
    )
    for people in list(peoples):
        if held(people.id):
            continue
        await seed_roles(ctx, people, tally)
        await open_roles(ctx, people, tally)
        await drift_roles(ctx, people, tally)
    await ctx.session.flush()


async def breach_cost(session: AsyncSession, mortal: EntityRow, role: RoleKind) -> int:
    row = await role_norm(session, mortal, role)
    if row is None or row.stance is EthicalStance.ACCEPTABLE:
        return 0
    return max(0, STANCE_ORDER.index(row.stance) - STANCE_ORDER.index(EthicalStance.ACCEPTABLE))
