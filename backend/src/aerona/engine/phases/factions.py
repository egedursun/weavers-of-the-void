from collections.abc import Mapping
from dataclasses import dataclass

from sqlalchemy import func, select

from aerona.constants.units import PERCENT
from aerona.constants.warfare import FACTION_NAME_TEMPLATE
from aerona.core.errors import ConflictError, ValidationFailedError
from aerona.core.grammar import an
from aerona.db.repositories.bonds import BondDraft, BondRepository
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.factions import FactionProfileRow
from aerona.db.tables.settlement import DistrictRow, SettlementProfileRow
from aerona.db.tables.society import CommunitySocietyRow
from aerona.db.write_guard import unheld
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.culture import Technique
from aerona.domain.enums.entity import SOCIETY_TYPES, EntityStatus, EntityType
from aerona.domain.enums.faction import FactionKind
from aerona.domain.enums.limits import PERCENT_MAX
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.settlement import DistrictKind
from aerona.domain.enums.society import SocialClass
from aerona.domain.models.entity_stats import FactionStats
from aerona.engine.context import TickContext
from aerona.engine.cycles.book import stress_factor
from aerona.engine.demography.recruitment import founding_factor, recruit
from aerona.engine.eras.effects import era_techniques
from aerona.engine.factions.agenda import dues, influence_from_members, monopolies, plan_goals, pursue, schisms
from aerona.engine.factions.book import ENGINE_OF_KIND, FactionBook, backfill_profiles, new_profile
from aerona.engine.factions.outlaws import hire, pay_companies, privateers, suppress
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.mind.drives import faction_drive
from aerona.engine.phase import Phase
from aerona.engine.phases.warfare import is_uprising
from aerona.engine.polity.book import RealmBook
from aerona.engine.polity.laws import LawBook
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import canon, living_entity, spoken_language
from aerona.engine.primitives.records import RecordSpec, create_record, retire_in
from aerona.engine.primitives.society import class_shares
from aerona.engine.primitives.stats import stat
from aerona.engine.recording.record import record as record_incident
from aerona.engine.services.war import ongoing_war_count
from aerona.rules.registry import Rules

K = FactionKind


@dataclass(frozen=True)
class FactionBlueprint:
    kind: FactionKind
    subtype: str
    suffix: str
    members: str


ENGINEERING = frozenset({Technique.STEAM_POWER, Technique.MACHINE_TOOLS, Technique.RAILWAYS})
FINANCE = frozenset({Technique.BANKING, Technique.JOINT_STOCK})

BLUEPRINTS = (
    FactionBlueprint(K.MERCHANT_GUILD, "merchant guild", "Guild", "merchants"),
    FactionBlueprint(K.CRAFT_GUILD, "craft guild", "Craft Guild", "artisans"),
    FactionBlueprint(K.PRIESTHOOD, "priests' council", "Priests' Council", "priests"),
    FactionBlueprint(K.WARRIOR_ORDER, "warrior order", "Warrior Order", "warriors"),
    FactionBlueprint(K.NOBLE_COUNCIL, "noble council", "Council of Lords", "nobles"),
    FactionBlueprint(K.PEASANT_LEAGUE, "peasant league", "League", "farmers"),
    FactionBlueprint(K.WORKERS_UNION, "workers' union", "Union", "industrial workers"),
    FactionBlueprint(K.ENGINEERS_SOCIETY, "engineers' society", "Society of Engineers", "engineers"),
    FactionBlueprint(K.FINANCIERS, "financiers' exchange", "Exchange", "financiers"),
    FactionBlueprint(K.VETERANS, "veterans' association", "Veterans", "veterans"),
    FactionBlueprint(K.REBELS, "rebel band", "Rebels", "malcontents"),
    FactionBlueprint(K.BANDITS, "bandit band", "Brigands", "outlaws"),
    FactionBlueprint(K.PIRATES, "pirate crew", "Corsairs", "sea-robbers"),
    FactionBlueprint(K.ASSASSINS, "assassins' guild", "Knives", "killers"),
    FactionBlueprint(K.SCHOLARS_ACADEMY, "academy", "Academy", "scholars"),
    FactionBlueprint(K.SECRET_SOCIETY, "secret society", "Hidden Circle", "initiates"),
    FactionBlueprint(K.MERCENARY_COMPANY, "free company", "Free Company", "sellswords"),
    FactionBlueprint(K.INTERWORLD_FEDERATION, "interworld federation", "Federation", "envoys"),
    FactionBlueprint(K.WANDERING_MARKET, "wandering market", "Caravan", "traders"),
    FactionBlueprint(K.ROUTE_RAIDERS, "route raiders", "Raiders", "raiders"),
    FactionBlueprint(K.SOCIAL_CIRCLE, "social circle", "Circle", "companions"),
    FactionBlueprint(K.CRIME_FAMILY, "crime family", "Family", "members"),
    FactionBlueprint(K.THIEVES_GUILD, "thieves' guild", "Thieves' Guild", "thieves"),
    FactionBlueprint(K.SMUGGLING_RING, "smuggling ring", "Ring", "smugglers"),
    FactionBlueprint(K.PIRATE_CONFEDERACY, "pirate confederacy", "Confederacy", "pirates"),
    FactionBlueprint(K.MAGE_ORDER, "mage order", "Mage Order", "mages"),
    FactionBlueprint(K.ESTATE, "estate", "Estate", "members"),
    FactionBlueprint(K.PARTY, "party", "Party", "partisans"),
    FactionBlueprint(K.MOVEMENT, "movement", "Movement", "followers"),
    FactionBlueprint(K.CHARTERED_COMPANY, "chartered company", "Company", "shareholders"),
    FactionBlueprint(K.HOLY_ORDER, "holy order", "Order", "devotees"),
    FactionBlueprint(K.ART_MOVEMENT, "art movement", "School", "makers"),
    FactionBlueprint(K.CLUB, "club", "Club", "players"),
    FactionBlueprint(K.LEAGUE, "league", "League", "clubs"),
)


