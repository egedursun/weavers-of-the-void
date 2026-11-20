from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.core.grammar import spoken as spoken_word
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.culture import (
    IdeologyAdherentRow,
    IdeologyTenetRow,
    LanguageStandingRow,
    SpeakerCohortRow,
    TraditionParticipationRow,
    TraditionProfileRow,
)
from aerona.db.tables.demography import PeopleCultureRow
from aerona.db.tables.entities import EntityRow, LanguageProfileRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.db.tables.society import CommunitySocietyRow
from aerona.db.write_guard import held as frozen
from aerona.db.write_guard import unheld
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.chronicle import WritingSystem
from aerona.domain.enums.culture import IdeologyTenet, ProphecyState, RiteStage, SpeakerKind, TraditionFunction
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.polity import LawKind
from aerona.engine.context import TickContext
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.lore import (
    art_forms,
    blueprints,
    dangers,
    eras,
    great_people,
    ideology,
    legends,
    names,
    obsolescence,
    printing,
    prophecy,
    research,
    research_depth,
    reverse,
    rites,
    smuggling,
    theories,
    traditions,
)
from aerona.engine.lore.backfill import backfill_typed_kinds
from aerona.engine.lore.calendar_rites import RiteCalendar, found_sleep_customs
from aerona.engine.lore.creed_change import keep_constitutions, schisms, syntheses
from aerona.engine.lore.language import SACRED_STAT, derive_registers, learn_second, prestige_parts, remeasure, speakers, standing_of, tongues_of
from aerona.engine.lore.prophecy_tales import keep_prophecy_tales
from aerona.engine.phase import Phase
from aerona.engine.phases.made_things import artwork_cycles, item_cycles
from aerona.engine.polity.book import RealmBook
from aerona.engine.polity.laws import LawBook
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.numbers import clamp_int, round_half_up, scaled_cap
from aerona.engine.primitives.queries import canon, spoken_language
from aerona.engine.primitives.stats import stat
from aerona.engine.recording.record import record

K = TraditionFunction
STAGE_DEFIED_BY = {RiteStage.DEATH: LawKind.BURIAL_LAW, RiteStage.UNION: LawKind.MARRIAGE_LAW}
DEFIED_BY = {
    K.FESTIVAL: LawKind.SUMPTUARY,
    K.OFFERING: LawKind.WORSHIP_BAN,
    K.PILGRIMAGE: LawKind.WORSHIP_BAN,
    K.ANCESTRAL_RITE: LawKind.WORSHIP_BAN,
    K.DUEL_CUSTOM: LawKind.PENAL_CODE,
    K.BODY_MARKING: LawKind.PENAL_CODE,
    K.HOSPITALITY: LawKind.FOREIGNER_RIGHTS,
}
HARD_SCRIPTS = frozenset({WritingSystem.PICTOGRAPHIC, WritingSystem.LOGOGRAPHIC, WritingSystem.KNOT, WritingSystem.NOTCH})
SCRIBE_FLOOR = 30


async def schooled(ctx: TickContext, language_id: int) -> bool:
    for community in await speakers(ctx.session, language_id):
        if await research.institutions(ctx.session, community):
            return True
    return False


async def stand(ctx: TickContext, language: EntityRow, liturgical: set[int]) -> LanguageStandingRow:
    table = ctx.rules.prestige
    row = await standing_of(ctx.session, language, ctx.epoch)
    parts = await prestige_parts(ctx, language)
    holy = language.id in liturgical or (stat(language, "sacredness") or 0) >= SACRED_STAT
    if holy:
        parts["its holiness"] = table.sacred
    target = clamp_int(sum(parts.values()), 0, PERCENT)
    if "prestige" not in row.locked:
        row.prestige = clamp_int(row.prestige + max(-table.drift, min(table.drift, target - row.prestige)), 0, PERCENT)
    row.prestige_parts = parts
    if "liturgical" not in row.locked:
        row.liturgical = holy
    if "standardisation" not in row.locked and await schooled(ctx, language.id):
        row.standardisation = clamp_int(row.standardisation + table.standardisation_gain, 0, PERCENT)
    if "lingua_franca" not in row.locked:
        row.lingua_franca = row.prestige >= table.lingua_franca
    row.updated_epoch = ctx.epoch
    return row


async def trade_tongue(ctx: TickContext, franca: int) -> int:
    learned = 0
    roads = await ctx.session.scalars(select(BondRow).where(BondRow.kind == BondKind.TRADES_WITH, BondRow.state == BondState.ACTIVE).order_by(BondRow.id))
    for road in roads:
        for community in (road.source_node_id, road.target_node_id):
            if franca not in await tongues_of(ctx.session, community):
                await learn_second(ctx, community, franca, ctx.rules.prestige.second_language_gain)
                learned += 1
    return learned


