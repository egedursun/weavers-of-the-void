from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from sqlalchemy import select

from aerona.catalog.estates import CAUSE_LABELS
from aerona.constants.units import PERCENT
from aerona.db.tables.demography import PeopleCultureRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.estates import EstatePrivilegeRow, EstateProfileRow, MovementProfileRow, MovementSupportRow
from aerona.db.tables.factions import FactionGoalRow, FactionProfileRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.db.tables.society import CommunitySocietyRow
from aerona.db.tables.society_depth import PolityLoyaltyRow
from aerona.db.write_guard import held
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.faction import FactionGoalKind, FactionKind, MovementCause
from aerona.domain.enums.mind import ValueAxis
from aerona.domain.enums.polity import DecisionRule, LawKind
from aerona.domain.enums.society import SocialClass
from aerona.domain.enums.war import WarCause
from aerona.domain.models.entity_stats import FactionStats
from aerona.engine.body.customs import people_of
from aerona.engine.context import TickContext
from aerona.engine.mind.book import values_for
from aerona.engine.notes import note
from aerona.engine.polity.book import Realm, RealmBook
from aerona.engine.polity.laws import LawBook
from aerona.engine.polity.policy import revolution
from aerona.engine.polity.regard import value_distance
from aerona.engine.polity.standing import secede
from aerona.engine.primitives.naming import seed_of
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.records import RecordSpec, create_record
from aerona.engine.primitives.society import class_shares
from aerona.engine.primitives.stats import stat
from aerona.engine.services.war import declare_war

HALF = PERCENT // 2
SUPPORT = "support"
GOALS: dict[MovementCause, FactionGoalKind] = {
    MovementCause.ABOLITION: FactionGoalKind.ABOLISH_LAW,
    MovementCause.INDEPENDENCE: FactionGoalKind.INDEPENDENCE,
    MovementCause.REVIVAL: FactionGoalKind.CONVERT_REALM,
    MovementCause.LAND_REFORM: FactionGoalKind.ABOLISH_LAW,
    MovementCause.FRANCHISE: FactionGoalKind.ENACT_LAW,
}
LAW_TARGETS: dict[MovementCause, LawKind] = {
    MovementCause.ABOLITION: LawKind.SLAVERY,
    MovementCause.LAND_REFORM: LawKind.SERFDOM,
}
ASSEMBLIES = frozenset({DecisionRule.ASSEMBLY, DecisionRule.COUNCIL})
POWER = 2


@dataclass
class MovementTally:
    founded: int = 0
    parties: int = 0
    protests: int = 0
    revolts: int = 0
    revolutions: int = 0


@dataclass(frozen=True)
class Ground:
    community: EntityRow
    realm: Realm
    laws: LawBook
    values: dict[ValueAxis, int]
    shares: dict[SocialClass, float]
    farmers_content: float


async def abolition(ctx: TickContext, ground: Ground) -> float:
    slavery = ground.laws.in_force(ground.realm.entity.id, LawKind.SLAVERY)
    if slavery is None or slavery.params.get("status") != "allowed":
        return 0.0
    return max(0.0, ground.values.get(ValueAxis.MERCY, 0) / 2 + ground.shares.get(SocialClass.SERF_OR_SLAVE, 0.0))


async def independence(ctx: TickContext, ground: Ground) -> float:
    folk = await people_of(ctx.session, ground.community)
    core = ground.realm.profile.core_entity_id
    if folk is None or core is None or folk.id == core:
        return 0.0
    table = ctx.rules.affairs
    culture = await ctx.session.get(PeopleCultureRow, folk.id)
    cohesion = culture.cohesion if culture is not None else HALF
    distinct = value_distance(await values_for(ctx.session, folk.id), await values_for(ctx.session, core))
    loyalty = await ctx.session.get(PolityLoyaltyRow, (ground.realm.entity.id, ground.community.id))
    grievances = loyalty.grievances if loyalty is not None else 0
    member = ground.realm.members.get(ground.community.id)
    autonomy = member.autonomy if member is not None else 0
    privileges = len(
        list(
            await ctx.session.scalars(
                select(EstatePrivilegeRow.privilege)
                .join(EstateProfileRow, EstateProfileRow.faction_entity_id == EstatePrivilegeRow.estate_entity_id)
                .where(EstateProfileRow.polity_entity_id == ground.realm.entity.id)
            )
        )
    )
    return (
        HALF
        - ground.values.get(ValueAxis.LOYALTY, 0) / 2
        + distinct / 2
        + (cohesion - HALF) * table.separatism_cohesion_pct / PERCENT
        + grievances * table.separatism_grievance_pct / PERCENT
        - autonomy * table.separatism_autonomy_pct / PERCENT
        - privileges * table.separatism_privilege
    )