def blueprint(kind: FactionKind) -> FactionBlueprint:
    return next(item for item in BLUEPRINTS if item.kind is kind)


def base_stats(rules: Rules, kind: FactionKind) -> tuple[int, int, int]:
    factions = rules.factions
    if kind in {K.MERCHANT_GUILD, K.CRAFT_GUILD, K.WANDERING_MARKET}:
        return factions.guild_strength, factions.guild_wealth, factions.guild_sway
    if kind in {K.PRIESTHOOD, K.SCHOLARS_ACADEMY, K.SECRET_SOCIETY, K.NOBLE_COUNCIL, K.SOCIAL_CIRCLE}:
        return factions.council_strength, factions.council_wealth, factions.council_sway
    return factions.order_strength, factions.order_wealth, factions.order_sway


async def disband_uprisings(ctx: TickContext) -> int:
    rules = ctx.rules.factions
    rng = ctx.rng("disband")
    bonds = BondRepository(ctx.session)
    disbanded = 0
    for faction in await canon(ctx.session, [EntityType.FACTION]):
        if not is_uprising(faction) or ctx.epoch - faction.birth_epoch < rules.revolt_disband_min_age:
            continue
        if await bonds.outgoing(faction.id, BondKind.ENEMY) or await bonds.incoming(faction.id, BondKind.ENEMY) or not rng.chance(rules.revolt_disband_chance):
            continue
        await retire_in(ctx, faction, "the uprising died out; the rebels dispersed and rejoined the people", close_bonds=True)
        if disbanded < rules.revolt_disband_note_cap:
            await record_incident(ctx, "faction.uprising_disbanded", roles={IncidentRole.SUBJECT: faction.id})
        disbanded += 1
    return disbanded


async def _existing(ctx: TickContext, community_id: int, kind: FactionKind) -> bool:
    statement = (
        select(EntityRow.id)
        .join(FactionProfileRow, FactionProfileRow.faction_entity_id == EntityRow.id)
        .where(EntityRow.status == EntityStatus.CANON, FactionProfileRow.kind == kind, FactionProfileRow.home_entity_id == community_id)
    )
    return await ctx.session.scalar(statement.limit(1)) is not None


async def industrial_kinds(ctx: TickContext, community: EntityRow, shares: Mapping[SocialClass, float]) -> list[FactionKind]:
    rules = ctx.rules.factions
    known = await era_techniques(ctx.session, community.id)
    wanted = (
        (K.WORKERS_UNION, Technique.FACTORY_PRODUCTION in known and shares[SocialClass.ARTISAN] >= rules.craft_min_artisan_pct),
        (K.ENGINEERS_SOCIETY, bool(known & ENGINEERING) and shares[SocialClass.PROFESSIONAL] >= rules.engineers_min_professional_pct),
        (K.FINANCIERS, bool(known & FINANCE) and shares[SocialClass.MERCHANT] >= rules.guild_min_merchant_pct),
    )
    return [kind for kind, fits in wanted if fits]