async def prestige_of(ctx: TickContext, language: EntityRow | None) -> int:
    row = await ctx.session.get(LanguageStandingRow, language.id) if language is not None else None
    return row.prestige if row is not None else 0


async def conquered_tongues(ctx: TickContext) -> int:
    table = ctx.rules.prestige
    learned = 0
    for realm in (await RealmBook.load(ctx.session)).realms.values():
        seat = realm.profile.capital_entity_id or realm.profile.core_entity_id
        ruling = await spoken_language(ctx.session, seat) if seat is not None else None
        if ruling is None:
            continue
        ruling_prestige = await prestige_of(ctx, ruling)
        for member in realm.members:
            own = await spoken_language(ctx.session, member)
            if own is None or own.id == ruling.id:
                continue
            weight = (await prestige_of(ctx, own)) * table.conquered_pct / PERCENT
            gain = round_half_up(table.second_language_gain * max(0.0, ruling_prestige - weight) / PERCENT)
            if gain > 0:
                await learn_second(ctx, member, ruling.id, gain)
                learned += 1
            back = round_half_up(table.second_language_gain * max(0.0, weight - ruling_prestige) / PERCENT)
            if back > 0 and seat is not None:
                await learn_second(ctx, seat, own.id, back)
                ctx.count("conquerors_converted")
                learned += 1
    return learned


async def courts_and_liturgies(ctx: TickContext) -> tuple[dict[int, int | None], dict[int, int | None]]:
    courts: dict[int, int | None] = {}
    for realm in (await RealmBook.load(ctx.session)).realms.values():
        seat = realm.profile.capital_entity_id or realm.profile.core_entity_id
        tongue = await spoken_language(ctx.session, seat) if seat is not None else None
        courts[realm.profile.polity_entity_id] = tongue.id if tongue is not None else None
    liturgies: dict[int, int | None] = {}
    for culture in list(await ctx.session.scalars(select(PeopleCultureRow).where(PeopleCultureRow.liturgical_language_id.is_not(None)))):
        liturgies[culture.people_entity_id] = culture.liturgical_language_id
    for cult in await canon(ctx.session, [EntityType.CULT]):
        home = await ctx.session.get(PeopleCultureRow, cult.location_id) if cult.location_id is not None else None
        spoken = await spoken_language(ctx.session, cult.location_id) if cult.location_id is not None else None
        liturgies[cult.id] = home.liturgical_language_id if home is not None and home.liturgical_language_id else (spoken.id if spoken else None)
    return courts, liturgies


async def cohort(ctx: TickContext, community_id: int, language_id: int, kind: SpeakerKind, share: int) -> None:
    row = await ctx.session.get(SpeakerCohortRow, (community_id, language_id, kind))
    if row is None:
        row = SpeakerCohortRow(community_entity_id=community_id, language_entity_id=language_id, kind=kind, share=0, since_epoch=ctx.epoch, locked=[])
        ctx.session.add(row)
    if "share" not in (row.locked or []):
        row.share = clamp_int(share, 0, PERCENT)


