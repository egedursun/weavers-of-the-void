from sqlalchemy import select

from aerona.db.tables.city_rules import ConurbationRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.polity import LawJurisdictionRow, PolityMemberRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.city_rules import ConurbationGovernance
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.polity import Jurisdiction
from aerona.domain.enums.urban import Morphology
from aerona.engine.body.customs import people_of
from aerona.engine.city_rules.book import CityTally
from aerona.engine.context import TickContext
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.queries import living_entity
from aerona.engine.primitives.stats import stat
from aerona.engine.recording.record import record
from aerona.engine.services.war import current_war

SAME_REALM = 40
SAME_PEOPLE = 30
SPREAD = 20
LARGE = 10
LARGE_PEOPLE = 20000
SPREADING = frozenset({Morphology.SPRAWL, Morphology.CONCENTRIC, Morphology.GRID})
SPREADING_LAWS = frozenset({ConurbationGovernance.ONE_COUNCIL, ConurbationGovernance.RULED_BY_CORE})


async def open_conurbations(ctx: TickContext) -> list[ConurbationRow]:
    return list(await ctx.session.scalars(select(ConurbationRow).where(ConurbationRow.split_epoch.is_(None)).order_by(ConurbationRow.id)))


async def conurbation_of(ctx: TickContext, town_id: int) -> ConurbationRow | None:
    return next((row for row in await open_conurbations(ctx) if town_id == row.core_entity_id or town_id in (row.members or [])), None)


async def ties(ctx: TickContext, first: EntityRow, second: EntityRow) -> int:
    realms = select(PolityMemberRow.polity_entity_id).where(PolityMemberRow.member_entity_id == first.id)
    shared = select(PolityMemberRow.polity_entity_id).where(PolityMemberRow.member_entity_id == second.id, PolityMemberRow.polity_entity_id.in_(realms))
    score = SAME_REALM if await ctx.session.scalar(shared.limit(1)) is not None else 0
    first_folk, second_folk = await people_of(ctx.session, first), await people_of(ctx.session, second)
    if first_folk is not None and second_folk is not None and first_folk.id == second_folk.id:
        score += SAME_PEOPLE
    first_profile = await ctx.session.get(SettlementProfileRow, first.id)
    second_profile = await ctx.session.get(SettlementProfileRow, second.id)
    if first_profile is not None and second_profile is not None and {first_profile.morphology, second_profile.morphology} & SPREADING:
        score += SPREAD
    if (stat(first, "population") or 0) + (stat(second, "population") or 0) >= LARGE_PEOPLE:
        score += LARGE
    return score


async def spread_laws(ctx: TickContext, row: ConurbationRow) -> None:
    if row.governance not in SPREADING_LAWS or "imposed_laws" in (row.locked or []):
        return
    laws = sorted(set(await ctx.session.scalars(select(LawJurisdictionRow.law_entity_id).where(LawJurisdictionRow.node_entity_id == row.core_entity_id))))
    for member in row.members or []:
        for law in laws:
            if await ctx.session.get(LawJurisdictionRow, (law, member)) is None:
                ctx.session.add(LawJurisdictionRow(law_entity_id=law, node_entity_id=member, jurisdiction=Jurisdiction.SETTLEMENT))
    row.imposed_laws = sorted(set(row.imposed_laws or []) | set(laws))
    await ctx.session.flush()


async def lift_laws(ctx: TickContext, row: ConurbationRow) -> None:
    for law in row.imposed_laws or []:
        for member in row.members or []:
            found = await ctx.session.get(LawJurisdictionRow, (law, member))
            if found is not None:
                await ctx.session.delete(found)
    row.imposed_laws = []


async def join(
    ctx: TickContext, core: EntityRow, members: list[EntityRow], governance: ConurbationGovernance, tally: CityTally, *, by: int | None = None
) -> ConurbationRow:
    found = await conurbation_of(ctx, core.id)
    row = found or ConurbationRow(core_entity_id=core.id, members=[], governance=governance, joined_epoch=ctx.epoch, imposed_laws=[], locked=[])
    row.members = sorted({*(row.members or []), *(member.id for member in members if member.id != core.id)})
    if found is None:
        ctx.session.add(row)
    await ctx.session.flush()
    await spread_laws(ctx, row)
    tally.joined += 1
    await record(
        ctx,
        "city.settlements_joined",
        roles={IncidentRole.SUBJECT: core.id, IncidentRole.ACTOR: by, IncidentRole.MEMBER: [member.id for member in members]},
        facts={"governance": governance, "members": len(row.members)},
    )
    return row


async def split(ctx: TickContext, row: ConurbationRow, tally: CityTally) -> None:
    await lift_laws(ctx, row)
    row.split_epoch = ctx.epoch
    tally.split += 1
    await record(ctx, "city.conurbation_split", roles={IncidentRole.SUBJECT: row.core_entity_id}, facts={"members": len(row.members or [])})


async def strained(ctx: TickContext, row: ConurbationRow) -> bool:
    core = await ctx.session.get(SettlementProfileRow, row.core_entity_id)
    for member in row.members or []:
        profile = await ctx.session.get(SettlementProfileRow, member)
        if await current_war(ctx.session, row.core_entity_id, member) is not None:
            return True
        if core is not None and profile is not None and profile.unrest - core.unrest >= ctx.rules.city_rules.split_unrest_gap:
            return True
    return False


async def share_unrest(ctx: TickContext, row: ConurbationRow) -> None:
    if row.governance is not ConurbationGovernance.ONE_COUNCIL:
        return
    profiles = [
        profile for profile in [await ctx.session.get(SettlementProfileRow, town) for town in [row.core_entity_id, *(row.members or [])]] if profile is not None
    ]
    if not profiles:
        return
    mean = sum(profile.unrest for profile in profiles) // len(profiles)
    for profile in profiles:
        if "unrest" not in (profile.locked or []):
            profile.unrest = mean


async def grow_together(ctx: TickContext, tally: CityTally) -> None:
    atlas = await RegionAtlas.load(ctx.session)
    threshold = ctx.rules.city_rules.join_tie_threshold
    regions = select(EntityRow.id).where(EntityRow.entity_type == EntityType.REGION, EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id)
    for region in list(await ctx.session.scalars(regions)):
        towns = [town for town in [await living_entity(ctx.session, node) for node in atlas.communities_in(region)] if town is not None]
        towns = sorted(
            [town for town in towns if town.entity_type is EntityType.SETTLEMENT and not held(town.id)],
            key=lambda town: (-(stat(town, "population") or 0), town.id),
        )
        if len(towns) < 2:
            continue
        core = towns[0]
        joining = [town for town in towns[1:] if await conurbation_of(ctx, town.id) is None and await ties(ctx, core, town) >= threshold]
        if joining:
            await join(ctx, core, joining, ConurbationGovernance.FEDERATED_COUNCILS, tally)


async def tend_conurbations(ctx: TickContext, tally: CityTally) -> None:
    for row in await open_conurbations(ctx):
        if held(row.core_entity_id) or "split_epoch" in (row.locked or []):
            continue
        core = await living_entity(ctx.session, row.core_entity_id)
        alive = [member for member in row.members or [] if await living_entity(ctx.session, member) is not None]
        if core is None or not alive or await strained(ctx, row):
            await split(ctx, row, tally)
            continue
        row.members = alive
        await spread_laws(ctx, row)
        await share_unrest(ctx, row)
    await grow_together(ctx, tally)
