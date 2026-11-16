from collections.abc import Mapping

from sqlalchemy import func, select

from aerona.constants.units import PERCENT
from aerona.core.total import total
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.estates import CompanyProfileRow
from aerona.db.tables.made import CompanyHoldingRow, CompanyPresenceRow, EnclaveRow
from aerona.db.tables.polity import PolityProfileRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.made import CompanyCharter, CompanyHoldingKind
from aerona.domain.enums.polity import GovernmentKind
from aerona.engine.context import TickContext
from aerona.engine.factions.companies import realm_of
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.notes import note
from aerona.engine.primitives.numbers import clamp_percent

HOLDING_WEIGHT: Mapping[CompanyHoldingKind, int] = total(
    CompanyHoldingKind,
    {
        CompanyHoldingKind.STRUCTURE: 100,
        CompanyHoldingKind.NETWORK: 150,
        CompanyHoldingKind.DATA_STORE: 120,
        CompanyHoldingKind.MADE_MIND: 130,
        CompanyHoldingKind.FABRICATOR: 140,
        CompanyHoldingKind.LIVING_LINE: 110,
        CompanyHoldingKind.ROUTE: 160,
        CompanyHoldingKind.ENCLAVE: 200,
    },
)
CHARTER_REACH: Mapping[CompanyCharter, tuple[bool, bool]] = total(
    CompanyCharter,
    {
        CompanyCharter.CHARTERED: (True, True),
        CompanyCharter.FREE: (True, True),
        CompanyCharter.STATE_OWNED: (False, False),
        CompanyCharter.COOPERATIVE: (False, True),
    },
)


async def holding_places(ctx: TickContext, company_id: int) -> list[tuple[int, int]]:
    places: list[tuple[int, int]] = []
    for holding in await ctx.session.scalars(select(CompanyHoldingRow).where(CompanyHoldingRow.company_entity_id == company_id).order_by(CompanyHoldingRow.id)):
        thing = await ctx.session.get(EntityRow, holding.holding_node_id)
        if thing is None:
            continue
        town = thing if thing.entity_type is EntityType.SETTLEMENT else await ctx.session.get(EntityRow, thing.location_id) if thing.location_id else None
        if town is not None and town.entity_type is EntityType.SETTLEMENT:
            places.append((town.id, HOLDING_WEIGHT[holding.kind]))
    return places


async def presence_in(ctx: TickContext, company_id: int, polity_id: int) -> CompanyPresenceRow:
    row = await ctx.session.get(CompanyPresenceRow, (company_id, polity_id))
    if row is None:
        row = CompanyPresenceRow(company_entity_id=company_id, polity_entity_id=polity_id, licensed=True, influence=0, locked=[])
        ctx.session.add(row)
    return row


async def take_enclave(ctx: TickContext, company: EntityRow, town_id: int) -> bool:
    if held(town_id) or await ctx.session.get(EnclaveRow, town_id) is not None:
        return False
    ctx.session.add(EnclaveRow(settlement_entity_id=town_id, company_entity_id=company.id, since_epoch=ctx.epoch, locked=[]))
    town = await ctx.session.get(EntityRow, town_id)
    await note(ctx, f"{company.name} came to hold {town.name if town else 'a town'} as its own enclave.", key="company.enclave", ids=[company.id, town_id])
    return True


async def capture(ctx: TickContext, company: EntityRow, polity_id: int) -> None:
    profile = await ctx.session.get(PolityProfileRow, polity_id)
    if profile is None or held(polity_id) or "government" in profile.locked or profile.government is GovernmentKind.OLIGARCHY:
        return
    profile.government = GovernmentKind.OLIGARCHY
    await note(ctx, f"{company.name} came to steer the realm it traded in.", key="company.capture", ids=[company.id, polity_id])


async def secede(ctx: TickContext, company: EntityRow) -> int:
    freed = 0
    for enclave in await ctx.session.scalars(select(EnclaveRow).where(EnclaveRow.company_entity_id == company.id)):
        town = await ctx.session.get(SettlementProfileRow, enclave.settlement_entity_id)
        if town is None or held(enclave.settlement_entity_id) or town.free_city:
            continue
        town.free_city, town.charter_entity_id = True, company.id
        freed += 1
    if freed:
        await note(ctx, f"The enclaves of {company.name} answered to no realm but the company.", key="company.sovereign", ids=[company.id])
    return freed


async def grow(ctx: TickContext, company: EntityRow, row: CompanyProfileRow) -> None:
    table = ctx.rules.company_power
    held_places = await holding_places(ctx, company.id)
    places = [town for town, _weight in held_places]
    captures, secedes = CHARTER_REACH[row.charter]
    realms: dict[int, int] = {}
    for town, weight in held_places:
        realm = await realm_of(ctx, town)
        if realm is not None:
            realms[realm] = realms.get(realm, 0) + weight
    for realm, weight in realms.items():
        presence = await presence_in(ctx, company.id, realm)
        if "influence" not in presence.locked:
            gain = weight * table.influence_per_holding // PERCENT if presence.licensed else 0
            presence.influence = clamp_percent(presence.influence + gain - table.influence_decay)
        if presence.influence >= table.enclave_influence:
            for town in places:
                if await realm_of(ctx, town) == realm:
                    await take_enclave(ctx, company, town)
        if captures and presence.influence >= table.capture_influence:
            await capture(ctx, company, realm)
    await ctx.session.flush()
    enclaves = int(await ctx.session.scalar(select(func.count()).where(EnclaveRow.company_entity_id == company.id)) or 0)
    if secedes and enclaves >= table.sovereignty_enclaves:
        await secede(ctx, company)


@reads("table.company_holdings", "table.company_profiles", "table.entities", "table.polity_members", "table.polity_profiles")
@writes("table.company_presences", "table.enclaves", "table.polity_profiles", "table.settlement_profiles")
async def keep_company_power(ctx: TickContext) -> None:
    for row in list(await ctx.session.scalars(select(CompanyProfileRow).order_by(CompanyProfileRow.faction_entity_id))):
        company = await ctx.session.get(EntityRow, row.faction_entity_id)
        if company is None or company.status is not EntityStatus.CANON or held(company.id):
            continue
        await grow(ctx, company, row)
        ctx.count("companies_weighed")