async def cohorts(ctx: TickContext) -> int:
    touched = 0
    speech = await ctx.session.execute(
        select(BondRow.source_node_id, BondRow.target_node_id).where(BondRow.kind == BondKind.SPEAKS, BondRow.state == BondState.ACTIVE)
    )
    seconds_of: dict[int, list[int]] = {}
    for holder_id, held_share in await ctx.session.execute(
        select(SpeakerCohortRow.community_entity_id, SpeakerCohortRow.share).where(SpeakerCohortRow.kind == SpeakerKind.SECOND)
    ):
        seconds_of.setdefault(holder_id, []).append(held_share)
    for community_id, language_id in speech.all():
        if frozen(community_id, language_id):
            continue
        seconds = seconds_of.get(community_id, [])
        await cohort(ctx, community_id, language_id, SpeakerKind.NATIVE, PERCENT - max([0, *seconds]) // 2)
        touched += 1
    for culture in list(await ctx.session.scalars(select(PeopleCultureRow).where(PeopleCultureRow.liturgical_language_id.is_not(None)))):
        if frozen(culture.people_entity_id, culture.liturgical_language_id):
            continue
        society = await ctx.session.get(CommunitySocietyRow, culture.people_entity_id)
        priests = round_half_up((society.share_priest + society.share_monastic) * PERCENT) if society is not None else PERCENT // 10
        await cohort(ctx, culture.people_entity_id, culture.liturgical_language_id or 0, SpeakerKind.LITURGICAL, max(1, priests))
        touched += 1
    return touched


async def scribes(ctx: TickContext) -> tuple[int, int]:
    table = ctx.rules.script
    pleased = strained = 0
    for society in list(await ctx.session.scalars(select(CommunitySocietyRow).where(CommunitySocietyRow.share_scribe > 0))):
        language = await spoken_language(ctx.session, society.entity_id)
        profile = await ctx.session.get(LanguageProfileRow, language.id) if language is not None else None
        if profile is None or profile.writing_system is None:
            continue
        if profile.writing_system in HARD_SCRIPTS:
            society.satisfaction_scribe = clamp_int(society.satisfaction_scribe + table.scribe_satisfaction, 0, PERCENT)
            pleased += 1
        elif profile.writing_system is WritingSystem.ALPHABET and society.satisfaction_scribe > SCRIBE_FLOOR:
            society.satisfaction_scribe = clamp_int(society.satisfaction_scribe - table.scribe_satisfaction, 0, PERCENT)
            town = await ctx.session.get(SettlementProfileRow, society.entity_id)
            if town is not None and "unrest" not in town.locked:
                town.unrest = clamp_int(town.unrest + table.alphabet_tension, 0, PERCENT)
            strained += 1
    return pleased, strained


@reads(
    "language.complexity",
    "language.sacredness",
    "table.artwork_profiles",
    "table.bonds",
    "table.community_relations",
    "table.community_societies",
    "table.community_society",
    "table.entities",
    "table.entity_flags",
    "table.language_grammar",
    "table.language_intelligibility",
    "table.language_profiles",
    "table.language_registers",
    "table.language_standing",
    "table.language_standings",
    "table.lexemes",
    "table.memories",
    "table.mortal_profiles",
    "table.name_exonyms",
    "table.name_meanings",
    "table.nodes",
    "table.offices",
    "table.people_culture",
    "table.personality_values",
    "table.polity_members",
    "table.polity_profiles",
    "table.polity_territories",
    "table.region_environment",
    "table.relationships",
    "table.reputations",
    "table.skills",
    "table.speaker_cohorts",
    "table.structure_profiles",
    "table.traits",
    "table.treaty_clauses",
    "table.treaty_parties",
    "table.treaty_profiles",
    "table.vassalages",
    "table.world_maps",
)
@writes(
    "table.community_relations",
    "table.community_societies",
    "table.community_society",
    "table.language_grammar",
    "table.language_intelligibility",
    "table.language_registers",
    "table.language_standing",
    "table.language_standings",
    "table.lexemes",
    "table.memories",
    "table.name_exonyms",
    "table.name_meanings",
    "table.settlement_profiles",
    "table.speaker_cohorts",
    "table.treaty_breaches",
)
async def language_cycles(ctx: TickContext) -> None:
    for key, value in (await names.names(ctx)).items():
        ctx.count(key, value)
    liturgical = set(await ctx.session.scalars(select(PeopleCultureRow.liturgical_language_id).where(PeopleCultureRow.liturgical_language_id.is_not(None))))
    standings = [
        await stand(ctx, language, {int(item) for item in liturgical if item is not None})
        for language in unheld(await canon(ctx.session, [EntityType.LANGUAGE]))
    ]
    franca = max((row for row in standings if row.lingua_franca), key=lambda row: (row.prestige, -row.language_entity_id), default=None)
    if franca is not None:
        ctx.count("lingua_franca_learners", await trade_tongue(ctx, franca.language_entity_id))
    ctx.count("conquered_learners", await conquered_tongues(ctx))
    courts, liturgies = await courts_and_liturgies(ctx)
    ctx.count("registers_shifted", await derive_registers(ctx, courts, liturgies, franca.language_entity_id if franca is not None else None))
    ctx.count("intelligibility_measured", await remeasure(ctx))
    ctx.count("tongue_cohorts", await cohorts(ctx))
    pleased, strained = await scribes(ctx)
    ctx.count("scribes_pleased", pleased)
    ctx.count("alphabet_strain", strained)


@reads(
    "legend.spread",
    "table.applied_fixups",
    "table.artwork_profiles",
    "table.bonds",
    "table.claims",
    "table.cosmos",
    "table.creator",
    "table.culture_values",
    "table.custom_kinds",
    "table.dimensional_events",
    "table.dimensions",
    "table.divine_wounds",
    "table.entities",
    "table.foreign_gods",
    "table.galactic_structures",
    "table.galaxies",
    "table.galaxy_clusters",
    "table.house_members",
    "table.house_profiles",
    "table.incident_participants",
    "table.incidents",
    "table.language_standing",
    "table.legend_profiles",
    "table.memories",
    "table.minds",
    "table.natural_law_profiles",
    "table.node_births",
    "table.nodes",
    "table.people_culture",
    "table.skills",
    "table.sons",
    "table.stars",
    "table.tradition_effects",
    "table.tradition_profiles",
    "table.value_profiles",
    "table.world_domain_hooks",
    "table.worlds",
)
@writes(
    "table.applied_fixups",
    "table.chronicle",
    "table.chronicle_entities",
    "table.claims",
    "table.culture_values",
    "table.house_profiles",
    "table.incident_facts",
    "table.incident_participants",
    "table.incidents",
    "table.legend_profiles",
    "table.memories",
    "table.tradition_effects",
    "table.tradition_profiles",
    "table.value_profiles",
)
async def legend_cycles(ctx: TickContext) -> None:
    table = ctx.rules.belief
    ctx.count("typed_kinds_backfilled", await backfill_typed_kinds(ctx))
    for legend in unheld(await canon(ctx.session, [EntityType.LEGEND])):
        row = await legends.profile_of(ctx, legend)
        if await legends.tell(ctx, legend, row):
            ctx.count("legends_drifted")
            await record(
                ctx,
                "lore.legend_drift",
                roles={IncidentRole.SUBJECT: legend.id},
                facts={"legend": str(legend.name), "spoken_word": str(spoken_word(row.archetype))},
            )
        if "credence" not in row.locked and await legends.confirmed(ctx, legend, row):
            row.credence = clamp_int(row.credence + table.confirmation, 0, PERCENT)
            ctx.count("legends_confirmed")
        ctx.count("legend_morals", await legends.press_morals(ctx, row))
        remembered = await legends.remember_legend(ctx, legend, row)
        if remembered:
            ctx.count("legend_memories", remembered)
            await record(ctx, "lore.legend_memory", roles={IncidentRole.SUBJECT: legend.id}, facts={"legend": str(legend.name)})
        outcome = await legends.consequences(ctx, row)
        if outcome:
            ctx.count("legend_consequences")
            await record(ctx, "lore.legend_consequence", roles={IncidentRole.SUBJECT: legend.id}, facts={"legend": str(legend.name), "outcome": outcome})


CREED_DEFIES = {
    IdeologyTenet.RATIONALISM: frozenset({K.OFFERING, K.PILGRIMAGE, K.ANCESTRAL_RITE, K.FAST}),
    IdeologyTenet.ANTI_GOD: frozenset({K.OFFERING, K.PILGRIMAGE, K.RITE_OF_PASSAGE}),
    IdeologyTenet.EGALITARIANISM: frozenset({K.DUEL_CUSTOM, K.BODY_MARKING}),
    IdeologyTenet.ASCETICISM: frozenset({K.FESTIVAL, K.ANCESTRAL_RITE}),
    IdeologyTenet.COSMOPOLITANISM: frozenset({K.TABOO, K.HOSPITALITY}),
    IdeologyTenet.CREATORISM: frozenset({K.ANCESTRAL_RITE, K.OFFERING}),
    IdeologyTenet.RESTRAINT: frozenset({K.MARTIAL_DISPLAY, K.DUEL_CUSTOM}),
}


def resistance(ctx: TickContext, tradition: EntityRow) -> int:
    table = ctx.rules.traditions
    rigidity = stat(tradition, "rigidity") or 0
    if rigidity < table.rigid_threshold:
        return 0
    return round_half_up(table.conflict_unrest * (1 + rigidity * table.rigidity_pct / (PERCENT * PERCENT)))


async def stir(ctx: TickContext, community: EntityRow, step: int) -> bool:
    town = await ctx.session.get(SettlementProfileRow, community.id)
    if town is None or "unrest" in town.locked or step <= 0:
        return False
    town.unrest = clamp_int(town.unrest + step, 0, PERCENT)
    return True


async def defied(ctx: TickContext, laws: LawBook, tradition: EntityRow, kind: TraditionFunction, community: EntityRow) -> bool:
    profile = await ctx.session.get(TraditionProfileRow, tradition.id)
    stage = profile.stage if profile is not None else None
    law = STAGE_DEFIED_BY.get(stage) if kind is K.RITE_OF_PASSAGE and stage is not None else DEFIED_BY.get(kind)
    if law is None or laws.in_force(community.id, law) is None:
        return False
    return await stir(ctx, community, resistance(ctx, tradition))


async def resisted_creeds(ctx: TickContext, tradition: EntityRow, kind: TraditionFunction, community: EntityRow) -> int:
    step = resistance(ctx, tradition)
    if not step:
        return 0
    held = await ctx.session.scalars(select(IdeologyAdherentRow).where(IdeologyAdherentRow.adherent_entity_id == community.id))
    struck = 0
    for adherent in list(held):
        tenets = set(await ctx.session.scalars(select(IdeologyTenetRow.tenet).where(IdeologyTenetRow.ideology_entity_id == adherent.ideology_entity_id)))
        if not any(kind in CREED_DEFIES.get(tenet, frozenset()) for tenet in tenets):
            continue
        adherent.strength = clamp_int(adherent.strength - ctx.rules.traditions.creed_resistance, 0, PERCENT)
        await stir(ctx, community, step)
        struck += 1
    return struck


async def commemorations(ctx: TickContext, atlas: RegionAtlas) -> None:
    fresh = await ctx.session.scalars(
        select(EntityRow).where(EntityRow.entity_type == EntityType.EVENT, EntityRow.birth_epoch == ctx.epoch).order_by(EntityRow.id)
    )
    for event in list(fresh):
        founded = await traditions.commemorate(ctx, event)
        if founded is not None:
            ctx.count("commemorations")
            await record(ctx, "lore.commemoration", roles={IncidentRole.SUBJECT: [founded.id, event.id]}, facts={"event": str(event.name)})
    for founded in await traditions.remember_years(ctx, atlas):
        ctx.count("commemorations_of_years")
        await record(ctx, "lore.commemoration_year", roles={IncidentRole.SUBJECT: founded.id})
    for founded in await traditions.remember_miracles(ctx):
        ctx.count("commemorations_of_miracles")
        await record(ctx, "lore.commemoration_miracle", roles={IncidentRole.SUBJECT: founded.id})


@reads(
    "event.severity",
    "people.population",
    "settlement.population",
    "table.applied_fixups",
    "table.bonds",
    "table.calendars",
    "table.chronicle",
    "table.chronicle_entities",
    "table.community_societies",
    "table.community_stocks",
    "table.creator",
    "table.culture_values",
    "table.custom_kinds",
    "table.dimensions",
    "table.entities",
    "table.foreign_gods",
    "table.galaxies",
    "table.galaxy_clusters",
    "table.goods_flows",
    "table.holder_techniques",
    "table.ideology_adherents",
    "table.ideology_tenets",
    "table.incident_participants",
    "table.incidents",
    "table.law_jurisdictions",
    "table.law_profiles",
    "table.laws",
    "table.name_registry",
    "table.node_births",
    "table.nodes",
    "table.notable_years",
    "table.people_culture",
    "table.polity_members",
    "table.region_dangers",
    "table.region_environment",
    "table.settlement_profiles",
    "table.sky_events",
    "table.sons",
    "table.spirit_profiles",
    "table.stars",
    "table.tradition_effects",
    "table.tradition_participation",
    "table.tradition_profiles",
    "table.traditions",
    "table.value_profiles",
    "table.world_maps",
    "table.world_seasons",
    "table.worlds",
    "tradition.rigidity",
)
@writes(
    "people.prosperity",
    "region.danger",
    "settlement.prosperity",
    "table.applied_fixups",
    "table.bonds",
    "table.chronicle",
    "table.chronicle_entities",
    "table.community_societies",
    "table.community_stocks",
    "table.culture_values",
    "table.entities",
    "table.goods_flows",
    "table.ideology_adherents",
    "table.incident_facts",
    "table.incident_participants",
    "table.incidents",
    "table.injuries",
    "table.legend_profiles",
    "table.name_registry",
    "table.nodes",
    "table.people_culture",
    "table.region_dangers",
    "table.region_environment",
    "table.settlement_profiles",
    "table.spirit_profiles",
    "table.tradition_effects",
    "table.tradition_participation",
    "table.tradition_profiles",
    "table.value_profiles",
)
async def tradition_cycles(ctx: TickContext) -> None:
    table = ctx.rules.traditions
    ctx.count("typed_kinds_backfilled", await backfill_typed_kinds(ctx))
    atlas = await RegionAtlas.load(ctx.session)
    laws = await LawBook.load(ctx.session)
    rite_rows = await RiteCalendar.load(ctx.session)
    celebrated: dict[int, int] = {}
    for tradition in ctx.rng("tradition_order").shuffled(unheld(await canon(ctx.session, [EntityType.TRADITION]))):
        profile = await traditions.profile_of(ctx, tradition)
        kind = profile.kind
        for community in unheld(await traditions.celebrants(ctx, tradition.id)):
            rite_rows.bind(profile, tradition, community)
            if celebrated.get(community.id, 0) >= table.cap:
                await traditions.participate(ctx, tradition, community)
                continue
            keeping = rite_rows.keeping(ctx, profile, tradition, community)
            done = await traditions.celebrate(ctx, tradition, community, atlas, keeping)
            if keeping.in_season is not None:
                ctx.count("traditions_in_season" if keeping.in_season else "traditions_off_season")
            celebrated[community.id] = celebrated.get(community.id, 0) + 1
            ctx.count(f"tradition_{done or 'none'}")
            if await defied(ctx, laws, tradition, kind, community):
                ctx.count("tradition_defiance")
            ctx.count("creeds_resisted", await resisted_creeds(ctx, tradition, kind, community))
    await commemorations(ctx, atlas)
    ctx.count("sleep_customs", await found_sleep_customs(ctx, atlas))
    skipped = await ctx.session.scalars(select(TraditionParticipationRow).where(TraditionParticipationRow.skipped > 0))
    ctx.count("traditions_skipped", len(list(skipped)))


@reads(
    "cult.followers",
    "mortal.age",
    "mortal.agility",
    "mortal.charisma",
    "mortal.endurance",
    "mortal.hp",
    "mortal.intellect",
    "mortal.lifespan",
    "mortal.strength",
    "mortal.willpower",
    "people.population",
    "people.prosperity",
    "people.wealth",
    "settlement.population",
    "settlement.prosperity",
    "settlement.wealth",
    "table.army_units",
    "table.art_form_practitioners",
    "table.art_form_profiles",
    "table.artifact_studies",
    "table.artwork_profiles",
    "table.assistive_aids",
    "table.augments",
    "table.banned_works",
    "table.blueprints",
    "table.bodies",
    "table.body_customs",
    "table.bonds",
    "table.book_contents",
    "table.captive_cohorts",
    "table.community_societies",
    "table.community_stocks",
    "table.conditions",
    "table.creator",
    "table.creature_anatomy",
    "table.crime_cases",
    "table.cult_tenets",
    "table.culture_values",
    "table.custom_kinds",
    "table.dimensions",
    "table.divine_wounds",
    "table.entities",
    "table.entity_flags",
    "table.era_deeds",
    "table.foreign_gods",
    "table.galaxies",
    "table.galaxy_clusters",
    "table.genomes",
    "table.great_people",
    "table.great_person_points",
    "table.holder_custom_techniques",
    "table.holder_levels",
    "table.holder_techniques",
    "table.incident_participants",
    "table.incidents",
    "table.incubating_ideas",
    "table.injuries",
    "table.inspirations",
    "table.institutions",
    "table.item_profiles",
    "table.knowledge_holders",
    "table.law_jurisdictions",
    "table.law_profiles",
    "table.loans",
    "table.mind_attributes",
    "table.mortal_equipment",
    "table.mortal_profiles",
    "table.name_registry",
    "table.network_nodes",
    "table.node_births",
    "table.nodes",
    "table.novelty_stocks",
    "table.occupations",
    "table.offices",
    "table.outbreaks",
    "table.people_culture",
    "table.polity_eras",
    "table.polity_members",
    "table.polity_profiles",
    "table.production_runs",
    "table.prostheses",
    "table.region_environment",
    "table.research_boosts",
    "table.research_focus",
    "table.research_progress",
    "table.sieges",
    "table.skills",
    "table.sky_events",
    "table.sons",
    "table.stars",
    "table.structure_profiles",
    "table.theory_adherents",
    "table.theory_anomalies",
    "table.theory_profiles",
    "table.treaty_clauses",
    "table.treaty_parties",
    "table.treaty_profiles",
    "table.vessel_profiles",
    "table.war_sides",
    "table.wars",
    "table.world_domain_hooks",
    "table.world_eras",
    "table.worlds",
)
@writes(
    "art_form.practitioners",
    "art_form.prestige",
    "knowledge.spread",
    "mortal.hp",
    "people.population",
    "people.prosperity",
    "people.wealth",
    "settlement.population",
    "settlement.prosperity",
    "settlement.wealth",
    "table.art_form_practitioners",
    "table.art_form_profiles",
    "table.artifact_studies",
    "table.blueprints",
    "table.bodies",
    "table.body_customs",
    "table.bonds",
    "table.book_contents",
    "table.chronicle",
    "table.chronicle_entities",
    "table.community_societies",
    "table.culture_values",
    "table.entities",
    "table.era_deeds",
    "table.great_person_points",
    "table.holder_levels",
    "table.holder_techniques",
    "table.incident_facts",
    "table.incident_participants",
    "table.incident_terms",
    "table.incidents",
    "table.injuries",
    "table.mortal_profiles",
    "table.name_registry",
    "table.node_births",
    "table.polity_eras",
    "table.polity_profiles",
    "table.research_boosts",
    "table.research_focus",
    "table.research_incidents",
    "table.research_progress",
    "table.ruler_currencies",
    "table.theory_adherents",
    "table.theory_anomalies",
    "table.theory_profiles",
    "table.world_eras",
    "theory.adherents",
    "theory.explanatory",
)
async def research_cycles(ctx: TickContext) -> None:
    ctx.count("holders_seeded", await research.ensure_holders(ctx))
    for key, value in (await research.practise(ctx)).items():
        ctx.count(f"research_{key}", value)
    for key, value in (await research_depth.research_depth(ctx)).items():
        ctx.count(f"research_{key}", value)
    ctx.count("techniques_adopted", await research_depth.adopt_techniques(ctx))
    ctx.count("techniques_diffused", await research.diffuse_techniques(ctx))
    ctx.count("societies_changed_by_techniques", await research_depth.changes_of_adoption(ctx))
    for step in (
        reverse.reverse_engineer,
        dangers.dangers,
        great_people.great_people,
        eras.eras,
        blueprints.blueprints,
        obsolescence.obsolescence,
        theories.theories,
        art_forms.art_forms,
        smuggling.smuggle,
    ):
        for key, value in (await step(ctx)).items():
            ctx.count(key, value)
    ctx.count("works_banned", await printing.censor(ctx))
    ctx.count("books_filled", await research.fill_books(ctx))
    ctx.count("books_read", await research.read_books(ctx))
    ctx.count("knowledge_spread_measured", await research.spread_of(ctx))


@reads(
    "ideology.adherents",
    "ideology.appeal",
    "item.curse",
    "item.damage",
    "item.might",
    "item.protection",
    "mortal.intellect",
    "table.banned_works",
    "table.bonds",
    "table.community_societies",
    "table.community_society",
    "table.constitutions",
    "table.creator",
    "table.cult_tenets",
    "table.culture_values",
    "table.dimensions",
    "table.entities",
    "table.foreign_gods",
    "table.galaxies",
    "table.galaxy_clusters",
    "table.holder_techniques",
    "table.ideology_adherents",
    "table.ideology_profiles",
    "table.ideology_tenets",
    "table.incident_participants",
    "table.incidents",
    "table.memories",
    "table.minds",
    "table.name_registry",
    "table.node_births",
    "table.node_materials",
    "table.nodes",
    "table.personality_values",
    "table.polity_members",
    "table.polity_profiles",
    "table.sons",
    "table.stars",
    "table.structure_profiles",
    "table.worlds",
)
@writes(
    "ideology.adherents",
    "table.bonds",
    "table.chronicle",
    "table.chronicle_entities",
    "table.constitutions",
    "table.culture_values",
    "table.entities",
    "table.ideology_adherents",
    "table.ideology_profiles",
    "table.ideology_tenets",
    "table.incident_facts",
    "table.incident_participants",
    "table.incidents",
    "table.item_history",
    "table.item_profiles",
    "table.memories",
    "table.name_registry",
    "table.node_materials",
    "table.polity_profiles",
    "table.value_profiles",
    "table.wars",
)
async def ideology_cycles(ctx: TickContext) -> None:
    table = ctx.rules.ideologies
    founded = await ideology.emerge(ctx)
    if founded is not None:
        ctx.count("creeds_founded")
        await record(ctx, "lore.creed_founded", roles={IncidentRole.SUBJECT: founded.id}, facts={"founded": str(founded.name)})
    events = 0
    creeds = ctx.rng("creed_order").shuffled(await ideology.living_creeds(ctx))
    limit = scaled_cap(table.cap, table.cap_creed_divisor, len(creeds))
    for creed, profile in creeds:
        if await ideology.write_text(ctx, creed, profile) is not None:
            ctx.count("creed_texts")
        ctx.count("creed_spread", await ideology.spread(ctx, creed, profile))
        ctx.count("creed_pressed", await ideology.press(ctx, creed, profile))
        ctx.count("creed_adopted", await ideology.adopt(ctx, creed))
        ctx.count("creed_splits", await schisms(ctx, creed))
        if events >= limit:
            continue
        persecuted = await ideology.clash_with_faith(ctx, creed)
        drained = await ideology.godless(ctx, creed)
        events += int(bool(persecuted)) + int(bool(drained))
        ctx.count("creeds_persecuted", persecuted)
        ctx.count("faith_drained", drained)
        outcome = await ideology.revolution(ctx, creed)
        if outcome:
            events += 1
            ctx.count("revolutions")
            await record(ctx, "lore.revolution", roles={IncidentRole.SUBJECT: creed.id}, facts={"creed": str(creed.name), "outcome": outcome})
    ctx.count("creed_merges", await syntheses(ctx, [creed for creed, _ in await ideology.living_creeds(ctx)]))
    ctx.count("constitutions", await keep_constitutions(ctx))


@reads(
    "rite.power",
    "table.applied_fixups",
    "table.army_profiles",
    "table.army_units",
    "table.battles",
    "table.bonds",
    "table.captive_cohorts",
    "table.castings",
    "table.culture_values",
    "table.custom_kinds",
    "table.entities",
    "table.entity_flags",
    "table.holder_techniques",
    "table.laws",
    "table.ley_lines",
    "table.nodes",
    "table.offices",
    "table.polity_members",
    "table.polity_profiles",
    "table.polity_territories",
    "table.region_pollution",
    "table.rite_effects",
    "table.rite_profiles",
    "table.skills",
    "table.sky_events",
    "table.species_ranges",
    "table.vassalages",
    "table.war_sides",
    "table.world_maps",
    "table.world_seasons",
)
@writes(
    "rite.castings",
    "table.applied_fixups",
    "table.army_units",
    "table.battles",
    "table.beast_profiles",
    "table.bonds",
    "table.captive_cohorts",
    "table.castings",
    "table.chronicle",
    "table.chronicle_entities",
    "table.entities",
    "table.entity_flags",
    "table.forced_weather",
    "table.incident_participants",
    "table.incidents",
    "table.injuries",
    "table.item_enchantments",
    "table.memories",
    "table.modifiers",
    "table.region_pollution",
    "table.rite_effects",
    "table.rite_profiles",
    "table.skills",
    "table.spirit_profiles",
)
async def rite_cycles(ctx: TickContext) -> None:
    ctx.count("rites_profiled", await rites.backfill(ctx))
    realms = await RealmBook.load(ctx.session)
    ctx.count("cult_rites", await rites.cult_rites(ctx, realms))
    ctx.count("war_mage_rites", await rites.war_mages(ctx, realms))
    ctx.count("enchantments", await rites.enchantments(ctx))
    ctx.count("rites_branded", await rites.heresies(ctx))


@reads(
    "prophecy.certainty",
    "table.bonds",
    "table.divine_wounds",
    "table.entities",
    "table.foreign_gods",
    "table.house_members",
    "table.legend_profiles",
    "table.node_births",
    "table.nodes",
    "table.offices",
    "table.polity_profiles",
    "table.prophecy_conditions",
    "table.sky_events",
    "table.sons",
    "table.wars",
    "table.world_domain_hooks",
)
@writes(
    "prophecy.certainty",
    "table.chronicle",
    "table.chronicle_entities",
    "table.claims",
    "table.entities",
    "table.incident_facts",
    "table.incident_participants",
    "table.incidents",
    "table.prophecy_conditions",
    "table.relations",
)
async def prophecy_cycles(ctx: TickContext) -> None:
    for seen in await canon(ctx.session, [EntityType.PROPHECY]):
        state, pressed = await prophecy.resolve(ctx, seen)
        if state is ProphecyState.FULFILLED:
            ctx.count("prophecies_fulfilled")
            tail = f" {pressed[0].upper()}{pressed[1:]}." if pressed else ""
            await record(ctx, "lore.prophecy_fulfilled", roles={IncidentRole.SUBJECT: seen.id}, facts={"tail": str(tail)})
        elif pressed:
            ctx.count("prophecies_pressing")
            await record(ctx, "lore.prophecy_pressure", roles={IncidentRole.SUBJECT: seen.id}, facts={"pressed": str(pressed)})
    await keep_prophecy_tales(ctx)


LANGUAGE_PHASES = (Phase("language_cycles", language_cycles),)
LEGEND_PHASES = (Phase("legend_cycles", legend_cycles),)
TRADITION_PHASES = (Phase("tradition_cycles", tradition_cycles),)
RESEARCH_PHASES = (Phase("research_cycles", research_cycles),)
IDEOLOGY_PHASES = (Phase("ideology_cycles", ideology_cycles),)
RITE_PHASES = (Phase("rite_cycles", rite_cycles),)
PROPHECY_PHASES = (Phase("prophecy_cycles", prophecy_cycles),)
ITEM_PHASES = (Phase("item_cycles", item_cycles),)
ARTWORK_PHASES = (Phase("artwork_cycles", artwork_cycles),)
PHASES = LANGUAGE_PHASES + LEGEND_PHASES + TRADITION_PHASES + RESEARCH_PHASES + IDEOLOGY_PHASES + RITE_PHASES + PROPHECY_PHASES + ITEM_PHASES + ARTWORK_PHASES
