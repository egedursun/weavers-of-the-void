from collections import Counter
from dataclasses import dataclass

from sqlalchemy import func, select

from aerona.constants.units import PERCENT
from aerona.db.repositories.names import NameRepository
from aerona.db.tables.afflictions import AfflictionRow
from aerona.db.tables.belonging import HeldIdentityRow
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.demography import PeopleCultureRow
from aerona.db.tables.ecology import SpeciesRangeRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.mind import CultureValueRow
from aerona.db.tables.polity import HouseProfileRow, PolityMemberRow
from aerona.db.tables.titles import TitleProfileRow
from aerona.db.tables.tongues import LanguagePolicyRow
from aerona.domain.enums.affliction import PackageKind, Transmission
from aerona.domain.enums.belonging import IdentityLayer, SalienceDriver
from aerona.domain.enums.bond import BondKind, BondRole, BondState
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.society import NaturalLaw
from aerona.domain.enums.tongues import LanguagePolicy
from aerona.domain.enums.transform import TransformTrigger
from aerona.domain.models.entity_stats import PeopleStats, SpeciesStats
from aerona.engine.body.afflictions import spec_of
from aerona.engine.context import TickContext
from aerona.engine.faith.book import FaithBook
from aerona.engine.interconnect.flows import FlowCategory, flowing
from aerona.engine.primitives.folk import folk_of, towns_of_people
from aerona.engine.primitives.naming import Namer, seed_of
from aerona.engine.primitives.numbers import clamp_int, clamp_percent
from aerona.engine.primitives.queries import canon, top_region
from aerona.engine.primitives.records import RecordSpec
from aerona.engine.primitives.stats import stat, stat_or
from aerona.engine.transform.ledger import Ledger
from aerona.engine.transform.moves import bind, bonds_from, end, make, unbind
from aerona.language.generator import NameKind

Push = tuple[int, TransformTrigger]
FERAL_INTELLIGENCE = 10


@dataclass(frozen=True)
class Forge:
    name_seed: str | None
    fallback: str
    body: str
    speaker_id: int
    location_id: int | None
    world_id: int | None
    sources: list[EntityRow]
    settlements: list[EntityRow]
    share_pct: int
    culture_from: int | None


async def members_of(ctx: TickContext, people: EntityRow) -> list[int]:
    statement = select(EntityRow.id).where(
        EntityRow.entity_type == EntityType.MORTAL, EntityRow.status == EntityStatus.CANON, await folk_of(ctx.session, people)
    )
    return list(await ctx.session.scalars(statement))


async def final_share(ctx: TickContext, members: list[int], *, package: PackageKind | None = None, curse: bool = False) -> int:
    if not members:
        return 0
    statement = select(AfflictionRow).where(AfflictionRow.bearer_node_id.in_(members), AfflictionRow.cured_epoch.is_(None))
    if package is not None:
        statement = statement.where(AfflictionRow.package == package)
    if curse:
        statement = statement.where(AfflictionRow.transmission == Transmission.CURSE)
    bearers = {row.bearer_node_id for row in await ctx.session.scalars(statement) if row.stage >= len(spec_of(row).stages)}
    return len(bearers) * PERCENT // len(members)


async def isolated(ctx: TickContext, people_id: int) -> bool:
    found = await ctx.session.scalar(
        select(func.count())
        .select_from(BondRow)
        .where(
            BondRow.kind == BondKind.TRADES_WITH,
            BondRow.state == BondState.ACTIVE,
            (BondRow.source_node_id == people_id) | (BondRow.target_node_id == people_id),
        )
    )
    return not found


async def sapience_pressures(ctx: TickContext) -> dict[int, Push]:
    table = ctx.rules.transform
    nature = await ctx.laws()
    found: dict[int, Push] = {}
    for people in await canon(ctx.session, [EntityType.PEOPLE]):
        members = await members_of(ctx, people)
        void = await final_share(ctx, members, package=PackageKind.VOID_TAINT)
        if void >= table.sapience_void_pct:
            found[people.id] = (PERCENT, TransformTrigger.VOID)
            continue
        curse = await final_share(ctx, members, curse=True)
        if curse >= table.sapience_void_pct:
            found[people.id] = (PERCENT, TransformTrigger.CURSE)
            continue
        ruined = stat_or(people, "prosperity", ctx.rules.society.default_stat) < ctx.rules.knowledge.dark_age_prosperity
        if ruined and nature.has(NaturalLaw.GIFT_WITHERING, people.world_id) and await isolated(ctx, people.id):
            found[people.id] = (PERCENT, TransformTrigger.DARK_AGE)
    return found


