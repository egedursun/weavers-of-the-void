from aerona.constants.units import PERCENT
from aerona.core.grammar import an
from aerona.db.write_guard import held
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.domain import Domain
from aerona.domain.enums.economy import CommodityKind, GoodsFlow
from aerona.domain.enums.faith import TenetKind
from aerona.domain.enums.mind import MemoryKind
from aerona.engine.context import TickContext
from aerona.engine.economy.stocks import goods_of
from aerona.engine.faith.backfill import backfill_faith
from aerona.engine.faith.book import Church, FaithBook, FaithLine
from aerona.engine.faith.doctrine import ensure_doctrines, staff
from aerona.engine.faith.exorcism import possessions
from aerona.engine.faith.souls import fear_of_torment, gnaw, possess, profiles, realm_essence, reincarnate, soul_eaters, tend
from aerona.engine.faith.strata_life import stratum_turn
from aerona.engine.faith.works import canonise, devotion, holding_income, pilgrim_plague, pilgrimage, sacred_beasts, saints, spend, survey_holdings, tithe
from aerona.engine.faith.zeal import stir
from aerona.engine.faith.zealotry import drift, fanaticism, investiture, suppress
from aerona.engine.gods.progress import cap_gained_essence
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.interconnect.flows import FlowCategory, flowing
from aerona.engine.mind.memories import remember
from aerona.engine.notes import note
from aerona.engine.phase import Phase
from aerona.engine.polity.laws import LawBook
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.knowledge import KnowledgeMap
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.primitives.stats import headcount, headcount_key, put_stat, set_stats

BLOOD_GODS = frozenset({Domain.BLOOD, Domain.DEATH, Domain.BONE, Domain.HUNGER, Domain.WAR})
THOUSAND = 1000


def feed_god(ctx: TickContext, church: Church, amount: int) -> None:
    god = church.god
    if god is None or not ({god.domain_primary, god.domain_secondary} & BLOOD_GODS):
        return
    before = god.essence
    god.essence += amount
    cap_gained_essence(ctx.rules, god, before)


async def human_sacrifice(ctx: TickContext, church: Church, book: FaithBook) -> int:
    table = ctx.rules.doctrine
    given = 0
    for member in church.members:
        people = headcount(member)
        victims = min(people, table.sacrifice_cohort)
        if victims <= 0:
            continue
        with flowing(FlowCategory.DEATH):
            put_stat(ctx.rules, member, headcount_key(member), people - victims)
        given += victims
    feed_god(ctx, church, table.sacrifice_essence)
    appalled = [community for community in book.communities.values() if community.world_id == church.cult.world_id and community not in church.members]
    for other in appalled:
        await remember(
            ctx.session,
            ctx.rules,
            holder_id=other.id,
            subject_id=church.cult.id,
            kind=MemoryKind.ILL_WILL,
            magnitude=-table.sacrifice_infamy,
            epoch=ctx.epoch,
            note="human sacrifice",
        )
    return given


