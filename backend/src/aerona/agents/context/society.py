from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.agents.context.lore import lore_lines
from aerona.agents.context.military import army_sheet, fleet_sheet, grievance_sheet, intrigue_sheet, war_sheet
from aerona.agents.context.realm import statecraft
from aerona.agents.context.society_depth import depth_lines
from aerona.agents.context.wilds import crop_lines, pet_lines, wild_lines
from aerona.core.grammar import several
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.demography import CohortRow, PeopleBiologyRow, PeopleCultureRow
from aerona.db.tables.disease import DiseaseProfileRow, EndemicDiseaseRow, OutbreakRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.faith import CultDoctrineRow
from aerona.db.tables.interconnect import IncidentRow
from aerona.db.tables.lore import ChronicleRow
from aerona.db.tables.military import CaptiveCohortRow, CommanderTraitRow, OccupationRow, WarAimRow
from aerona.db.tables.polity import HouseMemberRow, OathRow, OfficeRow, PolityMemberRow, PolityProfileRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.db.tables.society import CommunitySocietyRow
from aerona.db.tables.warfare import ArmyRow, WarRow, WarSideRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.demography import CohortCondition
from aerona.domain.enums.disease import OutbreakStatus
from aerona.domain.enums.entity import SOCIETY_TYPES, EntityType
from aerona.domain.enums.military import CaptiveFate
from aerona.domain.enums.polity import OathStatus
from aerona.domain.enums.war import WarStatus
from aerona.engine.body.customs import people_of
from aerona.engine.demography.biology import record_of
from aerona.engine.faith.book import faith_tenets, patron_node
from aerona.engine.gods.queries import community_of
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.stats import stat
from aerona.engine.structures.describe import structure_lines
from aerona.prompts.contexts.mortal import HomeLine
from aerona.rules.registry import Rules


def words(value: str) -> str:
    return value.replace("_", " ")


async def home_for(session: AsyncSession, me: EntityRow, rules: Rules) -> HomeLine | None:
    home = me if me.entity_type in SOCIETY_TYPES else await community_of(session, me)
    if home is None or home.entity_type not in SOCIETY_TYPES:
        return None
    town = await session.get(SettlementProfileRow, home.id)
    society = await session.get(CommunitySocietyRow, home.id)
    people = await people_of(session, home)
    culture = await session.get(PeopleCultureRow, people.id) if people is not None else None
    biology = await session.get(PeopleBiologyRow, people.id) if people is not None else None
    customs: list[str] = await folk_lines(session, biology, culture)
    region = (await RegionAtlas.load(session)).top_region(home.id)
    sickness = await sickness_lines(session, home, region)
    social = me.social_class
    realm_id = await session.scalar(select(PolityMemberRow.polity_entity_id).where(PolityMemberRow.member_entity_id == home.id).limit(1))
    realm = await session.get(EntityRow, realm_id) if realm_id is not None else None
    profile = await session.get(PolityProfileRow, realm_id) if realm_id is not None else None
    office = await session.scalar(select(OfficeRow).where(OfficeRow.holder_entity_id == me.id).limit(1))
    house_id = await session.scalar(select(HouseMemberRow.house_entity_id).where(HouseMemberRow.mortal_entity_id == me.id).limit(1))
    house = await session.get(EntityRow, house_id) if house_id is not None else None
    oaths = [
        f"{row.kind.value.replace('_', ' ')} oath{' before a god' if row.witness_son_id else ''}"
        for row in await session.scalars(select(OathRow).where(OathRow.swearer_entity_id == me.id, OathRow.status == OathStatus.SWORN))
    ]
    wars, command, occupied, captives = await war_lines(session, rules, me, home, region)
    tenets, judgement, zeal = await faith_lines(session, home)
    lore = await lore_lines(session, me, home, realm_id, house_id)
    state = await statecraft(session, me, home, realm_id)
    wildlife, herds, beasts = await wild_lines(session, home, region)
    crops = await crop_lines(session, region)
    pets = await pet_lines(session, me)
    depth = await depth_lines(session, home, social)
    return HomeLine(
        needs=depth.needs,
        wealth=depth.wealth,
        loyalty=depth.loyalty,
        labour=depth.labour,
        wildlife=wildlife,
        herds=herds,
        crops=crops,
        pets=pets,
        beasts=beasts,
        works=await structure_lines(session, home),
        tongues=lore.tongues,
        techniques=lore.techniques,
        creed=lore.creed,
        legends=lore.legends,
        traditions=lore.traditions,
        prophecies=lore.prophecies,
        rites=lore.rites,
        treasures=lore.treasures,
        tenets=tenets,
        judgement=judgement,
        zeal=zeal,
        wars=wars,
        command=command,
        occupied_by=occupied,
        captives=captives,
        realm=f"{realm.name} ({words(profile.government.value)}, legitimacy {profile.legitimacy})" if realm is not None and profile is not None else "",
        office=words(office.kind.value) if office is not None else "",
        house=house.name if house is not None else "",
        oaths=oaths,
        treaties=state.treaties,
        claims=state.claims,
        succession=state.succession,
        laws=state.laws,
        factions=state.factions,
        community=home.name,
        tier=town.size_tier.value if town is not None else "",
        order=town.public_order if town is not None else None,
        crime=town.crime if town is not None else None,
        unrest=town.unrest if town is not None else None,
        social_class=words(social.value) if social is not None else "",
        satisfaction=society.satisfaction(social) if society is not None and social is not None else None,
        customs=customs,
        sickness=sickness,
    )