async def people_check(ctx: TickContext, people_id: int) -> str | None:
    people = await ctx.session.get(EntityRow, people_id)
    if people is None or people.entity_type is not EntityType.PEOPLE or people.status is not EntityStatus.CANON:
        return "Only a living people can lose its sapience."
    return None


async def lose_sapience(ctx: TickContext, people_id: int, ledger: Ledger) -> int:
    people = await ctx.session.get_one(EntityRow, people_id)
    density = ctx.rules.transform.people_to_species_density
    population = stat(people, "population") or 0
    species = await make(
        ctx,
        ledger,
        RecordSpec(
            entity_type=EntityType.SPECIES,
            name=await NameRepository(ctx.session).unique_name(f"Feral {people.name}"),
            body=f"What is left of the people {people.name} after they lost speech and reckoning.",
            stats=SpeciesStats(
                strength=clamp_percent(stat_or(people, "martiality", PERCENT // 2)),
                intelligence=FERAL_INTELLIGENCE,
                danger=clamp_percent(stat_or(people, "martiality", PERCENT // 2)),
                abundance=clamp_percent(population // density),
            ),
            power=people.power_level,
            world_id=people.world_id,
            location_id=people.location_id,
        ),
    )
    with flowing(FlowCategory.TRANSFORMATION):
        for town_id in await towns_of_people(ctx.session, people.id):
            town = await ctx.session.get_one(EntityRow, town_id)
            region = await top_region(ctx.session, town)
            kept = stat(town, "population") or 0
            if region is not None:
                row = SpeciesRangeRow(
                    species_entity_id=species.id,
                    region_entity_id=region.id,
                    abundance=clamp_percent(kept // density),
                    since_epoch=ctx.epoch,
                    updated_epoch=ctx.epoch,
                    locked=[],
                )
                existing = await ctx.session.get(SpeciesRangeRow, (species.id, region.id))
                if existing is None:
                    ctx.session.add(row)
                    await ctx.session.flush()
                    ledger.added(row)
                else:
                    ledger.set(existing, "abundance", clamp_percent(existing.abundance + kept // density))
            ledger.stat(town, "population", 0)
        ledger.stat(people, "population", 0)
    for bond in await bonds_from(ctx, people.id, (BondKind.SPEAKS,)):
        unbind(ctx, ledger, bond, "its speakers lost speech")
    for title in await ctx.session.scalars(select(TitleProfileRow).where(TitleProfileRow.holder_node_id == people.id)):
        ledger.set(title, "holder_node_id", None)
    await bind(ctx, ledger, (species.id, people.id, BondKind.DESCENDS_FROM), f"what is left of {people.name}")
    end(ctx, ledger, people, EntityStatus.DESTROYED)
    return species.id


async def forge_people(ctx: TickContext, ledger: Ledger, forge: Forge) -> EntityRow:
    named = await Namer(ctx.session, ctx.rules).from_speaker(forge.speaker_id, forge.name_seed, NameKind.PEOPLE) if forge.name_seed is not None else None
    moved = 0
    with flowing(FlowCategory.MERGE):
        for source in forge.sources:
            have = stat(source, "population") or 0
            share = have * forge.share_pct // PERCENT
            if share > 0:
                ledger.stat(source, "population", have - share)
                moved += share
    lead = forge.sources[0] if forge.sources else None
    people = await make(
        ctx,
        ledger,
        RecordSpec(
            entity_type=EntityType.PEOPLE,
            name=await NameRepository(ctx.session).unique_name(named or forge.fallback),
            body=forge.body,
            stats=PeopleStats(
                population=max(ctx.rules.limits.people_population_floor, moved),
                martiality=stat(lead, "martiality") if lead is not None else None,
                craft=stat(lead, "craft") if lead is not None else None,
                piety=stat(lead, "piety") if lead is not None else None,
            ),
            power=max((source.power_level for source in forge.sources), default=1),
            world_id=forge.world_id,
            location_id=forge.location_id,
        ),
    )
    for settlement in forge.settlements:
        await bind(ctx, ledger, (settlement.id, people.id, BondKind.DESCENDS_FROM), "a home of the new people")
        await bind(ctx, ledger, (people.id, settlement.id, BondKind.LIVES_IN), "homeland", role=BondRole.HOMELAND)
    for source in forge.sources:
        await bind(ctx, ledger, (people.id, source.id, BondKind.DESCENDS_FROM), f"forged in part from {source.name}")
    if forge.culture_from is not None:
        for value in await ctx.session.scalars(select(CultureValueRow).where(CultureValueRow.entity_id == forge.culture_from)):
            row = CultureValueRow(entity_id=people.id, axis=value.axis, value=value.value)
            ctx.session.add(row)
            await ctx.session.flush()
            ledger.added(row)
    return people


async def identify(ctx: TickContext, ledger: Ledger, holder_id: int, layer: IdentityLayer, *, value_id: int, label: str) -> None:
    row = HeldIdentityRow(
        holder_entity_id=holder_id,
        layer=layer,
        value_node_id=value_id,
        value_label=label,
        strength=PERCENT,
        salience=PERCENT,
        driver=SalienceDriver.BASELINE,
        updated_epoch=ctx.epoch,
        locked=[],
    )
    ctx.session.add(row)
    await ctx.session.flush()
    ledger.added(row)


def peoples_and_towns(members: list[EntityRow]) -> tuple[list[EntityRow], list[EntityRow]]:
    return [row for row in members if row.entity_type is EntityType.PEOPLE], [row for row in members if row.entity_type is EntityType.SETTLEMENT]


async def endogamous(ctx: TickContext, peoples: list[EntityRow]) -> bool:
    for people in peoples:
        culture = await ctx.session.get(PeopleCultureRow, people.id)
        if culture is not None and culture.endogamous:
            return True
    return False


async def ethnoreligious_pressures(ctx: TickContext) -> dict[int, Push]:
    table = ctx.rules.transform
    book = await FaithBook.load(ctx.session)
    found: dict[int, Push] = {}
    for cult_id, church in sorted(book.churches.items()):
        peoples, towns = peoples_and_towns(church.members)
        if stat_or(church.cult, "zeal", 0) < table.ethnoreligious_cohesion or len(peoples) + len(towns) <= table.ethnoreligious_lands:
            continue
        if await endogamous(ctx, peoples):
            found[cult_id] = (PERCENT, TransformTrigger.ENGINE)
    return found


async def cult_check(ctx: TickContext, cult_id: int) -> str | None:
    cult = await ctx.session.get(EntityRow, cult_id)
    if cult is None or cult.entity_type is not EntityType.CULT or cult.status is not EntityStatus.CANON:
        return "Only a living faith can become a people."
    return None


async def faith_to_people(ctx: TickContext, cult_id: int, ledger: Ledger) -> int:
    cult = await ctx.session.get_one(EntityRow, cult_id)
    church = (await FaithBook.load(ctx.session)).churches.get(cult.id)
    peoples, towns = peoples_and_towns(church.members if church is not None else [])
    lead = peoples[0] if peoples else None
    people = await forge_people(
        ctx,
        ledger,
        Forge(
            name_seed=seed_of("ethnoreligious", cult.id, ctx.epoch),
            fallback=f"People of {cult.name}",
            body=f"The faithful of {cult.name}, who married among themselves across many lands until they were a people of their own.",
            speaker_id=(towns[0].id if towns else lead.id if lead is not None else cult.id),
            location_id=cult.location_id,
            world_id=cult.world_id,
            sources=peoples,
            settlements=towns,
            share_pct=ctx.rules.transform.ethnoreligious_share_pct,
            culture_from=lead.id if lead is not None else None,
        ),
    )
    await identify(ctx, ledger, people.id, IdentityLayer.FAITH, value_id=cult.id, label=cult.name)
    patrons = await bonds_from(ctx, cult.id, (BondKind.WORSHIPS,))
    for bond in patrons:
        await bind(ctx, ledger, (people.id, bond.target_node_id, BondKind.WORSHIPS), f"the faith of {cult.name}")
    return people.id


async def realm_members(ctx: TickContext, polity_id: int) -> list[EntityRow]:
    ids = list(await ctx.session.scalars(select(PolityMemberRow.member_entity_id).where(PolityMemberRow.polity_entity_id == polity_id)))
    if not ids:
        return []
    statement = select(EntityRow).where(EntityRow.id.in_(ids), EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id)
    return list(await ctx.session.scalars(statement))


async def nation_pressures(ctx: TickContext) -> dict[int, Push]:
    table = ctx.rules.transform
    official = set(await ctx.session.scalars(select(LanguagePolicyRow.holder_entity_id).where(LanguagePolicyRow.policy == LanguagePolicy.OFFICIAL)))
    found: dict[int, Push] = {}
    for polity in await canon(ctx.session, [EntityType.POLITY]):
        if polity.id not in official:
            continue
        members = await realm_members(ctx, polity.id)
        if not members:
            continue
        ids = [member.id for member in members]
        salience = await ctx.session.scalar(
            select(func.avg(HeldIdentityRow.salience)).where(
                HeldIdentityRow.holder_entity_id.in_(ids), HeldIdentityRow.layer == IdentityLayer.POLITY, HeldIdentityRow.value_node_id == polity.id
            )
        )
        peoples, _ = peoples_and_towns(members)
        cultures = [row for row in [await ctx.session.get(PeopleCultureRow, people.id) for people in peoples] if row is not None]
        literacy = sum(row.literacy for row in cultures) // len(cultures) if cultures else 0
        if (salience or 0) >= table.nation_salience and literacy >= table.nation_literacy:
            found[polity.id] = (PERCENT, TransformTrigger.ENGINE)
    return found


async def polity_check(ctx: TickContext, polity_id: int) -> str | None:
    polity = await ctx.session.get(EntityRow, polity_id)
    if polity is None or polity.entity_type is not EntityType.POLITY or polity.status is not EntityStatus.CANON:
        return "Only a living realm can forge a people."
    if not await realm_members(ctx, polity_id):
        return f"{polity.name} has no subjects to forge a people from."
    return None


async def realm_to_people(ctx: TickContext, polity_id: int, ledger: Ledger) -> int:
    polity = await ctx.session.get_one(EntityRow, polity_id)
    peoples, towns = peoples_and_towns(await realm_members(ctx, polity.id))
    weight = Counter({people.id: stat(people, "population") or 0 for people in peoples})
    lead = max(peoples, key=lambda row: (weight[row.id], -row.id)) if peoples else None
    people = await forge_people(
        ctx,
        ledger,
        Forge(
            name_seed=seed_of("nation", polity.id, ctx.epoch),
            fallback=f"People of {polity.name}",
            body=f"The subjects of {polity.name}, schooled in one tongue under one name until they were a people of their own.",
            speaker_id=polity.id,
            location_id=polity.location_id,
            world_id=polity.world_id,
            sources=peoples,
            settlements=towns,
            share_pct=PERCENT,
            culture_from=lead.id if lead is not None else None,
        ),
    )
    await identify(ctx, ledger, people.id, IdentityLayer.POLITY, value_id=polity.id, label=polity.name)
    for source in peoples:
        if stat(source, "population") == 0:
            end(ctx, ledger, source, EntityStatus.DESTROYED)
    return people.id


async def house_members(ctx: TickContext, house_id: int) -> int:
    found = await ctx.session.scalar(
        select(func.count())
        .select_from(BondRow)
        .join(EntityRow, EntityRow.id == BondRow.source_node_id)
        .where(
            BondRow.target_node_id == house_id,
            BondRow.kind == BondKind.MEMBER_OF,
            BondRow.state == BondState.ACTIVE,
            EntityRow.status == EntityStatus.CANON,
        )
    )
    return int(found or 0)


async def house_pressures(ctx: TickContext) -> dict[int, Push]:
    table = ctx.rules.transform
    found: dict[int, Push] = {}
    for house in await canon(ctx.session, [EntityType.HOUSE]):
        if ctx.epoch - house.birth_epoch < table.house_generations:
            continue
        if await house_members(ctx, house.id) >= table.house_members:
            found[house.id] = (PERCENT, TransformTrigger.ENGINE)
    return found


async def house_check(ctx: TickContext, house_id: int) -> str | None:
    house = await ctx.session.get(EntityRow, house_id)
    if house is None or house.entity_type is not EntityType.HOUSE or house.status is not EntityStatus.CANON:
        return "Only a living house can grow into a people."
    return None


async def house_to_people(ctx: TickContext, house_id: int, ledger: Ledger) -> int:
    house = await ctx.session.get_one(EntityRow, house_id)
    profile = await ctx.session.get(HouseProfileRow, house.id)
    founder = await ctx.session.get(EntityRow, profile.founder_entity_id) if profile is not None and profile.founder_entity_id is not None else None
    seat = await ctx.session.get(EntityRow, house.location_id) if house.location_id is not None else None
    origin = await ctx.session.get(EntityRow, founder.affiliated_entity_id) if founder is not None and founder.affiliated_entity_id is not None else None
    sources = [origin] if origin is not None and origin.entity_type is EntityType.PEOPLE else []
    towns = [seat] if seat is not None and seat.entity_type is EntityType.SETTLEMENT else []
    people = await forge_people(
        ctx,
        ledger,
        Forge(
            name_seed=None,
            fallback=founder.name if founder is not None else house.name,
            body=f"The house {house.name}, grown over generations of kin into a people named for "
            + (founder.name if founder is not None else "its founder")
            + ".",
            speaker_id=house.id,
            location_id=house.location_id,
            world_id=house.world_id,
            sources=sources,
            settlements=towns,
            share_pct=clamp_int(await house_members(ctx, house.id), 0, PERCENT),
            culture_from=origin.id if origin is not None else None,
        ),
    )
    await identify(ctx, ledger, people.id, IdentityLayer.HOUSE, value_id=house.id, label=house.name)
    return people.id
