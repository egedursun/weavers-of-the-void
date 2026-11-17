from dataclasses import dataclass

from sqlalchemy import func, select

from aerona.db.tables.demography import CohortRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.factions import FactionProfileRow
from aerona.db.tables.honours import VeteranGrantRow
from aerona.db.tables.polity import PolityMemberRow, PolityProfileRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.db.tables.warfare import WarRow
from aerona.db.write_guard import held
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.demography import CohortCondition
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.faction import FactionKind
from aerona.domain.enums.honours import VeteranGrant
from aerona.domain.enums.mind import MemoryKind, ValueAxis, ValueHolder
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.models.entity_stats import SettlementStats
from aerona.engine.body.customs import people_of
from aerona.engine.context import TickContext
from aerona.engine.economy.purse import coin_of, take_coin
from aerona.engine.mind.book import stored_values
from aerona.engine.phases.births import homeland_rule
from aerona.engine.phases.factions import found_faction
from aerona.engine.primitives.folk import towns_of_people
from aerona.engine.primitives.naming import Namer, seed_of
from aerona.engine.primitives.numbers import clamp_percent
from aerona.engine.primitives.queries import connect
from aerona.engine.primitives.records import RecordSpec, open_record
from aerona.engine.recording.record import FactInput, record
from aerona.engine.services.community_relations import change_relation
from aerona.engine.services.war import every_side, realms_of_side
from aerona.language.generator import NameKind


@dataclass
class VeteranTally:
    granted: int = 0
    colonies: int = 0
    pensions_paid: int = 0
    unpaid: int = 0
    associations: int = 0


async def veterans_in(ctx: TickContext, towns: list[int]) -> int:
    found = await ctx.session.scalar(
        select(func.coalesce(func.sum(CohortRow.count), 0)).where(CohortRow.community_entity_id.in_(towns), CohortRow.condition == CohortCondition.VETERAN)
    )
    return int(found or 0)


async def members_of(ctx: TickContext, polity_id: int) -> list[int]:
    return sorted(set(await ctx.session.scalars(select(PolityMemberRow.member_entity_id).where(PolityMemberRow.polity_entity_id == polity_id))))


async def frontier_of(ctx: TickContext, war: WarRow, realm_id: int) -> EntityRow | None:
    for side in await every_side(ctx.session, war.id):
        if realm_id in await realms_of_side(ctx.session, side.entity_id):
            continue
        foe = await ctx.session.get(EntityRow, side.entity_id)
        folk = await people_of(ctx.session, foe) if foe is not None else None
        for town_id in await towns_of_people(ctx.session, folk.id) if folk is not None else []:
            town = await ctx.session.get(EntityRow, town_id)
            region = await ctx.session.get(EntityRow, town.location_id) if town is not None and town.location_id is not None else None
            if region is not None and region.entity_type is EntityType.REGION:
                return region
    return None


async def found_colony(ctx: TickContext, realm: EntityRow, region: EntityRow, veterans: int) -> EntityRow | None:
    profile = await ctx.session.get(PolityProfileRow, realm.id)
    capital = await ctx.session.get(EntityRow, profile.capital_entity_id) if profile is not None and profile.capital_entity_id is not None else None
    folk = await people_of(ctx.session, capital) if capital is not None else None
    if folk is None:
        return None
    name = await Namer(ctx.session, ctx.rules).from_speaker(folk.id, seed_of("veteran.colony", realm.id, ctx.epoch), NameKind.PLACE)
    colony = await open_record(
        ctx.session,
        ctx.epoch,
        RecordSpec(
            entity_type=EntityType.SETTLEMENT,
            name=name or f"{folk.name} Colony",
            body=f"Veterans of {realm.name} were given land in {region.name} and settled it.",
            stats=SettlementStats(
                population=veterans, prosperity=ctx.rules.society.default_stat, defense=ctx.rules.society.default_stat, piety=ctx.rules.society.default_stat
            ),
            power=max(1, folk.power_level - 1),
            location_id=region.id,
            world_id=region.world_id,
            subtype="veteran colony",
        ),
    )
    await connect(ctx.session, colony.id, folk.id, BondKind.DESCENDS_FROM, ctx.epoch)
    await homeland_rule(ctx, folk, colony)
    ctx.session.add(PolityMemberRow(polity_entity_id=realm.id, member_entity_id=colony.id))
    await change_relation(ctx, colony.id, realm.id, ctx.rules.veterans.colony_loyalty, MemoryKind.GIFTED_ME, note="granted land to its veterans")
    return colony