async def sickness_lines(session: AsyncSession, home: EntityRow, region: int | None) -> list[str]:
    if region is None:
        return []
    found: list[str] = []
    raging = await session.scalars(select(OutbreakRow).where(OutbreakRow.region_entity_id == region, OutbreakRow.status != OutbreakStatus.ENDED))
    endemic = await session.scalars(select(EndemicDiseaseRow).where(EndemicDiseaseRow.region_entity_id == region))
    sick = sum(await session.scalars(select(CohortRow.count).where(CohortRow.community_entity_id == home.id, CohortRow.condition == CohortCondition.SICK)))
    for disease_id, label in [*((row.disease_entity_id, "raging") for row in raging), *((row.disease_entity_id, "endemic") for row in endemic)]:
        disease = await session.get(EntityRow, disease_id)
        if disease is None:
            continue
        profile = await session.get(DiseaseProfileRow, disease_id)
        found.append(f"{disease.name} ({label}{await disease_traits(session, profile)})")
    if sick:
        found.append(f"{sick} of {home.name} lie sick")
    return found


async def disease_traits(session: AsyncSession, profile: DiseaseProfileRow | None) -> str:
    if profile is None:
        return ""
    parts = [f"spread by {profile.vector.value}", f"strikes {', '.join(words(item) for item in profile.target_functions)}"]
    if profile.incubation:
        parts.append(f"hides {several(profile.incubation, 'year', 'years')} before it shows")
    host = await session.get(EntityRow, profile.host_species_id) if profile.host_species_id is not None else None
    if host is not None:
        parts.append(f"carried by {host.name}")
    origin = await session.get(IncidentRow, profile.origin_incident_id) if profile.origin_incident_id is not None else None
    if origin is not None:
        text = await session.scalar(select(ChronicleRow.text).where(ChronicleRow.id == origin.chronicle_id)) if origin.chronicle_id is not None else None
        parts.append(f"first rose in epoch {origin.epoch}{': ' + text if text else ''}")
    return "; " + "; ".join(parts)


async def record_name(session: AsyncSession, entity_id: int | None) -> str:
    found = await session.get(EntityRow, entity_id) if entity_id is not None else None
    return found.name if found is not None else ""


async def folk_lines(session: AsyncSession, biology: PeopleBiologyRow | None, culture: PeopleCultureRow | None) -> list[str]:
    lines: list[str] = []
    if biology is not None:
        lines += [
            f"{words(biology.size_class.value)} {words(biology.body_plan.value)} folk",
            f"{words(biology.diet.value)}, living on {words(biology.staple.value)}",
            f"at home in {words(biology.acclimatised.value)} lands",
        ]
        lines += [words(trait) for trait in biology.traits]
        immune = [name for name in [await record_name(session, item) for item in biology.immunities] if name]
        if immune:
            lines.append(f"hardened against {', '.join(immune)}")
    if culture is None:
        return lines
    wins, losses = record_of(culture, culture.martial_style.value)
    lines += [
        f"fights as {words(culture.martial_style.value)} ({several(wins, 'victory', 'victories')}, {several(losses, 'defeat', 'defeats')})",
        f"{words(culture.marriage.value)}, {'marrying only their own' if culture.endogamous else 'marrying outside their people'}",
        f"inheritance by {words(culture.inheritance.value)}",
        f"{words(culture.aesthetic.value)} art",
        f"funeral rite: {words(culture.funeral_rite.value)}",
        f"urbanisation {culture.urbanisation}",
    ]
    liturgy = await record_name(session, culture.liturgical_language_id)
    trade = await record_name(session, culture.trade_language_id)
    if liturgy:
        lines.append(f"prays in {liturgy}")
    if trade:
        lines.append(f"trades in {trade}")
    if culture.slavery_lawful:
        lines.append("keeps slaves")
    return lines