async def eligible_kinds(ctx: TickContext, community: EntityRow) -> list[FactionKind]:
    rules = ctx.rules.factions
    shares = await class_shares(ctx.session, ctx.rules, community.id)
    bonds = BondRepository(ctx.session)
    town = await ctx.session.get(SettlementProfileRow, community.id)
    society = await ctx.session.get(CommunitySocietyRow, community.id)
    kinds: list[FactionKind] = []
    trade = bool(await bonds.outgoing(community.id, BondKind.TRADES_WITH) or await bonds.incoming(community.id, BondKind.TRADES_WITH))
    if shares[SocialClass.MERCHANT] >= rules.guild_min_merchant_pct and trade and (stat(community, "prosperity") or 0) >= rules.guild_min_prosperity:
        kinds.append(K.MERCHANT_GUILD)
    if shares[SocialClass.ARTISAN] >= rules.craft_min_artisan_pct:
        kinds.append(K.CRAFT_GUILD)
    if shares[SocialClass.PRIEST] >= rules.council_min_priest_pct and await bonds.patron(community.id) is not None:
        kinds.append(K.PRIESTHOOD)
    warriors = shares[SocialClass.WARRIOR]
    at_war = await ongoing_war_count(ctx.session, community.id) > 0
    if warriors >= rules.order_min_warrior_pct or (at_war and warriors >= rules.order_at_war_min_warrior_pct):
        kinds.append(K.WARRIOR_ORDER)
    if warriors >= rules.mercenary_min_warrior_pct and not at_war:
        kinds.append(K.MERCENARY_COMPANY)
    if shares[SocialClass.NOBLE] >= rules.noble_min_pct:
        kinds.append(K.NOBLE_COUNCIL)
    if society is not None and shares[SocialClass.FARMER] >= rules.peasant_min_farmer_pct and society.satisfaction(SocialClass.FARMER) < rules.peasant_bitter:
        kinds.append(K.PEASANT_LEAGUE)
    if shares[SocialClass.SCRIBE] >= rules.academy_min_scribe_pct:
        kinds.append(K.SCHOLARS_ACADEMY)
    kinds += await industrial_kinds(ctx, community, shares)
    crime = town.crime if town is not None else 0
    if town is not None and town.unrest >= rules.secret_unrest:
        kinds.append(K.SECRET_SOCIETY)
    if crime >= rules.assassins_crime and shares[SocialClass.OUTCAST] > 0:
        kinds.append(K.ASSASSINS)
    if shares[SocialClass.OUTCAST] >= rules.bandits_outcast_pct and crime >= rules.bandits_crime:
        harbour = town is not None and await ctx.session.scalar(
            select(DistrictRow.id).where(DistrictRow.settlement_entity_id == community.id, DistrictRow.kind == DistrictKind.HARBOUR).limit(1)
        )
        kinds.append(K.PIRATES if harbour else K.BANDITS)
    kinds += await wider_kinds(ctx, community, shares, trade=trade, at_war=at_war)
    return [kind for kind in kinds if not await _existing(ctx, community.id, kind)]


async def foreign_trade(ctx: TickContext, community: EntityRow) -> bool:
    partners = select(BondRow.target_node_id).where(
        BondRow.source_node_id == community.id, BondRow.kind == BondKind.TRADES_WITH, BondRow.state == BondState.ACTIVE
    )
    other = await ctx.session.scalar(select(EntityRow.id).where(EntityRow.id.in_(partners), EntityRow.world_id != community.world_id).limit(1))
    return other is not None


async def pirate_bands(ctx: TickContext, community: EntityRow) -> int:
    found = await ctx.session.scalar(
        select(func.count())
        .select_from(FactionProfileRow)
        .join(EntityRow, EntityRow.id == FactionProfileRow.faction_entity_id)
        .where(FactionProfileRow.kind == K.PIRATES, EntityRow.world_id == community.world_id, EntityRow.status == EntityStatus.CANON)
    )
    return int(found or 0)