async def revival(ctx: TickContext, ground: Ground) -> float:
    return max(0.0, HALF - (stat(ground.community, "piety") or HALF) + ground.values.get(ValueAxis.PIETY, 0) / 2)


async def land_reform(ctx: TickContext, ground: Ground) -> float:
    serfdom = ground.laws.in_force(ground.realm.entity.id, LawKind.SERFDOM)
    if serfdom is None or not serfdom.params.get("allowed"):
        return 0.0
    return max(0.0, HALF - ground.farmers_content + ground.shares.get(SocialClass.FARMER, 0.0) / 2)


async def franchise(ctx: TickContext, ground: Ground) -> float:
    if ground.realm.profile.decision_rule in ASSEMBLIES:
        return 0.0
    return max(0.0, -ground.values.get(ValueAxis.HIERARCHY, 0) / 2)


PRESSURES: dict[MovementCause, Callable[[TickContext, Ground], Awaitable[float]]] = {
    MovementCause.ABOLITION: abolition,
    MovementCause.INDEPENDENCE: independence,
    MovementCause.REVIVAL: revival,
    MovementCause.LAND_REFORM: land_reform,
    MovementCause.FRANCHISE: franchise,
}


async def ground_of(ctx: TickContext, community: EntityRow, realm: Realm, laws: LawBook) -> Ground:
    society = await ctx.session.get(CommunitySocietyRow, community.id)
    content = society.satisfaction(SocialClass.FARMER) if society is not None else HALF
    return Ground(community, realm, laws, await values_for(ctx.session, community.id), await class_shares(ctx.session, ctx.rules, community.id), content)


async def movement_of(ctx: TickContext, realm_id: int, cause: MovementCause) -> MovementProfileRow | None:
    found: MovementProfileRow | None = await ctx.session.scalar(
        select(MovementProfileRow).where(MovementProfileRow.polity_entity_id == realm_id, MovementProfileRow.cause == cause).limit(1)
    )
    return found


