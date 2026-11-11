from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.urban import AMENITIES, NUISANCES, SERVICE_OF
from aerona.db.tables.discovery import ArtFormPractitionerRow, NameMeaningRow
from aerona.db.tables.disease import DiseaseProfileRow
from aerona.db.tables.economy import TradeRouteProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.evolution import SpeciesTraitRow, TraitHistoryRow
from aerona.db.tables.factions import FactionMembershipRow, FactionProfileRow
from aerona.db.tables.intrigue import BeliefRow
from aerona.db.tables.law_depth import OutlawRow, PardonRow
from aerona.db.tables.military import SpyNetworkRow
from aerona.db.tables.mind import CultureValueRow, MemoryRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.db.tables.polity import OathRow, OfficeRow, PolityMemberRow, PolityProfileRow
from aerona.db.tables.structures import StructureProfileRow
from aerona.db.tables.urban import ConvoyRow
from aerona.db.tables.warfare import WarRow, WarSideRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.economy import TradeMode
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.evolution import EvolvedTrait
from aerona.domain.enums.faction import FactionKind, FactionRank
from aerona.domain.enums.law_depth import RecruitMotive
from aerona.domain.enums.military import SpyCover, SpyOwnerKind
from aerona.domain.enums.mind import MemoryKind, SkillKind, SkillSource, TraitKind, ValueAxis
from aerona.domain.enums.polity import DecisionRule, GovernmentKind, OathKind, OathStatus, OfficeKind
from aerona.domain.enums.structure import StructureKind
from aerona.domain.enums.tongues import SoundChangeKind, SoundEnvironment
from aerona.domain.enums.urban import ConvoyStatus
from aerona.domain.enums.war import WarCause, WarSide, WarStatus
from aerona.domain.models.entity_stats import ArtFormStats, EventStats, FactionStats, LanguageStats, PolityStats, StructureStats
from aerona.engine.body.customs import people_of
from aerona.engine.context import TickContext
from aerona.engine.ecology.history import record_pathogen, record_species
from aerona.engine.economy.convoys import carry_culture, fate_of
from aerona.engine.factions.crime import CrimeTally, punish_informers, swear_silence
from aerona.engine.factions.mage_orders import OrderTally, contest_bans, rival_orders
from aerona.engine.law.outlawry import OutlawTally, hunt_outlaws, post_bounty
from aerona.engine.law.pardons import PardonTally, civil_war_ended, read_mercy
from aerona.engine.military.mole_hunts import MoleTally, purge
from aerona.engine.military.siege import warehoused
from aerona.engine.military.spy_depth import motive_for
from aerona.engine.mind.book import set_skill, traits_of
from aerona.engine.polity.laws import LawBook
from aerona.engine.primitives.language_profile import language_profile
from aerona.engine.primitives.manual import manual_context
from aerona.engine.tongues.sounds import Change, apply_change, derive, weather_names
from tests.engine.core.factories import CoreWorld, bond, entity, mortal, settlement, tuned_rules

VOWELS = frozenset("aeiou")


async def context(session: AsyncSession, **namespaces: dict[str, int]) -> TickContext:
    return await manual_context(session, "audit", rules=tuned_rules(**namespaces))


async def realm_of(session: AsyncSession, world: CoreWorld, town: EntityRow) -> EntityRow:
    polity = await entity(session, f"Crown of {town.name}", EntityType.POLITY, PolityStats(), world_id=world.world.id)
    session.add(
        PolityProfileRow(
            polity_entity_id=polity.id,
            government=next(iter(GovernmentKind)),
            decision_rule=next(iter(DecisionRule)),
            capital_entity_id=town.id,
            emblem={},
            legitimacy_parts={},
            locked=[],
        )
    )
    session.add(PolityMemberRow(polity_entity_id=polity.id, member_entity_id=town.id))
    await session.flush()
    return polity