async def wider_kinds(ctx: TickContext, community: EntityRow, shares: Mapping[SocialClass, float], *, trade: bool, at_war: bool) -> list[FactionKind]:
    rules = ctx.rules.factions
    town = await ctx.session.get(SettlementProfileRow, community.id)
    crime = town.crime if town is not None else 0
    unrest = town.unrest if town is not None else 0
    prosperity = stat(community, "prosperity") or 0
    outcasts = shares[SocialClass.OUTCAST]
    wanted = (
        (K.REBELS, unrest >= rules.secret_unrest and at_war),
        (K.THIEVES_GUILD, crime >= rules.assassins_crime and shares[SocialClass.MERCHANT] >= rules.guild_min_merchant_pct),
        (K.SMUGGLING_RING, crime >= rules.bandits_crime and trade),
        (K.CRIME_FAMILY, crime >= rules.assassins_crime and prosperity >= rules.guild_min_prosperity),
        (K.SOCIAL_CIRCLE, shares[SocialClass.NOBLE] >= rules.noble_min_pct and prosperity >= rules.guild_min_prosperity),
        (K.WANDERING_MARKET, community.entity_type is EntityType.PEOPLE and shares[SocialClass.MERCHANT] >= rules.guild_min_merchant_pct and trade),
        (K.VETERANS, not at_war and shares[SocialClass.WARRIOR] >= rules.order_min_warrior_pct),
        (K.INTERWORLD_FEDERATION, await foreign_trade(ctx, community)),
        (K.ROUTE_RAIDERS, outcasts >= rules.bandits_outcast_pct and crime >= rules.bandits_crime and trade),
        (K.PIRATE_CONFEDERACY, await pirate_bands(ctx, community) >= 2),
    )
    return [kind for kind, fits in wanted if fits]


async def found_faction(ctx: TickContext, community: EntityRow, kind: FactionKind) -> EntityRow:
    rules = ctx.rules.factions
    plan = blueprint(kind)
    rng = ctx.rng("faction_stats")
    strength, wealth, sway = (
        clamp_int(base + rng.die(rules.faction_stat_die) - rules.faction_stat_shift, 0, PERCENT_MAX) for base in base_stats(ctx.rules, kind)
    )
    power = clamp_int(
        round_half_up(community.power_level * rules.faction_power_share_pct / PERCENT) + 1, ctx.rules.deep_life.derived_min_power, rules.faction_max_power
    )
    faction = await create_record(
        ctx,
        RecordSpec(
            entity_type=EntityType.FACTION,
            name=FACTION_NAME_TEMPLATE.format(root=community.name, suffix=plan.suffix),
            body=f"The {plan.members} of {community.name} organised among themselves.",
            stats=FactionStats(strength=strength, wealth=wealth, sway=sway),
            power=power,
            location_id=community.id if community.entity_type is EntityType.SETTLEMENT else community.location_id,
            world_id=community.world_id,
            subtype=plan.subtype,
            engine_kind=ENGINE_OF_KIND.get(kind),
        ),
    )
    faction.affiliated_entity_id = community.id
    new_profile(ctx, faction, kind)
    bonds = BondRepository(ctx.session)
    await bonds.connect(BondDraft(faction.id, community.id, BondKind.DESCENDS_FROM, ctx.epoch, "born from within"))
    language = await spoken_language(ctx.session, community.id)
    if language is not None and language.status is EntityStatus.CANON:
        await bonds.connect(BondDraft(faction.id, language.id, BondKind.SPEAKS, ctx.epoch, f"the tongue of {community.name}"))
    patron = await bonds.patron(community.id)
    if patron is not None:
        await bonds.connect(BondDraft(faction.id, patron, BondKind.WORSHIPS, ctx.epoch, f"the faith of {community.name}"))
    await record_incident(
        ctx,
        "faction.founded",
        roles={IncidentRole.PRODUCT: faction.id, IncidentRole.PLACE: community.id},
        facts={"kind": kind},
        place=community.id,
    )
    ctx.count("factions_founded")
    return faction


async def found_factions(ctx: TickContext) -> int:
    rules = ctx.rules.factions
    rng = ctx.rng("founding")
    founded = 0
    for community in unheld(await canon(ctx.session, SOCIETY_TYPES)):
        if founded >= rules.faction_cap:
            break
        if (stat(community, "population") or 0) < rules.faction_min_population:
            continue
        kinds = await eligible_kinds(ctx, community)
        discontent = await founding_factor(ctx.session, ctx.rules, community.id, kinds[0]) if kinds else 1.0
        stress = await stress_factor(ctx.session, community.id, ctx.rules.structural_demography.faction_lift)
        if not rng.chance(rules.faction_chance * await faction_drive(ctx.session, ctx.rules, community.id) * discontent * stress):
            continue
        if kinds:
            await found_faction(ctx, community, kinds[0])
            founded += 1
    return founded


