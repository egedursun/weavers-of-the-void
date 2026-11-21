from aerona.db.write_guard import held as frozen
from aerona.domain.enums.polity import ClauseKind, PartyRole, TreatyKind
from aerona.engine.context import TickContext
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.phase import Phase
from aerona.engine.polity.accords import Clause, sign
from aerona.engine.polity.book import RealmBook
from aerona.engine.polity.formation import refresh_realms
from aerona.engine.polity.governance import agenda, collect, conquest_conflict, cult_laws, enforce, law_effects, proposals, repeal_discord
from aerona.engine.polity.houses import HouseBook, arrange_marriages, conquest_claims, dynasty_backfill, fabricate_claims, gather_kin, seed_houses, tend
from aerona.engine.polity.law_effects import realm_coinage
from aerona.engine.polity.laws import LawBook, backfill_kinds, ensure_profile
from aerona.engine.polity.oath_terms import releases
from aerona.engine.polity.oaths import lapse, pledges, vows
from aerona.engine.polity.offices import coups, name_heir, office_effects, press_claims, purge, regency, staff, succession_line
from aerona.engine.polity.pacts import outer_pacts
from aerona.engine.polity.standing import administration, legitimacy, overreach, rank, realm_tier, secede, settle, stability
from aerona.engine.polity.treaties import adopt_bonds, answer_proposals, hostilities, keep_clauses, tribute_ledger, vassal_duties
from aerona.engine.polity.wars import champions, join_wars
from aerona.engine.primitives.knowledge import KnowledgeMap


