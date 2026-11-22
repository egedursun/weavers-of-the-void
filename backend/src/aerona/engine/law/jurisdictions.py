from dataclasses import dataclass

from sqlalchemy import select

from aerona.catalog.life.domain import GUILD_KINDS
from aerona.constants.units import PERCENT
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.factions import FactionMembershipRow, FactionProfileRow
from aerona.db.tables.justice import CrimeCaseRow
from aerona.db.tables.law_depth import JurisdictionRow
from aerona.db.tables.polity import PolityMemberRow, PolityProfileRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.db.tables.urban import TradingPostRow
from aerona.db.write_guard import held
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.law_depth import CourtLevel, JurisdictionClaim
from aerona.domain.enums.mind import MemoryKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.context import TickContext
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.recording.record import record
from aerona.engine.services.community_relations import change_relation

STRENGTH = "strength"


@dataclass
class JurisdictionTally:
    claimed: int = 0
    struggles: int = 0
    crushed: int = 0


async def towns_of(ctx: TickContext, polity_id: int) -> list[int]:
    return list(await ctx.session.scalars(select(PolityMemberRow.member_entity_id).where(PolityMemberRow.polity_entity_id == polity_id)))


async def claimants(ctx: TickContext, polity_id: int) -> list[tuple[int, JurisdictionClaim]]:
    found: list[tuple[int, JurisdictionClaim]] = []
    profile = await ctx.session.get(PolityProfileRow, polity_id)
    if profile is not None and profile.state_religion_id is not None:
        found.append((profile.state_religion_id, JurisdictionClaim.CLERGY))
    towns = await towns_of(ctx, polity_id)
    guilds = await ctx.session.scalars(
        select(EntityRow.id)
        .join(FactionProfileRow, FactionProfileRow.faction_entity_id == EntityRow.id)
        .where(FactionProfileRow.kind.in_(list(GUILD_KINDS)), EntityRow.location_id.in_(towns), EntityRow.status == EntityStatus.CANON)
        .order_by(EntityRow.id)
    )
    found.extend((guild, JurisdictionClaim.GUILD) for guild in guilds)
    posts = await ctx.session.scalars(select(TradingPostRow.owner_entity_id).where(TradingPostRow.host_settlement_id.in_(towns)))
    for owner_id in set(posts):
        owner = await ctx.session.get(EntityRow, owner_id) if owner_id is not None else None
        home = owner.affiliated_entity_id or owner.location_id if owner is not None else None
        realm = await ctx.session.scalar(select(PolityMemberRow.polity_entity_id).where(PolityMemberRow.member_entity_id == home).limit(1)) if home else None
        if realm is not None and realm != polity_id:
            found.append((realm, JurisdictionClaim.FOREIGN))
    return sorted(set(found), key=lambda item: (item[0], item[1].value))


async def make_claims(ctx: TickContext, polity_id: int, tally: JurisdictionTally) -> None:
    for claimant, claim in await claimants(ctx, polity_id):
        if held(claimant) or await ctx.session.get(JurisdictionRow, (polity_id, claimant, claim)) is not None:
            continue
        if ctx.rng(f"law.claim.{polity_id}.{claimant}.{claim.value}").chance(ctx.rules.jurisdictions.claim_pct):
            ctx.session.add(
                JurisdictionRow(holder_entity_id=polity_id, claimant_entity_id=claimant, claim=claim, strength=10, since_epoch=ctx.epoch, locked=[])
            )
            tally.claimed += 1
    await ctx.session.flush()


async def struggle(ctx: TickContext, row: JurisdictionRow, tally: JurisdictionTally) -> None:
    table = ctx.rules.jurisdictions
    profile = await ctx.session.get(PolityProfileRow, row.holder_entity_id)
    seat = await ctx.session.get(SettlementProfileRow, profile.capital_entity_id or -1) if profile is not None else None
    if seat is not None and "unrest" not in (seat.locked or []) and not held(seat.settlement_entity_id):
        seat.unrest = clamp_int(seat.unrest + table.struggle_unrest, 0, PERCENT)
    await change_relation(
        ctx, row.holder_entity_id, row.claimant_entity_id, -table.struggle_relation, MemoryKind.BETRAYED_ME, note="a struggle over the courts"
    )
    tally.struggles += 1
    stability = profile.stability if profile is not None else 0
    if STRENGTH in row.locked or not ctx.rng(f"law.crown.{row.holder_entity_id}.{row.claimant_entity_id}").chance(table.crown_pct * stability / PERCENT):
        return
    await ctx.session.delete(row)
    tally.crushed += 1
    realm, claimant = await ctx.session.get(EntityRow, row.holder_entity_id), await ctx.session.get(EntityRow, row.claimant_entity_id)
    if realm is not None and claimant is not None:
        await record(
            ctx,
            f"law.jurisdiction_crushed_{row.claim.value}",
            roles={IncidentRole.AUTHORITY: realm.id, IncidentRole.VICTIM: claimant.id},
            facts={"chance": table.crown_pct * stability / PERCENT},
        )


async def press_claims(ctx: TickContext, tally: JurisdictionTally) -> None:
    table = ctx.rules.jurisdictions
    realms = await ctx.session.scalars(
        select(EntityRow.id).where(EntityRow.entity_type == EntityType.POLITY, EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id)
    )
    for polity_id in list(realms):
        if held(polity_id):
            continue
        await make_claims(ctx, polity_id, tally)
        rows = await ctx.session.scalars(
            select(JurisdictionRow)
            .where(JurisdictionRow.holder_entity_id == polity_id, JurisdictionRow.since_epoch < ctx.epoch)
            .order_by(JurisdictionRow.claimant_entity_id)
        )
        for row in list(rows):
            if held(row.claimant_entity_id):
                continue
            if STRENGTH not in row.locked:
                row.strength = clamp_int(row.strength + table.growth, 0, PERCENT)
            if row.strength >= table.struggle_at:
                await struggle(ctx, row, tally)
    await ctx.session.flush()


async def belongs(ctx: TickContext, mortal: EntityRow, claimant_id: int, claim: JurisdictionClaim) -> bool:
    if mortal.affiliated_entity_id == claimant_id:
        return True
    if claim is JurisdictionClaim.GUILD:
        member = await ctx.session.get(FactionMembershipRow, (claimant_id, mortal.id))
        return member is not None
    if claim is JurisdictionClaim.FOREIGN:
        home = mortal.affiliated_entity_id
        realm = await ctx.session.scalar(select(PolityMemberRow.polity_entity_id).where(PolityMemberRow.member_entity_id == home).limit(1)) if home else None
        return realm == claimant_id
    return False


async def claimed_court(ctx: TickContext, case: CrimeCaseRow, accused: EntityRow) -> None:
    if case.polity_entity_id is None:
        return
    rows = await ctx.session.scalars(
        select(JurisdictionRow).where(JurisdictionRow.holder_entity_id == case.polity_entity_id).order_by(JurisdictionRow.strength.desc())
    )
    for row in list(rows):
        if not await belongs(ctx, accused, row.claimant_entity_id, row.claim):
            continue
        if "evidence" not in case.locked:
            case.evidence = clamp_int(case.evidence - round_half_up(ctx.rules.jurisdictions.leniency * row.strength / PERCENT), 0, PERCENT)
        if row.claim is JurisdictionClaim.CLERGY and "court" not in case.locked:
            case.court = CourtLevel.RELIGIOUS
        return
