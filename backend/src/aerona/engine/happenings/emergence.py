from collections import Counter

from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.db.repositories.chronicle import incident_for
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.celestial import SkyEventRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.faith import HeresyRow
from aerona.db.tables.mind import MemoryRow
from aerona.db.tables.settlement import SettlementProfileRow, SettlementTreasuryRow
from aerona.db.tables.warfare import BattleRow
from aerona.db.write_guard import held
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.chronicle import ChronicleKind, FeedCategory
from aerona.domain.enums.entity import COMMUNITY_TYPES, SOCIETY_TYPES, EngineKind, EntityStatus, EntityType
from aerona.domain.enums.happening import EventPhase
from aerona.domain.enums.military import OutcomeClass
from aerona.domain.enums.mind import MemoryKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.settlement import TreasuryEntry
from aerona.domain.enums.world import SkyEventKind
from aerona.engine.context import TickContext
from aerona.engine.happenings.effects import onset
from aerona.engine.happenings.profile import Happening, happen, record_casualties, region_of
from aerona.engine.interconnect.flows import FlowCategory
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.primitives.stats import stat_or

REALM_TYPES = (EntityType.POLITY, EntityType.SETTLEMENT, EntityType.PEOPLE)
RULER_TYPES = (EntityType.MORTAL,)


def tag(ctx: TickContext, name: str) -> str:
    return f"{name} (Epoch {ctx.epoch})"


async def born_names(ctx: TickContext, kind: EngineKind) -> set[str]:
    statement = select(EntityRow.name).where(EntityRow.entity_type == EntityType.EVENT, EntityRow.engine_kind == kind, EntityRow.birth_epoch == ctx.epoch)
    return {name.casefold() for name in await ctx.session.scalars(statement)}


async def recent_at(ctx: TickContext, kind: EngineKind, location_id: int, epochs: int) -> bool:
    statement = select(EntityRow.id).where(
        EntityRow.entity_type == EntityType.EVENT,
        EntityRow.engine_kind == kind,
        EntityRow.location_id == location_id,
        EntityRow.birth_epoch > ctx.epoch - epochs,
    )
    return await ctx.session.scalar(statement.limit(1)) is not None