async def found_movement(ctx: TickContext, realm: Realm, cause: MovementCause, home: EntityRow, laws: LawBook) -> MovementProfileRow:
    faction = await create_record(
        ctx,
        RecordSpec(
            entity_type=EntityType.FACTION,
            name=f"the {CAUSE_LABELS[cause]} movement of {home.name}",
            body=f"A movement for {CAUSE_LABELS[cause].lower()} that rose in {home.name}.",
            stats=FactionStats(strength=PERCENT // 5, wealth=PERCENT // 10, sway=PERCENT // 4),
            power=POWER,
            location_id=home.id if home.entity_type is EntityType.SETTLEMENT else home.location_id,
            world_id=home.world_id,
            subtype="movement",
        ),
    )
    ctx.session.add(FactionProfileRow(faction_entity_id=faction.id, kind=FactionKind.MOVEMENT, home_entity_id=home.id, influence_over={}, locked=[]))
    row = MovementProfileRow(faction_entity_id=faction.id, cause=cause, polity_entity_id=realm.entity.id, support=0, founded_epoch=ctx.epoch, locked=[])
    target = LAW_TARGETS.get(cause)
    law_row = laws.in_force(realm.entity.id, target) if target is not None else None
    law = law_row.law_entity_id if law_row is not None else None
    key = LawKind.FRANCHISE.value if cause is MovementCause.FRANCHISE else target.value if target is not None else None
    ctx.session.add(
        FactionGoalRow(
            faction_entity_id=faction.id,
            kind=GOALS[cause],
            target_node_id=law or realm.entity.id,
            target_key=key,
            priority=70,
            since_epoch=ctx.epoch,
            locked=[],
        )
    )
    ctx.session.add(row)
    await ctx.session.flush()
    return row


async def drift_support(ctx: TickContext, row: MovementProfileRow, community: EntityRow, aim: float) -> int:
    support = await ctx.session.get(MovementSupportRow, (row.faction_entity_id, community.id))
    if support is None:
        support = MovementSupportRow(movement_entity_id=row.faction_entity_id, community_entity_id=community.id, share=0)
        ctx.session.add(support)
    if not support.locked:
        support.share = clamp_int(support.share + round_half_up((aim - support.share) * ctx.rules.movements.drift_pct / PERCENT), 0, PERCENT)
    return support.share


async def protest(ctx: TickContext, community: EntityRow, share: int) -> bool:
    town = await ctx.session.get(SettlementProfileRow, community.id)
    if town is None or share < ctx.rules.movements.protest_at or "unrest" in (town.locked or []):
        return False
    town.unrest = clamp_int(town.unrest + round_half_up(share * ctx.rules.movements.protest_pct / PERCENT), 0, PERCENT)
    return True


async def rise(ctx: TickContext, realm: Realm, row: MovementProfileRow, strongest: EntityRow, *, tally: MovementTally, book: RealmBook) -> None:
    if row.cause is MovementCause.INDEPENDENCE and strongest.id in realm.members:
        await secede(ctx, book, realm, strongest)
    else:
        core = realm.profile.core_entity_id
        if core is None:
            return
        await declare_war(
            ctx,
            row.faction_entity_id,
            core,
            f"the {CAUSE_LABELS[row.cause].lower()} movement rose against {realm.entity.name}",
            cause=WarCause.UPRISING,
            world_cap=False,
        )
    await note(
        ctx,
        f"The movement for {CAUSE_LABELS[row.cause].lower()} rose in arms against {realm.entity.name}.",
        key="movements.revolt",
        ids=[row.faction_entity_id, realm.entity.id],
        kind=ChronicleKind.CIVILIZATION,
    )
    tally.revolts += 1


async def overturn(ctx: TickContext, realm: Realm, row: MovementProfileRow, laws: LawBook) -> bool:
    table = ctx.rules.affairs
    if row.cause is not MovementCause.FRANCHISE or row.support < table.revolution_at or realm.profile.stability >= table.revolution_stability:
        return False
    if laws.param(realm.entity.id, LawKind.CONSTITUTION, "voters") == "all":
        return False
    return await revolution(ctx, realm, laws)


async def tend_realm(ctx: TickContext, realm: Realm, laws: LawBook, book: RealmBook, tally: MovementTally) -> None:
    table = ctx.rules.movements
    members = [found for member in realm.members if (found := await ctx.session.get(EntityRow, member)) is not None and found.status is EntityStatus.CANON]
    grounds = {member.id: await ground_of(ctx, member, realm, laws) for member in members}
    for cause in MovementCause:
        aims = {member.id: await PRESSURES[cause](ctx, grounds[member.id]) for member in members}
        row = await movement_of(ctx, realm.entity.id, cause)
        mean = sum(aims.values()) / len(aims) if aims else 0.0
        if row is None:
            if mean < table.found_at or not members or not ctx.rng(seed_of("movement.found", realm.entity.id, cause.value, ctx.epoch)).chance(table.found_pct):
                continue
            home = max(members, key=lambda member: (aims[member.id], -member.id))
            row = await found_movement(ctx, realm, cause, home, laws)
            tally.founded += 1
        if held(row.faction_entity_id):
            continue
        shares = {member.id: await drift_support(ctx, row, member, aims[member.id]) for member in members}
        if SUPPORT not in (row.locked or []):
            row.support = clamp_int(sum(shares.values()) / len(shares) if shares else 0, 0, PERCENT)
        for member in members:
            tally.protests += await protest(ctx, member, shares[member.id])
        if await overturn(ctx, realm, row, laws):
            tally.revolutions += 1
            continue
        if realm.profile.decision_rule in ASSEMBLIES and not row.is_party and row.support >= table.party_at:
            row.is_party = True
            profile = await ctx.session.get(FactionProfileRow, row.faction_entity_id)
            if profile is not None and "kind" not in (profile.locked or []):
                profile.kind = FactionKind.PARTY
            tally.parties += 1
        elif realm.profile.decision_rule not in ASSEMBLIES and row.support >= table.revolt_at and members:
            strongest = max(members, key=lambda member: (shares[member.id], -member.id))
            if ctx.rng(seed_of("movement.rise", row.faction_entity_id, ctx.epoch)).chance(table.revolt_pct):
                await rise(ctx, realm, row, strongest, tally=tally, book=book)


async def tend_movements(ctx: TickContext, tally: MovementTally) -> None:
    book = await RealmBook.load(ctx.session)
    laws = await LawBook.load(ctx.session)
    for realm in list(book.realms.values()):
        if not held(realm.entity.id) and realm.members:
            await tend_realm(ctx, realm, laws, book, tally)
