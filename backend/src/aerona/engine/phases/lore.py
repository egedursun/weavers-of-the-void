from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.culture import LanguageStandingRow, LegendProfileRow, SpeakerCohortRow, TraditionParticipationRow
from aerona.db.tables.demography import PeopleCultureRow
from aerona.db.tables.entities import EntityRow, LanguageProfileRow
from aerona.db.tables.polity import PolityProfileRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.db.tables.society import CommunitySocietyRow
from aerona.domain.enums.body import HarmCause
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.chronicle import WritingSystem
from aerona.domain.enums.culture import CurseKind, ItemDeed, ProphecyState, SpeakerKind, TraditionKind
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.mind import ValueAxis, ValueHolder
from aerona.domain.enums.polity import LawKind
from aerona.engine.body.hits import Harm
from aerona.engine.context import TickContext
from aerona.engine.cosmos.sanity import shift_sanity
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.lifecycle.wounds import apply_hits
from aerona.engine.lore import art, ideology, items, legends, prophecy, research, rites, traditions
from aerona.engine.lore.language import SACRED_STAT, learn_second, prestige_parts, speakers, standing_of, tongues_of
from aerona.engine.mind.book import stored_values, write_values
from aerona.engine.notes import note
from aerona.engine.phase import Phase
from aerona.engine.polity.book import RealmBook
from aerona.engine.polity.laws import LawBook
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import active_bonds, canon, close, living_entity, spoken_language
from aerona.engine.primitives.stats import shift_stat, stat

K = TraditionKind
DEFIED_BY = {
    K.FUNERAL_RITE: LawKind.BURIAL_LAW,
    K.MARRIAGE_RITE: LawKind.MARRIAGE_LAW,
    K.FESTIVAL: LawKind.SUMPTUARY,
    K.OFFERING: LawKind.WORSHIP_BAN,
    K.PILGRIMAGE: LawKind.WORSHIP_BAN,
    K.ANCESTOR_FEAST: LawKind.WORSHIP_BAN,
    K.DUEL_CUSTOM: LawKind.PENAL_CODE,
    K.SCAR_RITE: LawKind.PENAL_CODE,
    K.HOSPITALITY_LAW: LawKind.FOREIGNER_RIGHTS,
}
HARD_SCRIPTS = frozenset({WritingSystem.PICTOGRAPHIC, WritingSystem.KNOT, WritingSystem.NOTCH})
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
            pull = ruling_prestige - (await prestige_of(ctx, own)) * table.conquered_pct / PERCENT
            gain = round_half_up(table.second_language_gain * max(0.0, pull) / PERCENT)
            if gain > 0:
                await learn_second(ctx, member, ruling.id, gain)
                learned += 1
    return learned


async def cohort(ctx: TickContext, community_id: int, language_id: int, kind: SpeakerKind, share: int) -> None:
    row = await ctx.session.get(SpeakerCohortRow, (community_id, language_id, kind))
    if row is None:
        row = SpeakerCohortRow(community_entity_id=community_id, language_entity_id=language_id, kind=kind, share=0, since_epoch=ctx.epoch)
        ctx.session.add(row)
    row.share = clamp_int(share, 0, PERCENT)