def test_a_sound_change_applies_the_same_way_every_time_and_in_order() -> None:
    first = Change(SoundChangeKind.LENITION, "t", "d", SoundEnvironment.BETWEEN_VOWELS)
    second = Change(SoundChangeKind.LOSS, "a", "", SoundEnvironment.FINAL)
    assert derive("Matara", [first, second], VOWELS) == derive("Matara", [first, second], VOWELS) == "Madar"
    assert derive("Matara", [second, first], VOWELS) != derive("Matara", [first, second], VOWELS) or apply_change("Matara", second, VOWELS) == "Matar"


async def test_a_place_name_slowly_takes_the_sounds_of_its_tongue(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await context(session, sound_changes={"name_pct": 100})
    language = await entity(session, "Ostra", EntityType.LANGUAGE, LanguageStats(spread=20, complexity=40, sacredness=0), world_id=world.world.id)
    await language_profile(session, language, None)
    town = await settlement(session, "Atara", world, world.regions[0])
    session.add(NameMeaningRow(node_id=town.id, language_entity_id=language.id, name="Atara", gloss="the ford", morphemes=["at", "ara"], locked=[]))
    await session.flush()
    renamed = await weather_names(ctx, language.id, Change(SoundChangeKind.LENITION, "t", "d", SoundEnvironment.BETWEEN_VOWELS), VOWELS)
    meaning = await session.get(NameMeaningRow, town.id)
    assert renamed == 1 and town.name == "Adara" and meaning is not None and "once called Atara" in meaning.gloss


def test_fountains_and_parks_please_and_slaughterhouses_offend() -> None:
    assert {StructureKind.FOUNTAIN, StructureKind.PARK} <= AMENITIES and StructureKind.SLAUGHTERHOUSE in NUISANCES
    assert SERVICE_OF[StructureKind.FOUNTAIN].value == "water"


def test_convoys_between_warring_realms_are_raided_and_treaty_escorts_spare_them() -> None:
    rules = tuned_rules()
    convoy = ConvoyRow(guards=0, status=ConvoyStatus.TRAVELLING)
    profile = TradeRouteProfileRow(danger_bandits=0, danger_beasts=0, danger_sea=0, danger_weather=0, mode=TradeMode.ROAD)
    roll = rules.convoys.war_raid_pct / 2
    assert fate_of(rules, convoy, profile, roll) is ConvoyStatus.ARRIVED
    assert fate_of(rules, convoy, profile, roll, war=True) is ConvoyStatus.RAIDED
    assert fate_of(rules, convoy, profile, roll, war=True, escorted=True) is ConvoyStatus.ARRIVED


async def test_an_arriving_convoy_brings_art_and_news_of_its_home(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await context(session, convoys={"art_pct": 100})
    home = await settlement(session, "Ashby", world, world.regions[0], wealth=40, defense=30)
    away = await settlement(session, "Brook", world, world.regions[0])
    form = await entity(session, "Ring Dance", EntityType.ART_FORM, ArtFormStats(), world_id=world.world.id)
    session.add(ArtFormPractitionerRow(art_form_entity_id=form.id, practitioner_entity_id=home.id, mastery=60))
    await session.flush()
    await carry_culture(ctx, home, away)
    assert await session.get(ArtFormPractitionerRow, (form.id, away.id)) is not None
    news = await session.scalar(select(BeliefRow).where(BeliefRow.holder_node_id == away.id, BeliefRow.subject_node_id == home.id))
    assert news is not None


async def test_members_swear_the_code_and_an_informer_breaks_it(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await context(session, crime_orgs={"traitor_pct": 100})
    town = await settlement(session, "Ashby", world, world.regions[0])
    family = await entity(session, "The Lantern Family", EntityType.FACTION, FactionStats(strength=40), world_id=world.world.id, location_id=town.id)
    session.add(FactionProfileRow(faction_entity_id=family.id, kind=FactionKind.CRIME_FAMILY, home_entity_id=town.id, influence_over={}, locked=[]))
    member = await mortal(session, "Ilse", world, town.id)
    session.add(FactionMembershipRow(faction_entity_id=family.id, mortal_entity_id=member.id, rank=FactionRank.MEMBER, locked=[]))
    await session.flush()
    tally = CrimeTally()
    await swear_silence(ctx, family, tally)
    oath = await session.scalar(select(OathRow).where(OathRow.swearer_entity_id == member.id, OathRow.kind == OathKind.SILENCE))
    assert tally.sworn == 1 and oath is not None
    await punish_informers(ctx, family, tally)
    assert oath.status is OathStatus.BROKEN


async def test_an_order_defying_a_ban_is_outlawed_and_rival_orders_feud(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await context(session, magical_orders={"defiance_at": 100, "feud_pct": 100})
    town = await settlement(session, "Ashby", world, world.regions[0])
    await realm_of(session, world, town)
    orders = []
    for name, strength in (("The Quiet Order", 60), ("The Open Hand", 20)):
        order = await entity(session, name, EntityType.FACTION, FactionStats(strength=strength), world_id=world.world.id, location_id=town.id)
        profile = FactionProfileRow(
            faction_entity_id=order.id, kind=FactionKind.MAGE_ORDER, home_entity_id=town.id, reputation=50, influence_over={}, locked=[]
        )
        session.add(profile)
        orders.append((order, profile))
    await session.flush()
    tally = OrderTally()
    await rival_orders(ctx, orders, tally)
    assert tally.feuds == 1 and orders[1][1].reputation < 50
    await contest_bans(ctx, orders[0][0], orders[0][1], await LawBook.load(session), tally)
    assert not orders[0][1].outlawed


async def test_a_warehouse_stocks_a_besieged_town(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await context(session, ports={"warehouse_days": 30})
    town = await settlement(session, "Ashby", world, world.regions[0])
    store = await entity(session, "The Long Barn", EntityType.STRUCTURE, StructureStats(), world_id=world.world.id, location_id=town.id)
    session.add(StructureProfileRow(structure_entity_id=store.id, kind=StructureKind.WAREHOUSE, level=2, host_entity_id=town.id))
    await session.flush()
    assert await warehoused(ctx, town.id) == 60


async def test_a_pardon_is_read_by_the_mercy_of_its_people_and_a_civil_war_brings_an_amnesty(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await context(session)
    town = await settlement(session, "Ashby", world, world.regions[0])
    polity = await realm_of(session, world, town)
    ruler = await mortal(session, "Ilse", world, town.id)
    await bond(session, town.id, world.people.id, BondKind.DESCENDS_FROM)
    folk = await people_of(session, town) or world.people
    session.add_all([CultureValueRow(entity_id=folk.id, axis=ValueAxis.MERCY, value=90), MortalProfileRow(entity_id=ruler.id, renown=0, locked=[])])
    await session.flush()
    assert await read_mercy(ctx, ruler, polity.id) > 0
    honoured = await session.get(MortalProfileRow, ruler.id)
    assert honoured is not None and honoured.renown > 0
    event = await entity(session, "The Rising", EntityType.EVENT, EventStats(), world_id=world.world.id)
    war = WarRow(
        event_entity_id=event.id,
        world_id=world.world.id,
        status=WarStatus.ENDED,
        cause=WarCause.UPRISING,
        started_epoch=0,
        ended_epoch=ctx.epoch,
        ending="peace",
    )
    session.add(war)
    await session.flush()
    session.add(WarSideRow(war_id=war.id, entity_id=polity.id, side=WarSide.DEFENDER, joined_epoch=0))
    await session.flush()
    assert await civil_war_ended(ctx, polity.id, -1)
    session.add(PardonRow(granter_entity_id=ruler.id, amnesty=True, corrupt=False, epoch=ctx.epoch))
    await session.flush()
    assert not await civil_war_ended(ctx, polity.id, ctx.epoch)
    assert PardonTally().amnesties == 0


async def test_a_private_bounty_is_paid_by_its_poster_to_the_hunter(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await context(session, outlaws={"hunt_pct": 100, "hunter_skill": 1})
    town = await settlement(session, "Ashby", world, world.regions[0])
    polity = await realm_of(session, world, town)
    outlaw = await mortal(session, "Ilse", world, town.id)
    poster = await mortal(session, "Pell", world, town.id)
    hunter = await mortal(session, "Oren", world, town.id)
    session.add_all([MortalProfileRow(entity_id=poster.id, wealth=50, locked=[]), MortalProfileRow(entity_id=hunter.id, wealth=0, locked=[])])
    row = OutlawRow(mortal_entity_id=outlaw.id, polity_entity_id=polity.id, bounty=0, renown=0, declared_epoch=0, locked=[])
    session.add(row)
    await session.flush()
    await set_skill(session, hunter.id, SkillKind.TRACKING, 80, epoch=0, source=SkillSource.PLAYER)
    rate = ctx.rules.taxation.wealth_per_treasury
    assert await post_bounty(ctx, row, poster, 10 * rate) and row.private_bounty == 10 * rate
    await hunt_outlaws(ctx, OutlawTally())
    paid = await session.get(MortalProfileRow, hunter.id)
    assert paid is not None and paid.wealth == 10


async def test_one_wronged_by_their_lord_is_recruited_by_grievance(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await context(session)
    town = await settlement(session, "Ashby", world, world.regions[0])
    polity = await realm_of(session, world, town)
    lord = await mortal(session, "Ilse", world, town.id)
    wronged = await mortal(session, "Oren", world, town.id)
    session.add(OfficeRow(polity_entity_id=polity.id, kind=OfficeKind.RULER, holder_entity_id=lord.id))
    session.add(MemoryRow(holder_node_id=wronged.id, subject_node_id=lord.id, kind=MemoryKind.BETRAYED_ME, magnitude=-30, decay_pct=0, epoch=0))
    network = SpyNetworkRow(
        owner_entity_id=polity.id, owner_kind=SpyOwnerKind.POLITY, target_entity_id=town.id, cover=SpyCover.ENVOY, agent_ids=[], since_epoch=0, locked=[]
    )
    session.add(network)
    await session.flush()
    assert await motive_for(ctx, network, wronged) is RecruitMotive.EGO


async def test_a_spymaster_who_purges_the_innocent_grows_paranoid(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await context(session, mole_hunts={"paranoia_pct": 100})
    town = await settlement(session, "Ashby", world, world.regions[0])
    polity = await realm_of(session, world, town)
    spymaster = await mortal(session, "Ilse", world, town.id)
    official = await mortal(session, "Oren", world, town.id)
    office = OfficeRow(polity_entity_id=polity.id, kind=OfficeKind.TREASURER, holder_entity_id=official.id)
    session.add(office)
    await session.flush()
    await purge(ctx, polity.id, spymaster.id, office, official)
    assert TraitKind.PARANOID in await traits_of(session, spymaster.id) and MoleTally().purged == 0


async def test_species_and_sicknesses_keep_a_record_of_their_traits(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await context(session)
    rows = [
        SpeciesTraitRow(species_entity_id=world.species.id, region_entity_id=region.id, trait=EvolvedTrait.SPEED, mean=mean, variance=10, locked=[])
        for region, mean in zip(world.regions[:2], (40, 60), strict=True)
    ]
    assert await record_species(ctx, rows) == 1
    point = await session.get(TraitHistoryRow, (world.species.id, EvolvedTrait.SPEED.value, ctx.epoch))
    assert point is not None and point.value == 50
    sickness = await session.scalar(select(DiseaseProfileRow).limit(1))
    if sickness is not None:
        await record_pathogen(ctx, sickness)
        assert await session.get(TraitHistoryRow, (sickness.disease_entity_id, "virulence", ctx.epoch)) is not None