@reads(
    "army.size",
    "cult.followers",
    "faction.strength",
    "faction.sway",
    "faction.wealth",
    "law.rigidity",
    "mortal.age",
    "mortal.agility",
    "mortal.charisma",
    "mortal.importance",
    "mortal.intellect",
    "mortal.lifespan",
    "mortal.strength",
    "mortal.wisdom",
    "people.piety",
    "people.population",
    "people.prosperity",
    "polity.subjects",
    "settlement.piety",
    "settlement.population",
    "settlement.prosperity",
    "table.accounts",
    "table.applied_fixups",
    "table.armies",
    "table.army_officers",
    "table.army_profiles",
    "table.artwork_profiles",
    "table.augments",
    "table.bodies",
    "table.body_customs",
    "table.bonds",
    "table.claims",
    "table.coalition_members",
    "table.community_cohorts",
    "table.community_labour",
    "table.community_relations",
    "table.community_societies",
    "table.community_stocks",
    "table.conditions",
    "table.cosmos",
    "table.creator",
    "table.crime_cases",
    "table.cult_doctrines",
    "table.cult_tenets",
    "table.culture_ethics",
    "table.culture_honour",
    "table.culture_values",
    "table.currencies",
    "table.custom_kinds",
    "table.data_stores",
    "table.designated_heirs",
    "table.dimensional_events",
    "table.dimensions",
    "table.districts",
    "table.entities",
    "table.entity_flags",
    "table.exam_sittings",
    "table.fabrication",
    "table.faction_profiles",
    "table.feuds",
    "table.foreign_gods",
    "table.galactic_structures",
    "table.galaxies",
    "table.galaxy_clusters",
    "table.genomes",
    "table.goods",
    "table.held_identities",
    "table.holder_custom_techniques",
    "table.holder_levels",
    "table.holder_techniques",
    "table.house_members",
    "table.house_profiles",
    "table.incident_participants",
    "table.incidents",
    "table.injuries",
    "table.item_profiles",
    "table.language_intelligibility",
    "table.language_profiles",
    "table.law_jurisdictions",
    "table.law_profiles",
    "table.law_proposals",
    "table.learned_tactics",
    "table.living_line_sources",
    "table.living_lines",
    "table.living_profiles",
    "table.loans",
    "table.maimed_cohorts",
    "table.membership_categories",
    "table.memberships",
    "table.memories",
    "table.mercenary_contracts",
    "table.mind_profiles",
    "table.mind_states",
    "table.minds",
    "table.mortal_profiles",
    "table.name_registry",
    "table.natural_law_profiles",
    "table.network_nodes",
    "table.network_profiles",
    "table.node_births",
    "table.nodes",
    "table.oaths",
    "table.offices",
    "table.outbreaks",
    "table.passions",
    "table.patronage_ties",
    "table.peace_terms",
    "table.peer_members",
    "table.people_culture",
    "table.personality_values",
    "table.polity_loyalty",
    "table.polity_members",
    "table.polity_profiles",
    "table.polity_territories",
    "table.power_bases",
    "table.public_opinion",
    "table.regimes",
    "table.region_pollution",
    "table.relation_components",
    "table.relationships",
    "table.reputations",
    "table.routes",
    "table.ruler_currencies",
    "table.satires",
    "table.settlement_infrastructure",
    "table.settlement_profiles",
    "table.settlement_treasury",
    "table.skills",
    "table.sons",
    "table.speaker_cohorts",
    "table.spy_agents",
    "table.spy_networks",
    "table.stars",
    "table.structure_profiles",
    "table.title_holders",
    "table.title_profiles",
    "table.traits",
    "table.treaty_clauses",
    "table.treaty_parties",
    "table.treaty_profiles",
    "table.union_customs",
    "table.unit_designs",
    "table.vassalages",
    "table.vessel_profiles",
    "table.war_sides",
    "table.wars",
    "table.workshops",
    "table.world_maps",
    "table.worlds",
)
@writes(
    "army.size",
    "cult.followers",
    "faction.sway",
    "faction.wealth",
    "law.justice",
    "people.piety",
    "people.population",
    "people.prosperity",
    "people.wealth",
    "polity.legitimacy",
    "polity.stability",
    "polity.subjects",
    "polity.territory",
    "settlement.piety",
    "settlement.population",
    "settlement.prosperity",
    "settlement.wealth",
    "table.applied_fixups",
    "table.army_officers",
    "table.army_profiles",
    "table.battle_casualties",
    "table.battle_stacks",
    "table.body_customs",
    "table.bonds",
    "table.captive_cohorts",
    "table.captives",
    "table.chronicle",
    "table.chronicle_entities",
    "table.claims",
    "table.community_cohorts",
    "table.community_relations",
    "table.community_societies",
    "table.community_stocks",
    "table.currencies",
    "table.designated_heirs",
    "table.districts",
    "table.entities",
    "table.entity_flags",
    "table.feuds",
    "table.goods",
    "table.house_members",
    "table.house_profiles",
    "table.incident_facts",
    "table.incident_participants",
    "table.incidents",
    "table.law_jurisdictions",
    "table.law_profiles",
    "table.law_proposals",
    "table.learned_tactics",
    "table.loans",
    "table.maimed_cohorts",
    "table.memories",
    "table.mercenary_contracts",
    "table.mortal_profiles",
    "table.name_registry",
    "table.node_births",
    "table.oaths",
    "table.office_history",
    "table.offices",
    "table.peace_terms",
    "table.people_culture",
    "table.persuasions",
    "table.polity_loyalty",
    "table.polity_members",
    "table.polity_profiles",
    "table.polity_territories",
    "table.polity_treasury",
    "table.region_environment",
    "table.settlement_infrastructure",
    "table.settlement_profiles",
    "table.settlement_treasury",
    "table.sons",
    "table.spy_agents",
    "table.spy_networks",
    "table.transformations",
    "table.treaty_breaches",
    "table.vessel_profiles",
    "table.war_aims",
    "table.war_sides",
    "table.wars",
)
async def polity_cycles(ctx: TickContext) -> None:
    book = await RealmBook.load(ctx.session)
    before = dict(book.member_of)
    for key, value in (await refresh_realms(ctx, book)).items():
        ctx.count(key, value)
    knowledge = await KnowledgeMap.load(ctx.session)
    ctx.count("law_kinds_backfilled", await backfill_kinds(ctx.session, ctx.epoch))
    laws = await LawBook.load(ctx.session)
    for law in laws.laws.values():
        if law.id not in laws.profiles:
            laws.profiles[law.id] = await ensure_profile(ctx.session, law, ctx.epoch)
    laws = await LawBook.load(ctx.session)
    ctx.count("cult_laws", await cult_laws(ctx, laws))
    for realm in list(book.realms.values()):
        if frozen(realm.entity.id):
            continue
        newcomers = [member for member in realm.members if before.get(member) not in {None, realm.entity.id}]
        ctx.count("legal_conflicts", await conquest_conflict(ctx, book, realm, laws, newcomers))
        realm.profile.tier = await realm_tier(ctx, book, realm, knowledge)
        capacity, need = await administration(ctx, book, realm, knowledge)
        for member in await overreach(ctx, book, realm, capacity, need):
            await secede(ctx, book, realm, member)
            ctx.count("secessions")
        held: set[int] = set()
        regent = await regency(ctx, realm, held)
        if regent is not None:
            ctx.count(f"regency.{regent}")
        ctx.count("offices_filled", await staff(ctx, book, realm, held))
        ctx.count("purged", await purge(ctx, realm))
        for key, value in (await office_effects(ctx, book, realm)).items():
            ctx.count(f"office.{key}", value)
        ctx.count("coups", await coups(ctx, realm))
        await name_heir(ctx, realm, await succession_line(ctx, realm, laws))
        ctx.count("taxed", await collect(ctx, book, realm))
        for decision in await agenda(ctx, book, realm, laws):
            ctx.count(f"decision.{decision.replace(' ', '_')}")
        for decision in await proposals(ctx, realm, laws):
            ctx.count(f"proposal.{decision.replace(' ', '_')}")
        ctx.count("repealed", await repeal_discord(ctx, realm, laws))
        await law_effects(ctx, book, realm, laws)
        ctx.count("realm_coinage", await realm_coinage(ctx, realm))
        ctx.count("law_unrest", await enforce(ctx, realm, laws))
        legit = await legitimacy(ctx, book, realm, laws)
        steady = await stability(ctx, book, realm, sum(legit.values()))
        settle(realm, legit, steady)
        ctx.count("succession_wars", await press_claims(ctx, book, realm))
    rank(book)
    await ctx.session.flush()