async def sacrifices(ctx: TickContext, church: Church, book: FaithBook) -> int:
    table = ctx.rules.doctrine
    offered = 0
    if church.holds(TenetKind.ANIMAL_SACRIFICE):
        ledger = goods_of(ctx.session, ctx.epoch)
        for member in church.members:
            offered += await ledger.take_units(member.id, CommodityKind.LIVESTOCK, table.animal_sacrifice_livestock, GoodsFlow.OFFERING)
        if offered:
            feed_god(ctx, church, table.sacrifice_essence // 2 or 1)
    if church.holds(TenetKind.HUMAN_SACRIFICE) and church.members:
        offered += await human_sacrifice(ctx, church, book)
    return offered


async def church_year(ctx: TickContext, church: Church, book: FaithBook, *, laws: LawBook, atlas: RegionAtlas, knowledge: KnowledgeMap) -> list[FaithLine]:
    lines: list[FaithLine] = []
    cult = church.cult.id
    ctx.count("clergy_appointed", await staff(ctx, church))
    ctx.count("holdings_added", await survey_holdings(ctx, church))
    ctx.count("holding_income", await holding_income(ctx, church))
    ctx.count("tithes", await tithe(ctx, church, laws))
    ctx.count("devotion", await devotion(ctx, church, book.faith.patron(cult)))
    built = await spend(ctx, church, knowledge)
    if built in {"temple", "monastery"}:
        lines.append(FaithLine(f"{church.cult.name} raised {an(built)} from its tithes.", f"faith.{built}", (cult,)))
    if built:
        ctx.count(f"spent_{built}")
    pilgrims, _ = await pilgrimage(ctx, church)
    ctx.count("pilgrims", pilgrims)
    for saint in await saints(ctx, church):
        relic = await canonise(ctx, church, saint)
        text = f"{church.cult.name} named {saint.name} a saint; pilgrims come to the relics."
        lines.append(FaithLine(text, "faith.saint", (cult, saint.id, relic.item_entity_id)))
        ctx.count("saints")
    zeal = await stir(ctx, church, book, laws=laws, atlas=atlas)
    if pilgrims >= THOUSAND and church.doctrine is not None:
        gain = pilgrims // THOUSAND * ctx.rules.zeal.pilgrimage_per_1000
        church.doctrine.zeal_parts = {**church.doctrine.zeal_parts, "pilgrims": gain}
        if "zeal" not in church.doctrine.locked:
            zeal = clamp_int(zeal + gain, 0, PERCENT)
            set_stats(church.cult, zeal=zeal)
    fanatic = await fanaticism(ctx, church, book, atlas)
    if fanatic is not None:
        lines.append(fanatic)
        ctx.count("fanaticism")
    ctx.count("doctrinal_drift", await drift(ctx, church))
    ctx.count("heresies_suppressed", await suppress(ctx, church))
    quarrel = await investiture(ctx, church)
    if quarrel is not None:
        lines.append(quarrel)
    ctx.count("sacrifices", await sacrifices(ctx, church, book))
    ctx.count("pilgrim_plague", await pilgrim_plague(ctx, church, atlas))
    ctx.count("sacred_beasts_hunted", await sacred_beasts(ctx, church))
    ctx.count("torment_fear", await fear_of_torment(ctx, church))
    return lines


@reads(
    "cult.devotion",
    "cult.followers",
    "cult.influence",
    "cult.zeal",
    "item.damage",
    "item.might",
    "item.protection",
    "mortal.agility",
    "mortal.beauty",
    "mortal.charisma",
    "mortal.creativity",
    "mortal.endurance",
    "mortal.intellect",
    "mortal.lifespan",
    "mortal.perception",
    "mortal.strength",
    "mortal.willpower",
    "mortal.wisdom",
    "people.population",
    "people.prosperity",
    "settlement.population",
    "settlement.prosperity",
    "spirit.unrest",
    "table.afterlife_strata",
    "table.allele_pools",
    "table.applied_fixups",
    "table.battles",
    "table.bonds",
    "table.chronicle",
    "table.community_cohorts",
    "table.community_societies",
    "table.community_stocks",
    "table.cosmos",
    "table.creator",
    "table.cult_doctrines",
    "table.cult_holdings",
    "table.cult_offices",
    "table.cult_tenets",
    "table.culture_values",
    "table.disease_cures",
    "table.disease_profiles",
    "table.districts",
    "table.endemic_diseases",
    "table.entities",
    "table.entity_flags",
    "table.epoch_year_cursors",
    "table.genomes",
    "table.goods_flows",
    "table.herds",
    "table.heresies",
    "table.holder_levels",
    "table.holder_techniques",
    "table.immunities",
    "table.incident_participants",
    "table.incidents",
    "table.item_profiles",
    "table.language_profiles",
    "table.law_jurisdictions",
    "table.law_profiles",
    "table.laws",
    "table.lexemes",
    "table.ley_lines",
    "table.memories",
    "table.mind_attributes",
    "table.mind_profiles",
    "table.minds",
    "table.name_registry",
    "table.network_profiles",
    "table.node_materials",
    "table.nodes",
    "table.offices",
    "table.outbreaks",
    "table.personality_values",
    "table.place_environment",
    "table.place_profiles",
    "table.plague_responses",
    "table.polity_members",
    "table.polity_profiles",
    "table.pressures",
    "table.quarantines",
    "table.region_environment",
    "table.relics",
    "table.resource_profiles",
    "table.reverences",
    "table.settlement_infrastructure",
    "table.settlement_profiles",
    "table.skills",
    "table.sky_events",
    "table.sons",
    "table.souls",
    "table.species_hosts",
    "table.species_profiles",
    "table.species_ranges",
    "table.spirit_profiles",
    "table.tradition_profiles",
    "table.traits",
    "table.world_maps",
    "table.world_materials",
)
@writes(
    "cult.devotion",
    "cult.influence",
    "cult.zeal",
    "mortal.agility",
    "mortal.charisma",
    "mortal.intellect",
    "mortal.lifespan",
    "mortal.strength",
    "people.population",
    "settlement.population",
    "settlement.prosperity",
    "table.afterlife_strata",
    "table.applied_fixups",
    "table.bonds",
    "table.chronicle",
    "table.chronicle_entities",
    "table.community_societies",
    "table.community_stocks",
    "table.cult_doctrines",
    "table.cult_holdings",
    "table.cult_offices",
    "table.cult_tenets",
    "table.culture_values",
    "table.districts",
    "table.entities",
    "table.entity_flags",
    "table.epoch_year_cursors",
    "table.genomes",
    "table.goods_flows",
    "table.incident_participants",
    "table.incidents",
    "table.item_profiles",
    "table.language_profiles",
    "table.memories",
    "table.name_registry",
    "table.node_materials",
    "table.polity_profiles",
    "table.pressures",
    "table.relics",
    "table.skills",
    "table.sons",
    "table.soul_judgements",
    "table.spirit_profiles",
    "table.tradition_profiles",
)
async def faith_cycles(ctx: TickContext) -> None:
    book = await FaithBook.load(ctx.session)
    ctx.count("doctrines_founded", await ensure_doctrines(ctx, book))
    ctx.count("faith_backfilled", await backfill_faith(ctx, book))
    laws = await LawBook.load(ctx.session)
    atlas = await RegionAtlas.load(ctx.session)
    knowledge = await KnowledgeMap.load(ctx.session)
    for church in book.churches.values():
        if held(church.cult.id):
            continue
        for line in await church_year(ctx, church, book, laws=laws, atlas=atlas, knowledge=knowledge):
            await note(ctx, line.text, key=line.key, ids=list(line.ids), kind=ChronicleKind.WORSHIP)


@reads(
    "mortal.age",
    "mortal.agility",
    "mortal.charisma",
    "mortal.endurance",
    "mortal.hp",
    "mortal.intellect",
    "mortal.lifespan",
    "mortal.sanity",
    "mortal.strength",
    "mortal.willpower",
    "settlement.piety",
    "spirit.unrest",
    "table.afflictions",
    "table.afterlife_strata",
    "table.assistive_aids",
    "table.bodies",
    "table.body_customs",
    "table.bonds",
    "table.castings",
    "table.conditions",
    "table.cult_doctrines",
    "table.cult_tenets",
    "table.culture_values",
    "table.dimensions",
    "table.divine_wounds",
    "table.entities",
    "table.entity_traits",
    "table.epoch_year_cursors",
    "table.foreign_gods",
    "table.genomes",
    "table.holder_levels",
    "table.house_members",
    "table.house_profiles",
    "table.injuries",
    "table.item_profiles",
    "table.memories",
    "table.minds",
    "table.mortal_equipment",
    "table.natural_law_profiles",
    "table.nodes",
    "table.personality_values",
    "table.possessions",
    "table.prostheses",
    "table.region_pollution",
    "table.rite_effects",
    "table.rite_profiles",
    "table.sons",
    "table.spirit_profiles",
    "table.world_domain_hooks",
    "table.world_maps",
    "table.worlds",
)
@writes(
    "mortal.sanity",
    "spirit.unrest",
    "table.afflictions",
    "table.afterlife_strata",
    "table.bodies",
    "table.body_customs",
    "table.bonds",
    "table.castings",
    "table.chronicle",
    "table.chronicle_entities",
    "table.conditions",
    "table.entities",
    "table.epoch_year_cursors",
    "table.house_members",
    "table.house_profiles",
    "table.incident_participants",
    "table.incidents",
    "table.personality_values",
    "table.possessions",
    "table.region_pollution",
    "table.reincarnations",
    "table.rite_effects",
    "table.rite_profiles",
    "table.sons",
    "table.soul_judgements",
    "table.spirit_profiles",
    "table.traits",
)
async def soul_cycles(ctx: TickContext) -> None:
    atlas = await RegionAtlas.load(ctx.session)
    eaten_here = await soul_eaters(ctx, atlas)
    for profile, spirit in await profiles(ctx):
        if held(spirit.id):
            continue
        ctx.count(f"spirits_{await tend(ctx, profile, spirit)}")
        turned = await stratum_turn(ctx, profile, spirit)
        if turned is not None:
            ctx.count(f"strata_{turned}")
            if turned in {"faded", "reborn"}:
                continue
        region = atlas.top_region(spirit.id)
        fate = await gnaw(ctx, profile, spirit, eaten_here.get(region, [])) if region is not None else None
        if fate is not None:
            ctx.count(f"souls_{fate}")
            if fate == "eaten":
                continue
        child = await reincarnate(ctx, profile, spirit)
        if child is not None:
            ctx.count("reborn")
            await note(ctx, f"The soul of {spirit.name} was born again as {child.name}.", key="afterlife.reborn", ids=[spirit.id, child.id])
            continue
        host = await possess(ctx, profile, spirit)
        if host is not None:
            ctx.count("possessions")
            await note(ctx, f"{spirit.name} took hold of {host.name}.", key="afterlife.possession", ids=[spirit.id, host.id])
    possessed, exorcised = await possessions(ctx)
    ctx.count("possessed", possessed)
    ctx.count("exorcised", exorcised)
    ctx.count("realm_essence", await realm_essence(ctx))


FAITH_PHASES = (Phase("faith_cycles", faith_cycles),)
SOUL_PHASES = (Phase("soul_cycles", soul_cycles),)
PHASES = FAITH_PHASES + SOUL_PHASES