async def record_fire(ctx: TickContext, town: EntityRow, dead: int) -> EntityRow:
    atlas = await RegionAtlas.load(ctx.session)
    event, _ = await happen(
        ctx,
        Happening(
            EngineKind.FIRE,
            tag(ctx, f"the Great Fire of {town.name}"),
            f"A great fire swept through {town.name}; {dead} died in the flames.",
            "",
            town,
            clamp_int(20 + dead * PERCENT // max(1, stat_or(town, "population", 0) + dead) * 4, 0, PERCENT),
            {town.id: IncidentRole.TARGET},
            feed=FeedCategory.DISASTER,
        ),
        atlas,
        incident_id=incident_for(ctx.session, town.id, ctx.epoch),
    )
    await record_casualties(ctx, event.id, town, dead, category=FlowCategory.DISASTER, phase=EventPhase.ONSET)
    await onset(ctx, event, town, atlas)
    return event


async def record_sack(ctx: TickContext, town: EntityRow, dead: int) -> EntityRow:
    atlas = await RegionAtlas.load(ctx.session)
    event, _ = await happen(
        ctx,
        Happening(
            EngineKind.SACK,
            tag(ctx, f"the Sack of {town.name}"),
            f"{town.name} was sacked; its storehouses were emptied and {dead} of its people were put to the sword.",
            f"The sack of {town.name} was remembered in every ballad of the war.",
            town,
            clamp_int(40 + dead * PERCENT // max(1, stat_or(town, "population", 0) + dead) * 4, 0, PERCENT),
            {town.id: IncidentRole.TARGET},
            feed=FeedCategory.WAR,
            chronicle=ChronicleKind.WAR,
        ),
        atlas,
    )
    await record_casualties(ctx, event.id, town, dead, category=FlowCategory.CASUALTY, phase=EventPhase.ONSET)
    await onset(ctx, event, town, atlas)
    return event


async def festivals(ctx: TickContext, atlas: RegionAtlas) -> int:
    table = ctx.rules.events
    rows = await ctx.session.scalars(
        select(SettlementTreasuryRow.settlement_entity_id)
        .where(SettlementTreasuryRow.epoch == ctx.epoch, SettlementTreasuryRow.entry == TreasuryEntry.FESTIVAL)
        .distinct()
        .order_by(SettlementTreasuryRow.settlement_entity_id)
    )
    known = await born_names(ctx, EngineKind.FESTIVAL_OF_NOTE)
    made = 0
    for town_id in list(rows):
        town = await ctx.session.get(EntityRow, town_id)
        if town is None or town.status is not EntityStatus.CANON or stat_or(town, "population", 0) < table.festival_population or held(town.id):
            continue
        name = tag(ctx, f"the Great Festival of {town.name}")
        if name.casefold() in known or made >= table.emergent_cap:
            continue
        event, _ = await happen(
            ctx,
            Happening(
                EngineKind.FESTIVAL_OF_NOTE,
                name,
                f"For days {town.name} feasted, danced and gave thanks; the festival was spoken of for a generation.",
                f"{town.name} held a festival that was spoken of for a generation.",
                town,
                30,
                {town.id: IncidentRole.ACTOR},
            ),
            atlas,
        )
        await onset(ctx, event, town, atlas)
        made += 1
    return made


async def coronations(ctx: TickContext, atlas: RegionAtlas) -> int:
    table = ctx.rules.events
    bonds = await ctx.session.scalars(
        select(BondRow).where(BondRow.kind == BondKind.RULES, BondRow.epoch == ctx.epoch, BondRow.state == BondState.ACTIVE).order_by(BondRow.id)
    )
    known = await born_names(ctx, EngineKind.CORONATION)
    made = 0
    for bond in list(bonds):
        ruler = await ctx.session.get(EntityRow, bond.source_node_id)
        realm = await ctx.session.get(EntityRow, bond.target_node_id)
        if ruler is None or realm is None or ruler.entity_type not in RULER_TYPES or realm.entity_type not in REALM_TYPES:
            continue
        if ruler.status is not EntityStatus.CANON or realm.power_level < table.coronation_realm_power or held(ruler.id, realm.id):
            continue
        name = tag(ctx, f"the Coronation of {ruler.name}")
        if name.casefold() in known or made >= table.emergent_cap:
            continue
        event, _ = await happen(
            ctx,
            Happening(
                EngineKind.CORONATION,
                name,
                f"{ruler.name} was crowned ruler of {realm.name} before the gathered great of the realm.",
                f"{ruler.name} was crowned ruler of {realm.name}.",
                realm,
                35,
                {ruler.id: IncidentRole.ACTOR, realm.id: IncidentRole.TARGET},
            ),
            atlas,
        )
        await onset(ctx, event, realm, atlas)
        made += 1
    return made


async def weddings(ctx: TickContext, atlas: RegionAtlas) -> int:
    table = ctx.rules.events
    memories = await ctx.session.scalars(
        select(MemoryRow).where(MemoryRow.kind == MemoryKind.MARRIED_INTO, MemoryRow.epoch == ctx.epoch).order_by(MemoryRow.id)
    )
    pairs = sorted({(min(row.holder_node_id, row.subject_node_id), max(row.holder_node_id, row.subject_node_id)) for row in memories})
    known = await born_names(ctx, EngineKind.WEDDING)
    made = 0
    for first_id, second_id in pairs:
        first = await ctx.session.get(EntityRow, first_id)
        second = await ctx.session.get(EntityRow, second_id)
        if (
            first is None
            or second is None
            or first.entity_type not in COMMUNITY_TYPES
            or second.entity_type not in COMMUNITY_TYPES
            or held(first.id, second.id)
        ):
            continue
        name = tag(ctx, f"the Wedding of {first.name} and {second.name}")
        if name.casefold() in known or made >= table.emergent_cap:
            continue
        event, _ = await happen(
            ctx,
            Happening(
                EngineKind.WEDDING,
                name,
                f"The houses of {first.name} and {second.name} were joined in a wedding feast that lasted many days.",
                f"A wedding feast joined the houses of {first.name} and {second.name}.",
                first,
                25,
                {first.id: IncidentRole.ACTOR, second.id: IncidentRole.ACTOR},
                regions=[region for region in [await region_of(ctx.session, atlas, second.id)] if region is not None],
            ),
            atlas,
        )
        await onset(ctx, event, first, atlas, second)
        made += 1
    return made


async def massacres(ctx: TickContext, atlas: RegionAtlas) -> int:
    table = ctx.rules.events
    battles = await ctx.session.scalars(
        select(BattleRow).where(BattleRow.epoch == ctx.epoch, BattleRow.outcome_class == OutcomeClass.MASSACRE).order_by(BattleRow.id)
    )
    known = await born_names(ctx, EngineKind.MASSACRE)
    made = 0
    for battle in list(battles):
        loser = await ctx.session.get(EntityRow, battle.loser_entity_id)
        winner = await ctx.session.get(EntityRow, battle.winner_entity_id)
        place = await ctx.session.get(EntityRow, battle.place_entity_id) if battle.place_entity_id is not None else None
        where = place or loser
        if loser is None or where is None or held(loser.id, where.id, battle.winner_entity_id):
            continue
        name = tag(ctx, f"the Massacre at {where.name}")
        if name.casefold() in known or made >= table.emergent_cap:
            continue
        victor = winner.name if winner is not None else "the victors"
        event, _ = await happen(
            ctx,
            Happening(
                EngineKind.MASSACRE,
                name,
                f"After the battle at {where.name}, {victor} gave no quarter; {battle.loser_losses} of {loser.name} fell in the rout.",
                f"No quarter was given at {where.name}; {loser.name} was put to the sword.",
                where,
                clamp_int(50 + battle.loser_losses // 100, 0, PERCENT),
                {loser.id: IncidentRole.TARGET, **({winner.id: IncidentRole.ACTOR} if winner is not None else {})},
                feed=FeedCategory.WAR,
                chronicle=ChronicleKind.WAR,
            ),
            atlas,
        )
        if loser.entity_type in SOCIETY_TYPES:
            await record_casualties(ctx, event.id, loser, battle.loser_losses, category=FlowCategory.CASUALTY, phase=EventPhase.ONSET)
        await onset(ctx, event, where, atlas)
        made += 1
    return made


async def riots(ctx: TickContext, atlas: RegionAtlas) -> int:
    table = ctx.rules.events
    towns = await ctx.session.scalars(
        select(SettlementProfileRow).where(SettlementProfileRow.unrest >= table.riot_unrest).order_by(SettlementProfileRow.settlement_entity_id)
    )
    made = 0
    for profile in list(towns):
        town = await ctx.session.get(EntityRow, profile.settlement_entity_id)
        if town is None or town.status is not EntityStatus.CANON or made >= table.emergent_cap or held(town.id):
            continue
        if await recent_at(ctx, EngineKind.RIOT, town.id, max(1, table.riot_cooldown_epochs)):
            continue
        event, _ = await happen(
            ctx,
            Happening(
                EngineKind.RIOT,
                tag(ctx, f"the Riots of {town.name}"),
                f"The streets of {town.name} filled with an angry crowd; shops burned and the watch was driven back.",
                f"Riots broke out in {town.name}.",
                town,
                clamp_int(profile.unrest, 0, PERCENT),
                {town.id: IncidentRole.SUBJECT},
                feed=FeedCategory.DISASTER,
            ),
            atlas,
        )
        await onset(ctx, event, town, atlas)
        made += 1
    return made


async def schism_councils(ctx: TickContext, atlas: RegionAtlas) -> int:
    table = ctx.rules.events
    heresies = await ctx.session.scalars(select(HeresyRow).where(HeresyRow.declared_epoch == ctx.epoch).order_by(HeresyRow.heresy_entity_id))
    known = await born_names(ctx, EngineKind.SCHISM_COUNCIL)
    made = 0
    for heresy in list(heresies):
        sect = await ctx.session.get(EntityRow, heresy.heresy_entity_id)
        parent = await ctx.session.get(EntityRow, heresy.parent_entity_id)
        if sect is None or parent is None or made >= table.emergent_cap or held(sect.id, parent.id, parent.location_id):
            continue
        where = await ctx.session.get(EntityRow, parent.location_id) if parent.location_id is not None else None
        name = tag(ctx, f"the Council of {sect.name}")
        if name.casefold() in known:
            continue
        event, _ = await happen(
            ctx,
            Happening(
                EngineKind.SCHISM_COUNCIL,
                name,
                f"The elders of {parent.name} met in council and could not agree; those who would not yield walked out as {sect.name}.",
                f"A council of {parent.name} broke apart; {sect.name} walked out.",
                where or parent,
                40,
                {parent.id: IncidentRole.SUBJECT, sect.id: IncidentRole.ACTOR},
                chronicle=ChronicleKind.WORSHIP,
            ),
            atlas,
        )
        await onset(ctx, event, parent, atlas, sect)
        made += 1
    return made


async def eclipse_watches(ctx: TickContext, atlas: RegionAtlas) -> int:
    table = ctx.rules.events
    eclipses = await ctx.session.scalars(
        select(SkyEventRow)
        .where(SkyEventRow.kind == SkyEventKind.ECLIPSE, SkyEventRow.epoch == ctx.epoch, SkyEventRow.world_id.is_not(None))
        .order_by(SkyEventRow.id)
    )
    known = await born_names(ctx, EngineKind.ECLIPSE_WATCH)
    made = 0
    for world_id in sorted({row.world_id for row in eclipses if row.world_id is not None}):
        towns = [town for town in await _communities(ctx, world_id) if town.entity_type is EntityType.SETTLEMENT and not held(town.id)]
        host = max(towns, key=lambda town: (stat_or(town, "population", 0), -town.id), default=None)
        if host is None or made >= table.emergent_cap:
            continue
        name = tag(ctx, f"the Watch of the Dark Sun over {host.name}")
        if name.casefold() in known:
            continue
        event, _ = await happen(
            ctx,
            Happening(
                EngineKind.ECLIPSE_WATCH,
                name,
                f"The sun went dark over {host.name}; the people gathered on the roofs and walls and waited in silence for the light.",
                f"The people of {host.name} gathered to watch the sun go dark.",
                host,
                30,
                {host.id: IncidentRole.WITNESS},
            ),
            atlas,
        )
        await onset(ctx, event, host, atlas)
        made += 1
    return made


async def _communities(ctx: TickContext, world_id: int) -> list[EntityRow]:
    statement = select(EntityRow).where(EntityRow.world_id == world_id, EntityRow.status == EntityStatus.CANON, EntityRow.entity_type.in_(list(SOCIETY_TYPES)))
    return list(await ctx.session.scalars(statement.order_by(EntityRow.id)))


async def emerge(ctx: TickContext, atlas: RegionAtlas) -> Counter[str]:
    counts: Counter[str] = Counter()
    counts["festivals"] = await festivals(ctx, atlas)
    counts["coronations"] = await coronations(ctx, atlas)
    counts["weddings"] = await weddings(ctx, atlas)
    counts["massacres"] = await massacres(ctx, atlas)
    counts["riots"] = await riots(ctx, atlas)
    counts["schism_councils"] = await schism_councils(ctx, atlas)
    counts["eclipse_watches"] = await eclipse_watches(ctx, atlas)
    return counts