async def people_facts(session: AsyncSession, entity: EntityRow) -> list[str]:
    if entity.entity_type is not EntityType.PEOPLE:
        return []
    lines = await folk_lines(session, await session.get(PeopleBiologyRow, entity.id), await session.get(PeopleCultureRow, entity.id))
    return [f"Folk and customs: {', '.join(lines)}"] if lines else []


async def war_lines(session: AsyncSession, rules: Rules, me: EntityRow, home: EntityRow, region: int | None) -> tuple[list[str], str, str, int]:
    wars: list[str] = []
    for side in await session.scalars(select(WarSideRow).where(WarSideRow.entity_id == home.id, WarSideRow.left_epoch.is_(None))):
        war = await session.get(WarRow, side.war_id)
        if war is None or war.status is WarStatus.ENDED:
            continue
        event = await session.get(EntityRow, war.event_entity_id)
        rows = await session.scalars(select(WarAimRow).where(WarAimRow.war_id == war.id, WarAimRow.side_entity_id == home.id))
        aims = [words(row.kind.value) for row in rows]
        justified = "" if war.justified else ", unjustified"
        name = event.name if event is not None else "a war"
        line = f"{name} (weariness {side.weariness}, war support {side.support}{justified}, cause {words(war.cause.value)}"
        wars.append(line + (f", aims: {', '.join(aims)})" if aims else ")"))
        wars.extend(await war_sheet(session, rules, war, home.id))
    wars.extend(await grievance_sheet(session, home.id))
    wars.extend(await intrigue_sheet(session, home.id))
    wars.extend(await fleet_sheet(session, home.id))
    army_id = await session.scalar(select(ArmyRow.entity_id).where(ArmyRow.commander_entity_id == me.id, ArmyRow.disbanded_epoch.is_(None)).limit(1))
    army = await session.get(EntityRow, army_id) if army_id is not None else None
    traits = [words(trait.value) for trait in await session.scalars(select(CommanderTraitRow.trait).where(CommanderTraitRow.mortal_entity_id == me.id))]
    command = (await army_sheet(session, rules, army.id) if army is not None else "") + (
        f" (known as {', '.join(traits)})" if army is not None and traits else ""
    )
    occupation = await session.get(OccupationRow, region) if region is not None else None
    occupier = await session.get(EntityRow, occupation.occupier_entity_id) if occupation is not None and occupation.occupier_entity_id != home.id else None
    holding = select(func.coalesce(func.sum(CaptiveCohortRow.count), 0)).where(CaptiveCohortRow.captor_entity_id == home.id)
    held = await session.scalar(holding.where(CaptiveCohortRow.fate == CaptiveFate.HELD))
    return wars, command, occupier.name if occupier is not None else "", int(held or 0)


async def faith_lines(session: AsyncSession, home: EntityRow) -> tuple[list[str], str, int | None]:
    tenets = sorted(words(tenet.value) for tenet in await faith_tenets(session, home.id))
    god_id = await patron_node(session, home.id)
    if god_id is None:
        return tenets, "", None
    worshippers = select(BondRow.source_node_id).where(BondRow.target_node_id == god_id, BondRow.kind == BondKind.WORSHIPS)
    doctrines = select(CultDoctrineRow).where(CultDoctrineRow.cult_entity_id.in_(worshippers))
    doctrine = await session.scalar(doctrines.order_by(CultDoctrineRow.cult_entity_id).limit(1))
    cult = await session.get(EntityRow, doctrine.cult_entity_id) if doctrine is not None else None
    zeal = stat(cult, "zeal") if cult is not None else None
    return tenets, words(doctrine.judgement.value) if doctrine is not None else "", zeal
