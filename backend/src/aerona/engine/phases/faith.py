from aerona.constants.units import PERCENT
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.domain import Domain
from aerona.domain.enums.economy import CommodityKind, GoodsFlow
from aerona.domain.enums.faith import TenetKind
from aerona.domain.enums.mind import MemoryKind
from aerona.engine.context import TickContext
from aerona.engine.economy.stocks import goods_of
from aerona.engine.faith.book import Church, FaithBook
from aerona.engine.faith.doctrine import ensure_doctrines, staff
from aerona.engine.faith.souls import consume, fear_of_torment, possess, possessions, profiles, reincarnate, soul_eaters, tend
from aerona.engine.faith.works import canonise, pilgrim_plague, pilgrimage, sacred_beasts, saints, spend, survey_holdings, tithe
from aerona.engine.faith.zeal import stir
from aerona.engine.faith.zealotry import drift, fanaticism, investiture, suppress
from aerona.engine.gods.progress import cap_gained_essence
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.mind.memories import remember
from aerona.engine.notes import note
from aerona.engine.phase import Phase
from aerona.engine.polity.laws import LawBook
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.knowledge import KnowledgeMap
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.primitives.stats import set_stats

BLOOD_GODS = frozenset({Domain.BLOOD, Domain.DEATH, Domain.BONE, Domain.HUNGER, Domain.WAR})
THOUSAND = 1000


def feed_god(ctx: TickContext, church: Church, amount: int) -> None:
    god = church.god
    if god is None or not ({god.domain_primary, god.domain_secondary} & BLOOD_GODS):
        return
    before = god.essence
    god.essence += amount
    cap_gained_essence(ctx.rules, god, before)


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
        feed_god(ctx, church, table.sacrifice_essence)
        appalled = [community for community in book.communities.values() if community.world_id == church.cult.world_id and community not in church.members]
        for other in appalled[:5]:
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
        offered += 1
    return offered


async def church_year(ctx: TickContext, church: Church, book: FaithBook, *, laws: LawBook, atlas: RegionAtlas, knowledge: KnowledgeMap) -> list[str]:
    lines: list[str] = []
    ctx.count("clergy_appointed", await staff(ctx, church))
    ctx.count("holdings_added", await survey_holdings(ctx, church))
    ctx.count("tithes", tithe(ctx, church))
    built = await spend(ctx, church, knowledge)
    if built in {"temple", "monastery"}:
        lines.append(f"{church.cult.name} raised a {built} from its tithes.")
    if built:
        ctx.count(f"spent_{built}")
    pilgrims, _ = await pilgrimage(ctx, church)
    ctx.count("pilgrims", pilgrims)
    for saint in await saints(ctx, church):
        await canonise(ctx, church, saint)
        lines.append(f"{church.cult.name} named {saint.name} a saint; pilgrims come to the bones.")
        ctx.count("saints")
    zeal = await stir(ctx, church, book, laws=laws, atlas=atlas)
    if pilgrims >= THOUSAND and church.doctrine is not None:
        gain = pilgrims // THOUSAND * ctx.rules.zeal.pilgrimage_per_1000
        church.doctrine.zeal_parts = {**church.doctrine.zeal_parts, "pilgrims": gain}
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
    "cult.followers",
    "cult.influence",
    "cult.zeal",
    "people.population",
    "people.prosperity",
    "settlement.population",
    "settlement.prosperity",
    "table.afterlife_strata",
    "table.battles",
    "table.bonds",
    "table.chronicle",
    "table.community_societies",
    "table.community_stocks",
    "table.cult_doctrines",
    "table.cult_holdings",
    "table.cult_offices",
    "table.cult_tenets",
    "table.culture_values",
    "table.entity_flags",
    "table.epoch_year_cursors",
    "table.goods_flows",
    "table.heresies",
    "table.holder_levels",
    "table.language_profiles",
    "table.law_jurisdictions",
    "table.law_profiles",
    "table.laws",
    "table.lexemes",
    "table.memories",
    "table.name_registry",
    "table.nodes",
    "table.outbreaks",
    "table.place_environment",
    "table.polity_members",
    "table.relics",
    "table.reverences",
    "table.skills",
    "table.world_maps",
)
@writes(
    "cult.influence",
    "cult.zeal",
    "settlement.prosperity",
    "table.bonds",
    "table.chronicle",
    "table.chronicle_entities",
    "table.community_stocks",
    "table.cult_doctrines",
    "table.cult_holdings",
    "table.cult_offices",
    "table.cult_tenets",
    "table.entities",
    "table.entity_flags",
    "table.epoch_year_cursors",
    "table.goods_flows",
    "table.incident_participants",
    "table.incidents",
    "table.name_registry",
    "table.relics",
)
async def faith_cycles(ctx: TickContext) -> None:
    book = await FaithBook.load(ctx.session)
    ctx.count("doctrines_founded", await ensure_doctrines(ctx, book))
    laws = await LawBook.load(ctx.session)
    atlas = await RegionAtlas.load(ctx.session)
    knowledge = await KnowledgeMap.load(ctx.session)
    for church in book.churches.values():
        for line in await church_year(ctx, church, book, laws=laws, atlas=atlas, knowledge=knowledge):
            await note(ctx, line, key="faith.year", ids=[church.cult.id], kind=ChronicleKind.WORSHIP)


@reads(
    "spirit.unrest",
    "table.bonds",
    "table.castings",
    "table.cult_tenets",
    "table.culture_values",
    "table.entity_traits",
    "table.memories",
    "table.possessions",
    "table.spirit_profiles",
    "table.world_maps",
)
@writes("spirit.unrest", "table.conditions", "table.entities", "table.possessions", "table.reincarnations", "table.spirit_profiles")
async def soul_cycles(ctx: TickContext) -> None:
    atlas = await RegionAtlas.load(ctx.session)
    eaten_here = await soul_eaters(ctx, atlas)
    for profile, spirit in await profiles(ctx):
        ctx.count(f"spirits_{await tend(ctx, profile, spirit)}")
        region = atlas.top_region(spirit.id)
        if region in eaten_here and ctx.rng(f"eaten.{spirit.id}.{ctx.epoch}").chance(ctx.rules.necromancy.soul_eater_chance):
            await consume(ctx, profile, spirit)
            ctx.count("souls_eaten")
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
    held, exorcised = await possessions(ctx)
    ctx.count("possessed", held)
    ctx.count("exorcised", exorcised)


FAITH_PHASES = (Phase("faith_cycles", faith_cycles),)
SOUL_PHASES = (Phase("soul_cycles", soul_cycles),)
PHASES = FAITH_PHASES + SOUL_PHASES
