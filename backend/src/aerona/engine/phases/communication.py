from sqlalchemy import select

from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.engine.communication.ciphers import CipherTally, tend_ciphers
from aerona.engine.communication.dispatches import DispatchTally, courtesies, tend_dispatches
from aerona.engine.communication.opinion import OpinionTally, tend_opinion
from aerona.engine.communication.signals import SignalTally, build_links, fall_links
from aerona.engine.context import TickContext
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.phase import Phase
from aerona.engine.primitives.distance import RegionAtlas

OPINION_HOLDERS = (EntityType.SETTLEMENT, EntityType.PEOPLE)
CIPHER_OWNERS = (EntityType.POLITY, EntityType.SETTLEMENT, EntityType.FACTION, EntityType.CULT)


async def living(ctx: TickContext, kinds: tuple[EntityType, ...]) -> list[EntityRow]:
    rows = await ctx.session.scalars(
        select(EntityRow).where(EntityRow.entity_type.in_(list(kinds)), EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id)
    )
    return list(rows)


@reads(
    "table.armies",
    "table.army_profiles",
    "table.bonds",
    "table.ciphers",
    "table.community_relations",
    "table.cosmos",
    "table.custom_kinds",
    "table.entities",
    "table.faction_profiles",
    "table.held_identities",
    "table.holder_custom_techniques",
    "table.holder_techniques",
    "table.memories",
    "table.messages",
    "table.nodes",
    "table.occupations",
    "table.offices",
    "table.polity_profiles",
    "table.relationships",
    "table.reputations",
    "table.ruler_currencies",
    "table.signal_links",
    "table.spy_networks",
    "table.traits",
    "table.world_maps",
)
@writes("table.ciphers", "table.favours", "table.messages", "table.secrets", "table.signal_links", "table.treaty_breaches")
async def correspondence(ctx: TickContext) -> None:
    atlas = await RegionAtlas.load(ctx.session)
    dispatches = DispatchTally()
    await courtesies(ctx, atlas, dispatches)
    await tend_dispatches(ctx, dispatches)
    ciphers = CipherTally()
    await tend_ciphers(ctx, await living(ctx, CIPHER_OWNERS), ciphers)
    signals = SignalTally()
    await build_links(ctx, atlas, signals)
    await fall_links(ctx, signals)
    for key, value in (*vars(dispatches).items(),):
        ctx.count(f"dispatches_{key}", value)
    for key, value in vars(ciphers).items():
        ctx.count(f"ciphers_{key}", value)
    for key, value in vars(signals).items():
        ctx.count(f"signals_{key}", value)


@reads(
    "cult.zeal",
    "people.piety",
    "people.prosperity",
    "settlement.piety",
    "settlement.prosperity",
    "table.artwork_profiles",
    "table.bonds",
    "table.cult_holdings",
    "table.culture_values",
    "table.entities",
    "table.holder_techniques",
    "table.ideology_adherents",
    "table.incident_participants",
    "table.law_jurisdictions",
    "table.law_profiles",
    "table.mortal_profiles",
    "table.nodes",
    "table.offices",
    "table.polity_members",
    "table.polity_profiles",
    "table.public_opinion",
    "table.rumours",
    "table.satires",
    "table.settlement_profiles",
    "table.war_sides",
    "table.wars",
)
@writes("table.public_opinion")
async def public_opinion(ctx: TickContext) -> None:
    tally = OpinionTally()
    await tend_opinion(ctx, await living(ctx, OPINION_HOLDERS), tally)
    ctx.count("opinions_formed", tally.formed)
    ctx.count("censorship_found", tally.censorship_found)


PHASES = (Phase("correspondence", correspondence), Phase("public_opinion", public_opinion))