async def cohorts(ctx: TickContext) -> int:
    touched = 0
    speech = await ctx.session.execute(
        select(BondRow.source_node_id, BondRow.target_node_id).where(BondRow.kind == BondKind.SPEAKS, BondRow.state == BondState.ACTIVE)
    )
    for community_id, language_id in speech.all():
        seconds = await ctx.session.scalars(
            select(SpeakerCohortRow.share).where(SpeakerCohortRow.community_entity_id == community_id, SpeakerCohortRow.kind == SpeakerKind.SECOND)
        )
        await cohort(ctx, community_id, language_id, SpeakerKind.NATIVE, PERCENT - max([0, *seconds]) // 2)
        touched += 1
    for culture in list(await ctx.session.scalars(select(PeopleCultureRow).where(PeopleCultureRow.liturgical_language_id.is_not(None)))):
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


@reads("language.sacredness", "table.bonds", "table.language_standings", "table.speaker_cohorts", "table.people_culture", "table.community_society")
@writes("table.language_standings", "table.speaker_cohorts", "table.community_society", "table.settlement_profiles")
async def language_cycles(ctx: TickContext) -> None:
    liturgical = set(await ctx.session.scalars(select(PeopleCultureRow.liturgical_language_id).where(PeopleCultureRow.liturgical_language_id.is_not(None))))
    standings = [
        await stand(ctx, language, {int(item) for item in liturgical if item is not None}) for language in await canon(ctx.session, [EntityType.LANGUAGE])
    ]
    franca = max((row for row in standings if row.lingua_franca), key=lambda row: (row.prestige, -row.language_entity_id), default=None)
    if franca is not None:
        ctx.count("lingua_franca_learners", await trade_tongue(ctx, franca.language_entity_id))
    ctx.count("conquered_learners", await conquered_tongues(ctx))
    ctx.count("tongue_cohorts", await cohorts(ctx))
    pleased, strained = await scribes(ctx)
    ctx.count("scribes_pleased", pleased)
    ctx.count("alphabet_strain", strained)


async def confirmed(ctx: TickContext, legend: EntityRow, row: LegendProfileRow) -> bool:
    words = next((found for found, archetype in legends.WORD_ARCHETYPES if archetype is row.archetype), ())
    if not words or legend.location_id is None:
        return False
    events = await ctx.session.scalars(
        select(EntityRow.name).where(EntityRow.entity_type == EntityType.EVENT, EntityRow.birth_epoch == ctx.epoch, EntityRow.location_id == legend.location_id)
    )
    return any(word in name.lower() for name in events for word in words)


@reads("legend.spread", "table.bonds", "table.legend_profiles", "table.people_culture", "table.value_profiles", "table.claims", "table.house_profiles")
@writes("table.legend_profiles", "table.value_profiles", "table.claims", "table.house_profiles")
async def legend_cycles(ctx: TickContext) -> None:
    table = ctx.rules.belief
    for legend in await canon(ctx.session, [EntityType.LEGEND]):
        row = await legends.profile_of(ctx, legend)
        if await legends.tell(ctx, legend, row):
            ctx.count("legends_drifted")
            await note(
                ctx, f"In the retelling, {legend.name} became a tale of {row.archetype.value.replace('_', ' ')}.", key="lore.legend_drift", ids=[legend.id]
            )
        if "credence" not in row.locked and await confirmed(ctx, legend, row):
            row.credence = clamp_int(row.credence + table.confirmation, 0, PERCENT)
            ctx.count("legends_confirmed")
        ctx.count("legend_morals", await legends.press_morals(ctx, row))
        outcome = await legends.consequences(ctx, row)
        if outcome:
            ctx.count("legend_consequences")
            await note(ctx, f"Because {legend.name} is believed, {outcome}.", key="lore.legend_consequence", ids=[legend.id])


async def defied(ctx: TickContext, laws: LawBook, kind: TraditionKind, community: EntityRow) -> bool:
    law = DEFIED_BY.get(kind)
    if law is None or laws.in_force(community.id, law) is None:
        return False
    town = await ctx.session.get(SettlementProfileRow, community.id)
    if town is None or "unrest" in town.locked:
        return False
    town.unrest = clamp_int(town.unrest + ctx.rules.traditions.conflict_unrest, 0, PERCENT)
    return True


@reads("table.traditions", "table.tradition_participation", "table.bonds", "table.laws", "table.value_profiles", "table.community_stocks")
@writes("table.tradition_participation", "table.value_profiles", "table.community_stocks", "table.settlement_profiles", "table.region_environment")
async def tradition_cycles(ctx: TickContext) -> None:
    table = ctx.rules.traditions
    atlas = await RegionAtlas.load(ctx.session)
    laws = await LawBook.load(ctx.session)
    held = 0
    for tradition in await canon(ctx.session, [EntityType.TRADITION]):
        kind = (await traditions.profile_of(ctx, tradition)).kind
        for community in await traditions.celebrants(ctx, tradition.id):
            if held >= table.cap:
                await traditions.participate(ctx, tradition, community)
                continue
            done = await traditions.celebrate(ctx, tradition, community, atlas)
            held += 1
            ctx.count(f"tradition_{done or 'none'}")
            if await defied(ctx, laws, kind, community):
                ctx.count("tradition_defiance")
    fresh = await ctx.session.scalars(
        select(EntityRow).where(EntityRow.entity_type == EntityType.EVENT, EntityRow.birth_epoch == ctx.epoch).order_by(EntityRow.id)
    )
    for event in list(fresh):
        founded = await traditions.commemorate(ctx, event)
        if founded is not None:
            ctx.count("commemorations")
            await note(ctx, f"{founded.name} began, so that {event.name} is not forgotten.", key="lore.commemoration", ids=[founded.id, event.id])
    skipped = await ctx.session.scalars(select(TraditionParticipationRow).where(TraditionParticipationRow.skipped > 0))
    ctx.count("traditions_skipped", len(list(skipped)))


@reads("table.knowledge_holders", "table.holder_levels", "table.holder_techniques", "table.bonds", "table.people_culture")
@writes("table.holder_levels", "table.holder_techniques", "table.bonds", "table.book_contents")
async def research_cycles(ctx: TickContext) -> None:
    ctx.count("holders_seeded", await research.ensure_holders(ctx))
    for key, value in (await research.practise(ctx)).items():
        ctx.count(f"research_{key}", value)
    ctx.count("techniques_adopted", await research.adopt_techniques(ctx))
    ctx.count("techniques_diffused", await research.diffuse_techniques(ctx))
    ctx.count("books_filled", await research.fill_books(ctx))


@reads("ideology.adherents", "ideology.appeal", "table.ideology_profiles", "table.ideology_adherents", "table.community_society", "table.polity_profiles")
@writes("ideology.adherents", "table.ideology_profiles", "table.ideology_adherents", "table.value_profiles", "table.polity_profiles", "table.wars")
async def ideology_cycles(ctx: TickContext) -> None:
    table = ctx.rules.ideologies
    founded = await ideology.emerge(ctx)
    if founded is not None:
        ctx.count("creeds_founded")
        await note(ctx, f"A new creed was taught: {founded.name}.", key="lore.creed_founded", ids=[founded.id])
    events = 0
    for creed, profile in await ideology.living_creeds(ctx):
        ctx.count("creed_spread", await ideology.spread(ctx, creed, profile))
        ctx.count("creed_pressed", await ideology.press(ctx, creed, profile))
        ctx.count("creed_adopted", await ideology.adopt(ctx, creed))
        if events >= table.cap:
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
            await note(ctx, f"In the name of {creed.name}, {outcome}.", key="lore.revolution", ids=[creed.id])


@reads("rite.power", "table.rite_profiles", "table.rite_effects", "table.castings", "table.entity_flags", "table.laws")
@writes("rite.castings", "table.rite_profiles", "table.castings", "table.item_enchantments", "table.entities")
async def rite_cycles(ctx: TickContext) -> None:
    realms = await RealmBook.load(ctx.session)
    ctx.count("cult_rites", await rites.cult_rites(ctx, realms))
    ctx.count("enchantments", await rites.enchantments(ctx))
    ctx.count("rites_branded", await rites.heresies(ctx))


@reads("prophecy.certainty", "table.prophecy_conditions", "table.bonds", "table.offices", "table.house_members", "table.wars", "table.sky_events")
@writes("prophecy.certainty", "table.prophecy_conditions", "table.claims", "table.entities", "table.relations")
async def prophecy_cycles(ctx: TickContext) -> None:
    for seen in await canon(ctx.session, [EntityType.PROPHECY]):
        state, pressed = await prophecy.resolve(ctx, seen)
        if state is ProphecyState.FULFILLED:
            ctx.count("prophecies_fulfilled")
            await note(ctx, f"{seen.name} came true.", key="lore.prophecy_fulfilled", ids=[seen.id])
        elif pressed:
            ctx.count("prophecies_pressing")
            await note(ctx, f"Under the weight of {seen.name}, {pressed}.", key="lore.prophecy_pressure", ids=[seen.id])


async def afflict(ctx: TickContext, item: EntityRow) -> str | None:
    row = await items.profile_of(ctx, item)
    if row.curse is CurseKind.NONE:
        return None
    owner_id = await items.owner_of(ctx, item.id)
    bearer = await living_entity(ctx.session, owner_id)
    if bearer is None:
        return None
    table = ctx.rules.item_curses
    strength = stat(item, "curse") or PERCENT // 2
    mortal = bearer if bearer.entity_type is EntityType.MORTAL else None
    if row.curse is CurseKind.WASTING and mortal is not None:
        harm = Harm(
            damage=strength * table.wasting_pct / PERCENT,
            cause=HarmCause.CURSE,
            death_cause=f"wasted away under the curse of {item.name}",
            source_node_id=item.id,
        )
        await apply_hits(ctx, mortal, harm)
    elif row.curse is CurseKind.MADNESS and mortal is not None:
        shift_sanity(ctx.rules, mortal, -strength * table.madness_pct / PERCENT)
    elif row.curse is CurseKind.BLOODTHIRST:
        holder = ValueHolder.PERSONAL if mortal is not None else ValueHolder.CULTURE
        values = await stored_values(ctx.session, holder, bearer.id)
        values[ValueAxis.MARTIAL] = values.get(ValueAxis.MARTIAL, 0) + round_half_up(strength * table.bloodthirst_pct / PERCENT)
        values[ValueAxis.MERCY] = values.get(ValueAxis.MERCY, 0) - round_half_up(strength * table.bloodthirst_pct / PERCENT)
        await write_values(ctx.session, holder, bearer.id, values)
    elif row.curse is CurseKind.MISFORTUNE:
        home = await living_entity(ctx.session, bearer.location_id) if mortal is not None else bearer
        if home is not None and stat(home, "prosperity") is not None:
            shift_stat(home, "prosperity", -round_half_up(strength * table.misfortune_pct / PERCENT))
    elif row.curse is CurseKind.BETRAYAL and ctx.rng(f"curse.betray.{item.id}.{ctx.epoch}").chance(strength * table.betrayal_pct / PERCENT):
        for bond in await active_bonds(ctx.session, [BondKind.OWNS], sources=[bearer.id], targets=[item.id]):
            await close(ctx.session, bond, ctx.epoch, "the cursed thing slipped away")
        items.record(ctx, item.id, ItemDeed.LOST, bearer.id, f"slipped from the hand of {bearer.name}")
    else:
        return None
    return row.curse.value


@reads("table.item_profiles", "table.item_history", "table.relics", "table.region_environment", "table.conditions")
@writes("table.item_profiles", "table.item_history", "table.relics", "table.conditions", "cult.zeal", "table.memories")
async def item_cycles(ctx: TickContext) -> None:
    atlas = await RegionAtlas.load(ctx.session)
    for item in await items.living_items(ctx):
        for key, value in (await items.item_year(ctx, atlas, item)).items():
            ctx.count(f"items_{key}", value)
        cursed = await afflict(ctx, item)
        if cursed:
            ctx.count(f"curse_{cursed}")
    for key, value in (await items.relic_year(ctx, atlas)).items():
        ctx.count(f"relics_{key}", value)


@reads("artwork.renown", "artwork.influence", "table.artwork_profiles", "table.polity_profiles", "table.offices")
@writes("table.artwork_profiles", "table.value_profiles", "table.polity_profiles", "table.entities")
async def artwork_cycles(ctx: TickContext) -> None:
    for work in await art.living_artworks(ctx):
        for key, value in (await art.art_year(ctx, work)).items():
            ctx.count(f"art_{key}", value)
    for realm in list(await ctx.session.scalars(select(PolityProfileRow).order_by(PolityProfileRow.polity_entity_id))):
        raised = await art.commission(ctx, realm)
        if raised is not None:
            ctx.count("propaganda_works")
            await note(ctx, f"{raised.name} was raised to praise the ruler.", key="lore.propaganda", ids=[raised.id, realm.polity_entity_id])


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