@reads(
    "mortal.age",
    "mortal.lifespan",
    "mortal.strength",
    "people.prosperity",
    "settlement.prosperity",
    "table.age_set_members",
    "table.applied_fixups",
    "table.bonds",
    "table.child_standing",
    "table.claims",
    "table.creator",
    "table.culture_ethics",
    "table.culture_values",
    "table.dimensions",
    "table.entities",
    "table.entity_flags",
    "table.foreign_gods",
    "table.galaxies",
    "table.galaxy_clusters",
    "table.genomes",
    "table.heirlooms",
    "table.hero_quests",
    "table.house_members",
    "table.house_profiles",
    "table.incident_participants",
    "table.incidents",
    "table.injuries",
    "table.kin_group_members",
    "table.kin_groups",
    "table.kinship_systems",
    "table.language_registers",
    "table.law_jurisdictions",
    "table.law_profiles",
    "table.marriages",
    "table.membership_categories",
    "table.memberships",
    "table.memories",
    "table.mortal_profiles",
    "table.name_registry",
    "table.node_births",
    "table.nodes",
    "table.oaths",
    "table.offices",
    "table.people_biology",
    "table.people_culture",
    "table.people_reproduction",
    "table.polity_members",
    "table.polity_profiles",
    "table.polity_territories",
    "table.purity",
    "table.sentences",
    "table.sons",
    "table.speaker_cohorts",
    "table.stars",
    "table.traits",
    "table.union_customs",
    "table.vassalages",
    "table.wars",
    "table.world_maps",
    "table.worlds",
)
@writes(
    "house.members",
    "house.prestige",
    "house.wealth",
    "table.applied_fixups",
    "table.bonds",
    "table.chronicle",
    "table.chronicle_entities",
    "table.claims",
    "table.entities",
    "table.entity_flags",
    "table.heirlooms",
    "table.hero_quests",
    "table.house_members",
    "table.house_profiles",
    "table.incident_facts",
    "table.incident_participants",
    "table.incidents",
    "table.marriages",
    "table.memories",
    "table.mortal_profiles",
    "table.name_registry",
    "table.oaths",
    "table.sons",
    "table.treaty_breaches",
    "table.treaty_clauses",
    "table.treaty_parties",
    "table.treaty_profiles",
)
async def house_cycles(ctx: TickContext) -> None:
    realms = await RealmBook.load(ctx.session)
    book = await HouseBook.load(ctx)
    ctx.count("houses_founded", await seed_houses(ctx, book, realms))
    ctx.count("dynasty_ancestors", await dynasty_backfill(ctx, book))
    ctx.count("conquest_claims", await conquest_claims(ctx, realms))
    ctx.count("fabricated_claims", await fabricate_claims(ctx, realms))
    ctx.count("kin_joined", await gather_kin(ctx, book))
    for key, value in (await tend(ctx, book, realms)).items():
        ctx.count(key, value)
    for first, second in await arrange_marriages(ctx, book, realms):
        ctx.count("marriages")
        first_realm, second_realm = realms.realm_of(first.location_id), realms.realm_of(second.location_id)
        if first_realm is not None and second_realm is not None and first_realm.entity.id != second_realm.entity.id:
            first_core, second_core = first_realm.profile.core_entity_id, second_realm.profile.core_entity_id
            if first_core is not None and second_core is not None:
                houses = [house for house in (book.house_of.get(first.id), book.house_of.get(second.id)) if house is not None]
                await sign(
                    ctx,
                    TreatyKind.MARRIAGE_PACT,
                    [(first_core, PartyRole.SIGNATORY), (second_core, PartyRole.SIGNATORY), *((house, PartyRole.SIGNATORY) for house in dict.fromkeys(houses))],
                    clauses=[
                        Clause(ClauseKind.MARRIAGE, first_core, second_core, {"first_id": first.id, "second_id": second.id}),
                        Clause(ClauseKind.CALL_TO_ARMS, first_core, second_core),
                        Clause(ClauseKind.CALL_TO_ARMS, second_core, first_core),
                    ],
                    until=ctx.epoch + ctx.rules.treaties.marriage_treaty_epochs,
                )
    await ctx.session.flush()