@reads(
    "faction.strength",
    "faction.sway",
    "faction.wealth",
    "mortal.charisma",
    "mortal.intellect",
    "mortal.strength",
    "people.population",
    "people.prosperity",
    "settlement.population",
    "settlement.prosperity",
    "table.applied_fixups",
    "table.armies",
    "table.army_profiles",
    "table.bonds",
    "table.book_contents",
    "table.claims",
    "table.community_societies",
    "table.culture_values",
    "table.districts",
    "table.entities",
    "table.faction_actions",
    "table.faction_goals",
    "table.faction_memberships",
    "table.faction_profiles",
    "table.incident_participants",
    "table.incidents",
    "table.item_profiles",
    "table.law_jurisdictions",
    "table.law_profiles",
    "table.memories",
    "table.minds",
    "table.name_registry",
    "table.node_births",
    "table.nodes",
    "table.oaths",
    "table.offices",
    "table.polity_members",
    "table.polity_profiles",
    "table.polity_stress",
    "table.polity_territories",
    "table.pressures",
    "table.routes",
    "table.ruler_currencies",
    "table.settlement_profiles",
    "table.skills",
    "table.sons",
    "table.traits",
    "table.treaty_clauses",
    "table.treaty_parties",
    "table.treaty_profiles",
    "table.vassalages",
    "table.war_sides",
    "table.wars",
    "table.world_maps",
)
@writes(
    "faction.strength",
    "people.prosperity",
    "polity.legitimacy",
    "settlement.prosperity",
    "table.applied_fixups",
    "table.bonds",
    "table.chronicle",
    "table.chronicle_entities",
    "table.community_relations",
    "table.entities",
    "table.entity_flags",
    "table.faction_actions",
    "table.faction_goals",
    "table.faction_memberships",
    "table.faction_profiles",
    "table.incident_facts",
    "table.incident_participants",
    "table.incident_terms",
    "table.incidents",
    "table.injuries",
    "table.law_jurisdictions",
    "table.law_profiles",
    "table.memories",
    "table.mortal_profiles",
    "table.name_registry",
    "table.node_births",
    "table.oaths",
    "table.office_history",
    "table.offices",
    "table.polity_profiles",
    "table.settlement_profiles",
    "table.treaty_breaches",
    "table.treaty_clauses",
    "table.treaty_parties",
    "table.treaty_profiles",
    "table.war_sides",
)
async def factions(ctx: TickContext) -> None:
    ctx.count("uprisings_disbanded", await disband_uprisings(ctx))
    ctx.count("faction_recruits", await recruit(ctx))
    await found_factions(ctx)
    book = await FactionBook.load(ctx.session)
    ctx.count("faction_profiles", await backfill_profiles(ctx, book))
    realms = await RealmBook.load(ctx.session)
    laws = await LawBook.load(ctx.session)
    await dues(ctx, book)
    await influence_from_members(ctx, book)
    ctx.count("faction_goals", await plan_goals(ctx, book, realms))
    ctx.count("faction_acts", await pursue(ctx, book, realms, laws))
    ctx.count("faction_schisms", await schisms(ctx, book))
    ctx.count("monopolies", await monopolies(ctx, book, laws))
    ctx.count("bands_broken", await suppress(ctx, book, realms))
    ctx.count("privateer_raids", await privateers(ctx, book, realms))
    ctx.count("companies_hired", await hire(ctx, book, realms))
    for key, value in (await pay_companies(ctx, book, realms)).items():
        ctx.count(f"companies_{key}", value)
    await ctx.session.flush()


async def decree_faction(ctx: TickContext, community_id: int, kind: FactionKind) -> EntityRow:
    community = await living_entity(ctx.session, community_id)
    if community is None or community.entity_type not in SOCIETY_TYPES:
        raise ValidationFailedError("Factions are founded inside a living people or settlement.")
    if await _existing(ctx, community.id, kind):
        raise ConflictError(f"{community.name} already has {an(blueprint(kind).subtype)}.")
    return await found_faction(ctx, community, kind)


async def dissolve_faction(ctx: TickContext, faction_id: int) -> EntityRow:
    faction = await living_entity(ctx.session, faction_id)
    if faction is None or faction.entity_type is not EntityType.FACTION:
        raise ValidationFailedError("Only a living faction can be dissolved.")
    await retire_in(ctx, faction, "dissolved by decree", close_bonds=True)
    await record_incident(ctx, "faction.dissolved", roles={IncidentRole.SUBJECT: faction.id})
    return faction


PHASES = (Phase("factions", factions),)
