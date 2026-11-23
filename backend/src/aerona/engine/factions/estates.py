from dataclasses import dataclass

from sqlalchemy import select

from aerona.catalog.civics import PRIVILEGE_GATES
from aerona.catalog.estates import ESTATE_CLASSES, ESTATE_LAWS, ESTATE_NAMES, PRIVILEGE_WISHES, RENTED
from aerona.catalog.estates import PRIVILEGES as PRIVILEGE_SPECS
from aerona.constants.units import PERCENT
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.estates import EstatePrivilegeRow, EstateProfileRow
from aerona.db.tables.factions import FactionProfileRow
from aerona.db.tables.polity import PolityMemberRow
from aerona.db.tables.society import CommunitySocietyRow
from aerona.db.write_guard import held
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.faction import EstatePrivilege, FactionKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.polity import LegitimacyBasis
from aerona.domain.enums.society import SocialClass
from aerona.domain.models.entity_stats import FactionStats
from aerona.engine.context import TickContext
from aerona.engine.lore.civics import polity_allows
from aerona.engine.polity.book import Realm, RealmBook
from aerona.engine.polity.enactment import propose
from aerona.engine.polity.policy import approval_of
from aerona.engine.primitives.naming import seed_of
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.records import RecordSpec, create_record
from aerona.engine.primitives.society import class_shares
from aerona.engine.primitives.stats import set_stats, stat
from aerona.engine.recording.record import record

LOYALTY = "loyalty"
INFLUENCE = "influence"
PRIVILEGES = "privileges"
POWER = 2
TEN = 10


@dataclass
class EstateTally:
    founded: int = 0
    granted: int = 0
    revoked: int = 0
    rents: int = 0
    proposals: int = 0


async def realm_shares(ctx: TickContext, realm: Realm) -> dict[SocialClass, float]:
    totals: dict[SocialClass, float] = {}
    members = list(realm.members)
    for member in members:
        for social_class, share in (await class_shares(ctx.session, ctx.rules, member)).items():
            totals[social_class] = totals.get(social_class, 0.0) + share
    return {social_class: value / len(members) for social_class, value in totals.items()} if members else {}


async def estates_by_class(ctx: TickContext) -> dict[tuple[int, SocialClass], EstateProfileRow]:
    found: dict[tuple[int, SocialClass], EstateProfileRow] = {}
    for row in await ctx.session.scalars(select(EstateProfileRow).order_by(EstateProfileRow.faction_entity_id)):
        found.setdefault((row.polity_entity_id, row.social_class), row)
    return found


async def privileges_of(ctx: TickContext, estate_id: int) -> set[EstatePrivilege]:
    return set(await ctx.session.scalars(select(EstatePrivilegeRow.privilege).where(EstatePrivilegeRow.estate_entity_id == estate_id)))