@reads(
    "faction.wealth",
    "people.population",
    "people.prosperity",
    "people.wealth",
    "settlement.population",
    "settlement.prosperity",
    "settlement.wealth",
    "table.applied_fixups",
    "table.armies",
    "table.beast_profiles",
    "table.bonds",
    "table.community_relations",
    "table.community_societies",
    "table.community_stocks",
    "table.cosmos",
    "table.creator",
    "table.creator_taboos",
    "table.cult_tenets",
    "table.culture_ethics",
    "table.culture_honour",
    "table.culture_values",
    "table.deed_claims",
    "table.deeds",
    "table.dimensional_events",
    "table.dimensions",
    "table.entities",
    "table.entity_flags",
    "table.faction_memberships",
    "table.foreign_gods",
    "table.galactic_structures",
    "table.galaxies",
    "table.galaxy_clusters",
    "table.geasa",
    "table.goods_flows",
    "table.held_identities",
    "table.holder_levels",
    "table.incident_participants",
    "table.language_intelligibility",
    "table.language_profiles",
    "table.language_registers",
    "table.law_jurisdictions",
    "table.law_profiles",
    "table.marriages",
    "table.memories",
    "table.mind_profiles",
    "table.minds",
    "table.mortal_profiles",
    "table.name_registry",
    "table.natural_law_profiles",
    "table.nodes",
    "table.oaths",
    "table.offices",
    "table.personality_values",
    "table.polity_members",
    "table.polity_profiles",
    "table.polity_regard",
    "table.polity_territories",
    "table.relation_components",
    "table.relationships",
    "table.reputations",
    "table.ruler_currencies",
    "table.skills",
    "table.sons",
    "table.speaker_cohorts",
    "table.stars",
    "table.trade_route_tolls",
    "table.tradition_profiles",
    "table.traits",
    "table.treaty_clauses",
    "table.treaty_parties",
    "table.treaty_profiles",
    "table.tributes",
    "table.vassalages",
    "table.wants",
    "table.war_sides",
    "table.wars",
    "table.world_maps",
    "table.worlds",
)
@writes(
    "faction.wealth",
    "people.prosperity",
    "people.wealth",
    "settlement.prosperity",
    "settlement.wealth",
    "table.applied_fixups",
    "table.bonds",
    "table.chronicle",
    "table.chronicle_entities",
    "table.community_relations",
    "table.community_societies",
    "table.community_stocks",
    "table.deed_claims",
    "table.deeds",
    "table.entities",
    "table.entity_flags",
    "table.goods_flows",
    "table.incident_participants",
    "table.incidents",
    "table.memories",
    "table.mortal_profiles",
    "table.name_registry",
    "table.oaths",
    "table.polity_profiles",
    "table.polity_regard",
    "table.reputations",
    "table.sons",
    "table.thoughts",
    "table.traits",
    "table.treaty_breaches",
    "table.treaty_clauses",
    "table.treaty_parties",
    "table.treaty_profiles",
    "table.tributes",
    "table.vassalages",
    "table.war_sides",
    "table.wars",
)
async def treaty_cycles(ctx: TickContext) -> None:
    book = await RealmBook.load(ctx.session)
    ctx.count("treaties_adopted", await adopt_bonds(ctx))
    for key, value in (await answer_proposals(ctx)).items():
        ctx.count(f"proposals_{key}", value)
    ctx.count("treaties_breached", await hostilities(ctx))
    for key, value in (await keep_clauses(ctx, book)).items():
        ctx.count(f"treaties_{key}", value)
    for key, value in (await vassal_duties(ctx, book)).items():
        ctx.count(f"vassal_{key}", value)
    ctx.count("tributes_closed", await tribute_ledger(ctx))
    for key, value in (await outer_pacts(ctx, book)).items():
        ctx.count(f"pacts_{key}", value)
    ctx.count("joined_wars", await join_wars(ctx, book))
    ctx.count("champions", await champions(ctx))
    rulers = {member: realm.ruler_id for realm in book.realms.values() if realm.ruler_id is not None for member in realm.members}
    ctx.count("pledges", await pledges(ctx, rulers))
    ctx.count("vows", await vows(ctx))
    kept, broken = await lapse(ctx)
    ctx.count("oaths_kept", kept)
    ctx.count("oaths_broken", broken)
    ctx.count("oaths_released", await releases(ctx))
    await ctx.session.flush()


PHASES = (
    Phase("polity_cycles", polity_cycles),
    Phase("house_cycles", house_cycles),
    Phase("treaty_cycles", treaty_cycles),
)
