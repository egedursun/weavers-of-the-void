from aerona.domain.enums.polity import ClauseKind, PartyRole, TreatyKind
from aerona.engine.context import TickContext
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.phase import Phase
from aerona.engine.polity.book import RealmBook
from aerona.engine.polity.formation import refresh_realms
from aerona.engine.polity.governance import agenda, collect, conquest_conflict, cult_laws, enforce, law_effects, proposals, repeal_discord
from aerona.engine.polity.houses import HouseBook, arrange_marriages, gather_kin, seed_houses, tend
from aerona.engine.polity.laws import LawBook, backfill_kinds, ensure_profile
from aerona.engine.polity.oaths import lapse, pledges
from aerona.engine.polity.offices import name_heir, press_claims, purge, regency, staff, succession_line
from aerona.engine.polity.standing import administration, legitimacy, overreach, rank, realm_tier, secede, settle, stability
from aerona.engine.polity.treaties import Clause, adopt_bonds, hostilities, keep_clauses, sign
from aerona.engine.polity.wars import champions, join_wars
from aerona.engine.primitives.knowledge import KnowledgeMap


@reads(
    "army.size",
    "faction.strength",
    "law.rigidity",
    "mortal.age",
    "mortal.agility",
    "mortal.charisma",
    "mortal.intellect",
    "mortal.lifespan",
    "mortal.strength",
    "people.population",
    "people.prosperity",
    "polity.subjects",
    "settlement.population",
    "settlement.prosperity",
    "table.applied_fixups",
    "table.armies",
    "table.bonds",
    "table.community_societies",
    "table.cult_tenets",
    "table.culture_values",
    "table.entity_flags",
    "table.epoch_year_cursors",
    "table.holder_levels",
    "table.holder_techniques",
    "table.house_members",
    "table.injuries",
    "table.item_profiles",
    "table.law_jurisdictions",
    "table.law_profiles",
    "table.loans",
    "table.maimed_cohorts",
    "table.name_registry",
    "table.nodes",
    "table.oaths",
    "table.offices",
    "table.outbreaks",
    "table.people_culture",
    "table.personality_values",
    "table.polity_members",
    "table.polity_profiles",
    "table.polity_territories",
    "table.settlement_infrastructure",
    "table.settlement_profiles",
    "table.settlement_treasury",
    "table.skills",
    "table.traits",
    "table.vassalages",
    "table.war_sides",
    "table.wars",
    "table.world_maps",
)
@writes(
    "army.size",
    "cult.followers",
    "law.justice",
    "people.population",
    "people.prosperity",
    "polity.legitimacy",
    "polity.stability",
    "polity.subjects",
    "polity.territory",
    "settlement.population",
    "settlement.prosperity",
    "table.applied_fixups",
    "table.chronicle",
    "table.chronicle_entities",
    "table.community_societies",
    "table.designated_heirs",
    "table.entities",
    "table.epoch_year_cursors",
    "table.incident_participants",
    "table.incidents",
    "table.law_jurisdictions",
    "table.law_profiles",
    "table.loans",
    "table.name_registry",
    "table.oaths",
    "table.office_history",
    "table.offices",
    "table.people_culture",
    "table.polity_members",
    "table.polity_profiles",
    "table.polity_territories",
    "table.polity_treasury",
    "table.settlement_profiles",
    "table.settlement_treasury",
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
        newcomers = [member for member in realm.members if before.get(member) not in {None, realm.entity.id}]
        ctx.count("legal_conflicts", await conquest_conflict(ctx, book, realm, laws, newcomers))
        realm.profile.tier = realm_tier(book, realm)
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
        await name_heir(ctx, realm, await succession_line(ctx, realm, laws))
        ctx.count("taxed", await collect(ctx, book, realm))
        for decision in await agenda(ctx, book, realm, laws):
            ctx.count(f"decision.{decision.replace(' ', '_')}")
        for decision in await proposals(ctx, realm, laws):
            ctx.count(f"proposal.{decision.replace(' ', '_')}")
        ctx.count("repealed", await repeal_discord(ctx, realm, laws))
        await law_effects(ctx, book, realm, laws)
        ctx.count("law_unrest", await enforce(ctx, realm, laws))
        legit = await legitimacy(ctx, book, realm, laws)
        steady = await stability(ctx, book, realm, sum(legit.values()))
        settle(realm, legit, steady)
        ctx.count("succession_wars", await press_claims(ctx, book, realm))
    rank(book)
    await ctx.session.flush()


@reads(
    "mortal.age",
    "table.bonds",
    "table.claims",
    "table.culture_values",
    "table.epoch_year_cursors",
    "table.heirlooms",
    "table.house_members",
    "table.house_profiles",
    "table.injuries",
    "table.name_registry",
    "table.nodes",
    "table.offices",
    "table.polity_members",
    "table.polity_profiles",
    "table.polity_territories",
    "table.speaker_cohorts",
    "table.vassalages",
    "table.world_maps",
)
@writes(
    "house.members",
    "house.prestige",
    "house.wealth",
    "table.bonds",
    "table.chronicle",
    "table.chronicle_entities",
    "table.claims",
    "table.entities",
    "table.entity_flags",
    "table.epoch_year_cursors",
    "table.heirlooms",
    "table.house_members",
    "table.house_profiles",
    "table.incident_participants",
    "table.incidents",
    "table.name_registry",
    "table.treaty_clauses",
    "table.treaty_parties",
    "table.treaty_profiles",
)
async def house_cycles(ctx: TickContext) -> None:
    realms = await RealmBook.load(ctx.session)
    book = await HouseBook.load(ctx)
    ctx.count("houses_founded", await seed_houses(ctx, book, realms))
    ctx.count("kin_joined", await gather_kin(ctx, book))
    for key, value in (await tend(ctx, book, realms)).items():
        ctx.count(key, value)
    for first, second in await arrange_marriages(ctx, book, realms):
        ctx.count("marriages")
        first_realm, second_realm = realms.realm_of(first.location_id), realms.realm_of(second.location_id)
        if first_realm is not None and second_realm is not None and first_realm.entity.id != second_realm.entity.id:
            first_core, second_core = first_realm.profile.core_entity_id, second_realm.profile.core_entity_id
            if first_core is not None and second_core is not None:
                await sign(
                    ctx,
                    TreatyKind.MARRIAGE_PACT,
                    [(first_core, PartyRole.SIGNATORY), (second_core, PartyRole.SIGNATORY)],
                    clauses=[
                        Clause(ClauseKind.MARRIAGE, first_core, second_core, {"first_id": first.id, "second_id": second.id}),
                        Clause(ClauseKind.CALL_TO_ARMS, first_core, second_core),
                        Clause(ClauseKind.CALL_TO_ARMS, second_core, first_core),
                    ],
                    until=ctx.epoch + ctx.rules.treaties.marriage_treaty_epochs,
                )
    await ctx.session.flush()


@reads(
    "table.armies",
    "table.bonds",
    "table.community_relations",
    "table.language_intelligibility",
    "table.memories",
    "table.minds",
    "table.name_registry",
    "table.nodes",
    "table.oaths",
    "table.offices",
    "table.polity_members",
    "table.polity_profiles",
    "table.polity_territories",
    "table.skills",
    "table.speaker_cohorts",
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
    "table.bonds",
    "table.entities",
    "table.memories",
    "table.name_registry",
    "table.oaths",
    "table.treaty_breaches",
    "table.treaty_clauses",
    "table.treaty_parties",
    "table.treaty_profiles",
    "table.vassalages",
    "table.war_sides",
    "table.wars",
)
async def treaty_cycles(ctx: TickContext) -> None:
    book = await RealmBook.load(ctx.session)
    ctx.count("treaties_adopted", await adopt_bonds(ctx))
    ctx.count("treaties_breached", await hostilities(ctx))
    for key, value in (await keep_clauses(ctx, book)).items():
        ctx.count(f"treaties_{key}", value)
    ctx.count("joined_wars", await join_wars(ctx, book))
    ctx.count("champions", await champions(ctx))
    rulers = {member: realm.ruler_id for realm in book.realms.values() if realm.ruler_id is not None for member in realm.members}
    ctx.count("pledges", await pledges(ctx, rulers))
    kept, broken = await lapse(ctx)
    ctx.count("oaths_kept", kept)
    ctx.count("oaths_broken", broken)
    await ctx.session.flush()


PHASES = (
    Phase("polity_cycles", polity_cycles),
    Phase("house_cycles", house_cycles),
    Phase("treaty_cycles", treaty_cycles),
)