async def grant(ctx: TickContext, war: WarRow, realm: EntityRow, tally: VeteranTally) -> None:
    table = ctx.rules.veterans
    towns = await members_of(ctx, realm.id)
    veterans = await veterans_in(ctx, towns)
    if veterans <= 0:
        return
    capital = await ctx.session.get(PolityProfileRow, realm.id)
    core = await ctx.session.get(EntityRow, capital.capital_entity_id) if capital is not None and capital.capital_entity_id is not None else None
    folk = await people_of(ctx.session, core) if core is not None else None
    martial = (await stored_values(ctx.session, ValueHolder.CULTURE, folk.id)).get(ValueAxis.MARTIAL, 0) if folk is not None else 0
    region = await frontier_of(ctx, war, realm.id) if martial >= table.land_martial_from and veterans >= table.colony_veterans else None
    colony = await found_colony(ctx, realm, region, veterans) if region is not None else None
    afford = await coin_of(ctx.session, ctx.rules, realm) >= veterans * table.pension_cost
    kind = VeteranGrant.LAND if colony is not None else VeteranGrant.PENSION if afford else VeteranGrant.NONE
    ctx.session.add(
        VeteranGrantRow(
            polity_entity_id=realm.id,
            kind=kind,
            veterans=veterans,
            settlement_entity_id=colony.id if colony is not None else None,
            war_entity_id=war.event_entity_id,
            epoch=ctx.epoch,
            locked=[],
        )
    )
    tally.granted += 1
    tally.colonies += colony is not None
    roles = {IncidentRole.ACTOR: realm.id, **({IncidentRole.PRODUCT: colony.id} if colony is not None else {})}
    facts: dict[str, FactInput] = {"grant": kind, "veterans": veterans}
    if region is not None:
        facts["region"] = region.id
    await record(ctx, "veterans.granted", roles=roles, facts=facts, place=colony.id if colony is not None else realm.id)


async def grant_after_wars(ctx: TickContext, tally: VeteranTally) -> None:
    granted = set(await ctx.session.scalars(select(VeteranGrantRow.war_entity_id).where(VeteranGrantRow.war_entity_id.is_not(None))))
    for war in list(await ctx.session.scalars(select(WarRow).where(WarRow.ended_epoch.in_([ctx.epoch - 1, ctx.epoch])).order_by(WarRow.id))):
        if war.event_entity_id in granted:
            continue
        realms: set[int] = set()
        for side in await every_side(ctx.session, war.id):
            realms |= await realms_of_side(ctx.session, side.entity_id)
        for realm_id in sorted(realms):
            realm = await ctx.session.get(EntityRow, realm_id)
            if realm is not None and realm.status is EntityStatus.CANON and not held(realm_id):
                await grant(ctx, war, realm, tally)


async def pay_pensions(ctx: TickContext, tally: VeteranTally) -> None:
    table = ctx.rules.veterans
    live = select(VeteranGrantRow).where(VeteranGrantRow.kind == VeteranGrant.PENSION, VeteranGrantRow.epoch > ctx.epoch - table.pension_years)
    for row in list(await ctx.session.scalars(live.order_by(VeteranGrantRow.id))):
        realm = await ctx.session.get(EntityRow, row.polity_entity_id)
        if realm is None or held(realm.id) or row.veterans <= 0:
            continue
        cost = row.veterans * table.pension_cost
        towns = await members_of(ctx, realm.id)
        if await take_coin(ctx.session, ctx.rules, realm, cost):
            for town_id in towns:
                purse = await ctx.session.get(SettlementProfileRow, town_id)
                if purse is not None and not held(town_id) and "treasury" not in purse.locked:
                    purse.treasury += cost // max(1, len(towns))
            tally.pensions_paid += 1
            continue
        tally.unpaid += 1
        for town_id in towns:
            await change_relation(ctx, town_id, realm.id, -table.unpaid_grievance, MemoryKind.BETRAYED_ME, note="left its veterans unpaid")


async def band_veterans(ctx: TickContext, tally: VeteranTally) -> None:
    table = ctx.rules.veterans
    rows = await ctx.session.execute(
        select(CohortRow.community_entity_id, func.sum(CohortRow.count))
        .where(CohortRow.condition == CohortCondition.VETERAN)
        .group_by(CohortRow.community_entity_id)
        .having(func.sum(CohortRow.count) >= table.association_from)
        .order_by(CohortRow.community_entity_id)
    )
    for town_id, _ in rows.all():
        town = await ctx.session.get(EntityRow, town_id)
        if town is None or town.status is not EntityStatus.CANON or town.entity_type is not EntityType.SETTLEMENT or held(town.id):
            continue
        standing = await ctx.session.scalar(
            select(FactionProfileRow.faction_entity_id)
            .join(EntityRow, EntityRow.id == FactionProfileRow.faction_entity_id)
            .where(FactionProfileRow.kind == FactionKind.VETERANS, FactionProfileRow.home_entity_id == town.id, EntityRow.status == EntityStatus.CANON)
            .limit(1)
        )
        if standing is not None:
            continue
        faction = await found_faction(ctx, town, FactionKind.VETERANS)
        tally.associations += 1
        await record(ctx, "veterans.association", roles={IncidentRole.ACTOR: town.id, IncidentRole.PRODUCT: faction.id}, place=town.id)


async def bitter_veterans(ctx: TickContext, tally: VeteranTally) -> None:
    table = ctx.rules.veterans
    unpaid = select(VeteranGrantRow).where(VeteranGrantRow.kind == VeteranGrant.NONE, VeteranGrantRow.epoch > ctx.epoch - table.pension_years)
    for row in list(await ctx.session.scalars(unpaid.order_by(VeteranGrantRow.id))):
        for town_id in await members_of(ctx, row.polity_entity_id):
            town = await ctx.session.get(SettlementProfileRow, town_id)
            if town is not None and not held(town_id) and "unrest" not in town.locked:
                town.unrest = clamp_percent(town.unrest + table.ungranted_unrest)
        tally.unpaid += 1


async def keep_veterans(ctx: TickContext, tally: VeteranTally) -> None:
    await grant_after_wars(ctx, tally)
    await pay_pensions(ctx, tally)
    await bitter_veterans(ctx, tally)
    await band_veterans(ctx, tally)
    await ctx.session.flush()