async def found_estate(ctx: TickContext, realm: Realm, social_class: SocialClass) -> EstateProfileRow:
    faction = await create_record(
        ctx,
        RecordSpec(
            entity_type=EntityType.FACTION,
            name=f"the {ESTATE_NAMES[social_class]} of {realm.entity.name}",
            body=f"The {ESTATE_NAMES[social_class].lower()} of {realm.entity.name}, gathered as an estate of the realm.",
            stats=FactionStats(strength=PERCENT // 4, wealth=PERCENT // 4, sway=PERCENT // 4),
            power=POWER,
            location_id=realm.profile.capital_entity_id,
            world_id=realm.entity.world_id,
            subtype="estate",
        ),
    )
    ctx.session.add(
        FactionProfileRow(faction_entity_id=faction.id, kind=FactionKind.ESTATE, home_entity_id=realm.profile.capital_entity_id, influence_over={}, locked=[])
    )
    row = EstateProfileRow(
        faction_entity_id=faction.id, polity_entity_id=realm.entity.id, social_class=social_class, loyalty=PERCENT // 2, influence=0, locked=[]
    )
    ctx.session.add(row)
    await ctx.session.flush()
    return row


async def class_mood(ctx: TickContext, realm: Realm, social_class: SocialClass) -> float:
    moods = [society.satisfaction(social_class) for member in realm.members if (society := await ctx.session.get(CommunitySocietyRow, member)) is not None]
    return sum(moods) / len(moods) if moods else PERCENT / 2


async def tend_estate(ctx: TickContext, realm: Realm, row: EstateProfileRow, share: float) -> None:
    table = ctx.rules.estates
    privileges = await privileges_of(ctx, row.faction_entity_id)
    if LOYALTY not in (row.locked or []):
        approval = await approval_of(ctx, realm.entity.id, row.social_class)
        bought = sum(getattr(table, PRIVILEGE_SPECS[privilege].loyalty) for privilege in privileges) * table.privilege_loyalty / TEN
        aim = PERCENT // 2 + bought + (await class_mood(ctx, realm, row.social_class) - PERCENT / 2) / 2 + approval / 2
        row.loyalty = clamp_int(row.loyalty + round_half_up((aim - row.loyalty) * table.loyalty_drift_pct / PERCENT), 0, PERCENT)
    if INFLUENCE not in (row.locked or []):
        seat = table.council_seat_influence if EstatePrivilege.COUNCIL_SEAT in privileges else 0
        row.influence = clamp_int(share * table.share_influence_pct / PERCENT + seat, 0, PERCENT)
    cost = sum(getattr(table, PRIVILEGE_SPECS[privilege].cost) for privilege in privileges)
    if cost > 0 and "treasury" not in realm.profile.locked:
        realm.profile.treasury = max(0, realm.profile.treasury - cost)
    profile = await ctx.session.get(FactionProfileRow, row.faction_entity_id)
    if profile is not None and "influence_over" not in (profile.locked or []):
        profile.influence_over = {**(profile.influence_over or {}), str(realm.entity.id): row.influence}


async def grant(ctx: TickContext, row: EstateProfileRow, privilege: EstatePrivilege) -> bool:
    if await ctx.session.get(EstatePrivilegeRow, (row.faction_entity_id, privilege)) is not None:
        return False
    if not await polity_allows(ctx.session, row.polity_entity_id, PRIVILEGE_GATES.get(privilege)):
        return False
    ctx.session.add(EstatePrivilegeRow(estate_entity_id=row.faction_entity_id, privilege=privilege, granted_epoch=ctx.epoch))
    await ctx.session.flush()
    return True


async def revoke(ctx: TickContext, row: EstateProfileRow, privilege: EstatePrivilege) -> bool:
    found = await ctx.session.get(EstatePrivilegeRow, (row.faction_entity_id, privilege))
    if found is None or found.locked:
        return False
    await ctx.session.delete(found)
    if LOYALTY not in (row.locked or []):
        row.loyalty = clamp_int(row.loyalty - ctx.rules.estates.revoke_loyalty, 0, PERCENT)
    return True


async def bargain(ctx: TickContext, realm: Realm, row: EstateProfileRow, tally: EstateTally) -> None:
    table = ctx.rules.estates
    if PRIVILEGES in (row.locked or []):
        return
    privileges = await privileges_of(ctx, row.faction_entity_id)
    wishes = [privilege for privilege in PRIVILEGE_WISHES[row.social_class] if privilege not in privileges]
    if row.loyalty <= table.grant_below and row.influence >= table.grant_influence and wishes:
        if await grant(ctx, row, wishes[0]):
            await record(
                ctx,
                "estates.granted",
                roles={IncidentRole.GIVER: realm.entity.id, IncidentRole.RECEIVER: row.faction_entity_id},
                facts={"estate": row.social_class, "privilege": wishes[0], "loyalty": row.loyalty, "influence": row.influence},
                place=realm.profile.capital_entity_id,
            )
            tally.granted += 1
        return
    needy = realm.profile.treasury < table.revoke_treasury
    exempt = EstatePrivilege.TAX_EXEMPTION in privileges
    if needy and row.loyalty >= table.revoke_above and exempt and await revoke(ctx, row, EstatePrivilege.TAX_EXEMPTION):
        await record(
            ctx,
            "estates.revoked",
            roles={IncidentRole.AUTHORITY: realm.entity.id, IncidentRole.VICTIM: row.faction_entity_id},
            facts={"estate": row.social_class, "privilege": EstatePrivilege.TAX_EXEMPTION, "treasury": realm.profile.treasury},
            place=realm.profile.capital_entity_id,
        )
        tally.revoked += 1


async def lobby(ctx: TickContext, realm: Realm, row: EstateProfileRow, tally: EstateTally) -> None:
    table = ctx.rules.estates
    kind, params = ESTATE_LAWS[row.social_class]
    if row.influence < table.grant_influence or not ctx.rng(seed_of("estate.lobby", row.faction_entity_id, ctx.epoch)).chance(table.propose_pct):
        return
    if await propose(ctx, realm, kind, dict(params), champion_id=row.faction_entity_id, basis=LegitimacyBasis.COUNCIL) is not None:
        tally.proposals += 1


async def tend_estates(ctx: TickContext, tally: EstateTally) -> None:
    table = ctx.rules.estates
    book = await RealmBook.load(ctx.session)
    estates = await estates_by_class(ctx)
    for realm in book.realms.values():
        if held(realm.entity.id) or not realm.members:
            continue
        shares = await realm_shares(ctx, realm)
        for social_class in SocialClass:
            share = shares.get(social_class, 0.0)
            row = estates.get((realm.entity.id, social_class))
            ready = social_class in ESTATE_CLASSES and row is None and share >= table.found_share and realm.profile.capital_entity_id is not None
            if ready and ctx.rng(seed_of("estate.found", realm.entity.id, social_class.value, ctx.epoch)).chance(table.found_pct):
                row = await found_estate(ctx, realm, social_class)
                tally.founded += 1
            if row is None or held(row.faction_entity_id):
                continue
            faction = await ctx.session.get(EntityRow, row.faction_entity_id)
            if faction is None or faction.status is not EntityStatus.CANON:
                continue
            await tend_estate(ctx, realm, row, share)
            await bargain(ctx, realm, row, tally)
            await lobby(ctx, realm, row, tally)


async def realm_of_community(ctx: TickContext, community_id: int) -> int | None:
    found: int | None = await ctx.session.scalar(select(PolityMemberRow.polity_entity_id).where(PolityMemberRow.member_entity_id == community_id).limit(1))
    return found


async def privileged_classes(ctx: TickContext, community_id: int, privilege: EstatePrivilege) -> set[SocialClass]:
    realm = await realm_of_community(ctx, community_id)
    if realm is None:
        return set()
    rows = await ctx.session.scalars(
        select(EstateProfileRow.social_class)
        .join(EstatePrivilegeRow, EstatePrivilegeRow.estate_entity_id == EstateProfileRow.faction_entity_id)
        .where(EstateProfileRow.polity_entity_id == realm, EstatePrivilegeRow.privilege == privilege)
    )
    return set(rows)


async def exempt_share(ctx: TickContext, community_id: int) -> float:
    exempt = await privileged_classes(ctx, community_id, EstatePrivilege.TAX_EXEMPTION)
    if not exempt:
        return 0.0
    shares = await class_shares(ctx.session, ctx.rules, community_id)
    return min(1.0, sum(shares.get(social_class, 0.0) for social_class in exempt) / PERCENT)


async def armed_share(ctx: TickContext, community_id: int) -> float:
    armed = await privileged_classes(ctx, community_id, EstatePrivilege.ARMS)
    shares = await class_shares(ctx.session, ctx.rules, community_id)
    return sum(shares.get(social_class, 0.0) for social_class in armed - {SocialClass.WARRIOR})


async def immune(ctx: TickContext, mortal: EntityRow) -> bool:
    if mortal.social_class is None or mortal.location_id is None:
        return False
    return mortal.social_class in await privileged_classes(ctx, mortal.location_id, EstatePrivilege.JUDICIAL_IMMUNITY)


async def monopoly_rent(ctx: TickContext, tally: EstateTally) -> None:
    rows = await ctx.session.scalars(
        select(EstateProfileRow)
        .join(EstatePrivilegeRow, EstatePrivilegeRow.estate_entity_id == EstateProfileRow.faction_entity_id)
        .where(EstatePrivilegeRow.privilege.in_(list(RENTED)))
        .order_by(EstateProfileRow.faction_entity_id)
    )
    for row in list(rows):
        faction = await ctx.session.get(EntityRow, row.faction_entity_id)
        if faction is None or held(faction.id):
            continue
        set_stats(faction, wealth=clamp_int((stat(faction, "wealth") or 0) + ctx.rules.estates.monopoly_rent, 0, PERCENT))
        tally.rents += 1
