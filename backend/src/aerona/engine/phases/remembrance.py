import re
from dataclasses import dataclass
from enum import StrEnum

from sqlalchemy import select

from aerona.core.errors import ValidationFailedError
from aerona.db.repositories.bonds import BondDraft, BondRepository
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.sons import SonRow
from aerona.db.tables.warfare import WarRow, WarSideRow
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.domain import DEATH_DOMAINS, Domain
from aerona.domain.enums.entity import COMMUNITY_TYPES, HERO_ROLES, EngineKind, EntityFlag, EntityStatus, EntityType, MortalRole
from aerona.domain.enums.mind import MemoryKind
from aerona.domain.enums.son import SonStatus
from aerona.domain.enums.structure import StructureKind
from aerona.domain.models.entity_stats import ArtworkStats, EntityStats, LegendStats, StructureStats, TraditionStats
from aerona.engine.context import TickContext
from aerona.engine.disease.outbreaks import disease_god
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.notes import note
from aerona.engine.phase import Phase
from aerona.engine.primitives.faith import change_religion, living_patron
from aerona.engine.primitives.naming import seed_of
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.primitives.queries import add_flag, canon, connect, flags_by_entity, living_entity
from aerona.engine.primitives.records import RecordSpec, create_record
from aerona.engine.primitives.stats import headcount_bounds, set_stats, shift_stat, stat
from aerona.engine.services.community_relations import change_relation
from aerona.engine.structures.profiles import ensure_profile

EPOCH_SUFFIX = re.compile(r"\s*\(Epoch \d+\)\s*")
LIVES_LOST = re.compile(r"(\d+) lives lost")
MEMORIAL_TYPES = frozenset({EntityType.ARTWORK, EntityType.LEGEND, EntityType.TRADITION, EntityType.STRUCTURE})
WAR_KINDS = frozenset({EngineKind.WAR, EngineKind.BATTLE, EngineKind.SIEGE})
DISASTER_KINDS = frozenset(
    {EngineKind.EARTHQUAKE, EngineKind.FLOOD, EngineKind.PLAGUE, EngineKind.DROUGHT, EngineKind.STORM, EngineKind.MAGIC_STORM, EngineKind.FAMINE}
)
PLAGUE_DOMAINS = DEATH_DOMAINS | {Domain.PLAGUE, Domain.LIFE}
HERO_FLAGS = frozenset({EntityFlag.CHOSEN, EntityFlag.AGE_CHANGER, EntityFlag.PROPHET, EntityFlag.LEGENDARY})
HOME_BONDS = (BondKind.LIVES_IN, BondKind.DESCENDS_FROM, BondKind.MEMBER_OF)


class MemorialForm(StrEnum):
    MONUMENT = "monument"
    EPIC = "epic"
    LAMENT = "lament"
    TRADITION = "tradition"
    TALE = "tale"


@dataclass(frozen=True)
class WarMemory:
    ids: list[int]
    victor: EntityRow | None
    loser: EntityRow | None
    sides: list[EntityRow]


def plain_name(name: str) -> str:
    return EPOCH_SUFFIX.sub(" ", name).strip()


async def is_remembered(ctx: TickContext, node_id: int) -> bool:
    statement = (
        select(BondRow.id)
        .join(EntityRow, EntityRow.id == BondRow.source_node_id)
        .where(BondRow.target_node_id == node_id, BondRow.state != BondState.HIDDEN_REJECTED, EntityRow.entity_type.in_(list(MEMORIAL_TYPES)))
        .limit(1)
    )
    return await ctx.session.scalar(statement) is not None


def is_rich(ctx: TickContext, community: EntityRow | None) -> bool:
    if community is None:
        return False
    value = stat(community, "prosperity")
    return (value if value is not None else stat(community, "wealth") or 0) >= ctx.rules.remembrance.rich_threshold


def seat_of(community: EntityRow | None) -> int | None:
    if community is None:
        return None
    return community.id if community.entity_type is EntityType.SETTLEMENT else community.location_id


async def memorial(ctx: TickContext, form: MemorialForm, name: str, subtype: str, body: str, *, location_id: int | None, world_id: int) -> EntityRow:
    settings = ctx.rules.remembrance
    rng = ctx.rng(seed_of("memorial", name))
    stats: EntityStats
    if form is MemorialForm.MONUMENT:
        entity_type, power = EntityType.STRUCTURE, settings.monument_power
        stats = StructureStats(
            splendor=clamp_int(settings.monument_splendor + rng.die(settings.monument_splendor_die), 0, 100),
            durability=clamp_int(settings.monument_durability + rng.die(settings.monument_durability_die), 0, 100),
            function=clamp_int(settings.monument_function + rng.die(settings.monument_function_die), 0, 100),
        )
    elif form in (MemorialForm.EPIC, MemorialForm.LAMENT):
        entity_type, power = EntityType.ARTWORK, settings.work_power
        stats = ArtworkStats(
            renown=clamp_int(settings.work_renown + rng.die(settings.work_renown_die), 0, 100),
            influence=clamp_int(settings.work_influence + rng.die(settings.work_influence_die), 0, 100),
        )
    elif form is MemorialForm.TRADITION:
        entity_type, power = EntityType.TRADITION, settings.tradition_power
        stats = TraditionStats(spread=settings.tradition_spread, rigidity=settings.tradition_rigidity)
    else:
        entity_type, power = EntityType.LEGEND, settings.legend_power
        stats = LegendStats(spread=settings.legend_spread)
    created = await create_record(
        ctx,
        RecordSpec(
            entity_type=entity_type,
            name=name,
            body=body,
            stats=stats,
            power=power,
            location_id=location_id,
            world_id=world_id,
            subtype=subtype,
            flags=(EntityFlag.COMMEMORATION,),
        ),
    )
    if entity_type is EntityType.STRUCTURE:
        await ensure_profile(ctx.session, ctx.rules, ctx.epoch, created, StructureKind.MONUMENT)
    return created


async def _tell(ctx: TickContext, record: EntityRow, about_ids: list[int], description: str) -> None:
    bonds = BondRepository(ctx.session)
    for about in about_ids:
        await bonds.connect(BondDraft(record.id, about, BondKind.TELLS_OF, ctx.epoch, description))


async def fallen_of_war(ctx: TickContext, war_event_id: int) -> list[int]:
    parts = list(await ctx.session.scalars(select(BondRow.source_node_id).where(BondRow.kind == BondKind.PART_OF, BondRow.target_node_id == war_event_id)))
    statement = (
        select(EntityRow.id)
        .join(BondRow, BondRow.target_node_id == EntityRow.id)
        .where(
            BondRow.source_node_id.in_([war_event_id, *parts]),
            BondRow.kind.in_([BondKind.PARTY_TO, BondKind.CAUSED]),
            EntityRow.entity_type == EntityType.MORTAL,
            EntityRow.status == EntityStatus.DEAD,
        )
        .distinct()
        .order_by(EntityRow.id)
        .limit(ctx.rules.remembrance.fallen_named)
    )
    return list(await ctx.session.scalars(statement))


@dataclass(frozen=True)
class WarScene:
    war: WarRow
    event: EntityRow
    name: str
    fallen: list[int]
    victor: EntityRow | None
    loser: EntityRow | None
    sides: list[EntityRow]

    @property
    def builder(self) -> EntityRow | None:
        return self.victor or (self.sides[0] if self.sides else None)


async def war_scene(ctx: TickContext, war: WarRow) -> WarScene | None:
    event = await ctx.session.get(EntityRow, war.event_entity_id)
    if event is None:
        return None
    side_ids = list(
        await ctx.session.scalars(select(WarSideRow.entity_id).where(WarSideRow.war_id == war.id).order_by(WarSideRow.joined_epoch, WarSideRow.entity_id))
    )
    sides = [entity for entity in [await ctx.session.get(EntityRow, side_id) for side_id in side_ids] if entity is not None]
    victor = await ctx.session.get(EntityRow, war.victor_entity_id) if war.victor_entity_id is not None else None
    loser = await ctx.session.get(EntityRow, war.loser_entity_id) if war.loser_entity_id is not None else None
    if victor is not None and loser is None:
        loser = next((side for side in sides if side.id != victor.id), None)
    return WarScene(war, event, plain_name(event.name), await fallen_of_war(ctx, event.id), victor, loser, sides)


async def war_monument(ctx: TickContext, scene: WarScene) -> EntityRow | None:
    builder = scene.builder
    seat = seat_of(builder) or scene.event.location_id
    if seat is None:
        return None
    by = f"{builder.name} raised it in memory of {scene.name}" if builder is not None else f"Raised in memory of {scene.name}"
    monument = await memorial(
        ctx,
        MemorialForm.MONUMENT,
        f"{scene.name} Monument",
        "victory monument",
        f"{by}; the names of the victors and the count of the fallen are carved on it.",
        location_id=seat,
        world_id=scene.event.world_id,
    )
    if builder is not None:
        await connect(ctx.session, builder.id, monument.id, BondKind.BUILT, ctx.epoch, description=f"in memory of {scene.name}")
    await _tell(ctx, monument, [scene.event.id, *scene.fallen], "remembers")
    return monument


async def war_epic(ctx: TickContext, scene: WarScene) -> EntityRow:
    builder = scene.builder
    bards = f"The bards of {builder.name}" if builder is not None else "Bards"
    epic = await memorial(
        ctx,
        MemorialForm.EPIC,
        f"{scene.name} Epic",
        "epic",
        f"{bards} sang a long epic of {scene.name}.",
        location_id=seat_of(builder),
        world_id=scene.event.world_id,
    )
    if builder is not None:
        await connect(ctx.session, builder.id, epic.id, BondKind.PRODUCED, ctx.epoch, description=f"for the victory of {scene.name}")
    await _tell(ctx, epic, [scene.event.id, *scene.fallen], "sings of")
    return epic


async def war_lament(ctx: TickContext, scene: WarScene) -> EntityRow:
    victor = scene.victor
    mourner = scene.loser or next((side for side in scene.sides if victor is None or side.id != victor.id), None)
    lament = await memorial(
        ctx,
        MemorialForm.LAMENT,
        f"{scene.name} Lament",
        "lament",
        f"{mourner.name if mourner is not None else 'The defeated'} mourned the defeat of {scene.name} and all it lost; every singing renews the grudge.",
        location_id=seat_of(mourner),
        world_id=scene.event.world_id,
    )
    if mourner is not None:
        await connect(ctx.session, mourner.id, lament.id, BondKind.PRODUCED, ctx.epoch, description=f"for the defeat of {scene.name}")
        if victor is not None and mourner.id != victor.id:
            await change_relation(ctx, mourner.id, victor.id, -ctx.rules.remembrance.lament_grudge, MemoryKind.LAMENTED, note=f"{scene.name} lament")
    await _tell(ctx, lament, [scene.event.id, *scene.fallen], "mourns")
    return lament


async def peace_oath(ctx: TickContext, scene: WarScene) -> EntityRow:
    names = " and ".join(side.name for side in scene.sides) or "Both sides"
    oath = await memorial(
        ctx,
        MemorialForm.TRADITION,
        f"{scene.name} Peace Oath",
        "peace oath",
        f"When {scene.name} ended with no victor, {names} began to lay down their arms on the same day every year and mourn their dead together.",
        location_id=None,
        world_id=scene.event.world_id,
    )
    living = [side for side in scene.sides if side.status is EntityStatus.CANON]
    for side in living:
        await connect(ctx.session, side.id, oath.id, BondKind.CELEBRATES, ctx.epoch)
    await _tell(ctx, oath, [scene.event.id, *scene.fallen], "remembers the peace of")
    if len(living) == len(scene.sides) == 2:
        await change_relation(
            ctx, scene.sides[0].id, scene.sides[1].id, ctx.rules.remembrance.peace_oath_warmth, MemoryKind.KEPT_OATH, note=f"{scene.name} peace oath"
        )
    return oath


async def remember_war(ctx: TickContext, war: WarRow, form: MemorialForm | None = None) -> WarMemory:
    scene = await war_scene(ctx, war)
    if scene is None:
        return WarMemory([], None, None, [])
    choice = form or (MemorialForm.EPIC if scene.victor is not None else MemorialForm.TRADITION)
    rich_victor = is_rich(ctx, scene.victor) and seat_of(scene.victor) is not None
    raise_monument = choice is MemorialForm.MONUMENT or (
        form is None and choice is MemorialForm.EPIC and rich_victor and ctx.rng(seed_of("war_memory", war.id)).chance(ctx.rules.remembrance.monument_chance)
    )
    ids: list[int] = []
    monument = await war_monument(ctx, scene) if raise_monument else None
    ids.extend([monument.id] if monument is not None else [])
    if choice is MemorialForm.EPIC or (choice is MemorialForm.MONUMENT and monument is None):
        ids.append((await war_epic(ctx, scene)).id)
    if (form is None and choice is MemorialForm.EPIC and scene.loser is not None) or choice is MemorialForm.LAMENT:
        ids.append((await war_lament(ctx, scene)).id)
    if choice in (MemorialForm.TRADITION, MemorialForm.TALE):
        ids.append((await peace_oath(ctx, scene)).id)
    return WarMemory(ids, scene.victor, scene.loser, scene.sides)


async def disaster_toll(ctx: TickContext, event: EntityRow) -> tuple[int, list[EntityRow]]:
    total = 0
    struck: list[EntityRow] = []
    for bond in await BondRepository(ctx.session).outgoing(event.id, BondKind.CAUSED, active_only=False):
        match = LIVES_LOST.search(bond.description or "")
        total += int(match.group(1)) if match else 0
        target = await living_entity(ctx.session, bond.target_node_id)
        if target is not None and target.entity_type in COMMUNITY_TYPES and target not in struck:
            struck.append(target)
    return total, struck


async def remember_disaster(ctx: TickContext, event: EntityRow, form: MemorialForm | None = None) -> list[int]:
    settings = ctx.rules.remembrance
    _, struck = await disaster_toll(ctx, event)
    name = plain_name(event.name)
    keeper = max(struck, key=lambda community: (stat(community, "population") or 0, -community.id), default=None)
    rng = ctx.rng(seed_of("disaster_memory", event.id))
    choice = form
    if choice is None:
        if keeper is not None and is_rich(ctx, keeper) and seat_of(keeper) is not None and rng.chance(settings.disaster_monument_chance):
            choice = MemorialForm.MONUMENT
        elif keeper is not None and rng.chance(settings.disaster_tradition_chance):
            choice = MemorialForm.TRADITION
        else:
            choice = MemorialForm.TALE
    if choice is MemorialForm.MONUMENT and keeper is not None and seat_of(keeper) is not None:
        monument = await memorial(
            ctx,
            MemorialForm.MONUMENT,
            f"{name} Monument",
            "memorial",
            f"{keeper.name} raised a stone for those it lost in {name}.",
            location_id=seat_of(keeper),
            world_id=event.world_id,
        )
        await connect(ctx.session, keeper.id, monument.id, BondKind.BUILT, ctx.epoch, description=f"in memory of {name}")
        await _tell(ctx, monument, [event.id], "remembers")
        return [monument.id]
    if choice is MemorialForm.TRADITION and keeper is not None:
        day = await memorial(
            ctx,
            MemorialForm.TRADITION,
            f"{name} Remembrance",
            "day of remembrance",
            f"Every year on the day of {name}, {keeper.name} lights no fire and counts the names of its dead.",
            location_id=None,
            world_id=event.world_id,
        )
        for community in struck[: settings.fallen_named]:
            await connect(ctx.session, community.id, day.id, BondKind.CELEBRATES, ctx.epoch)
        await _tell(ctx, day, [event.id], "remembers")
        return [day.id]
    tale = await memorial(
        ctx,
        MemorialForm.TALE,
        f"{name} Tale",
        "disaster tale",
        f"{name} was told and retold until it became a warning: why the sky and the earth grew angry, who was saved and who was not.",
        location_id=None,
        world_id=event.world_id,
    )
    await _tell(ctx, tale, [event.id], "tells of")
    for community in struck[: settings.fallen_named]:
        await connect(ctx.session, community.id, tale.id, BondKind.TELLS_OF, ctx.epoch, description="tells the disaster")
    return [tale.id]


async def home_of(ctx: TickContext, mortal: EntityRow) -> EntityRow | None:
    location = await living_entity(ctx.session, mortal.location_id)
    if location is not None and location.entity_type in COMMUNITY_TYPES:
        return location
    for kind in HOME_BONDS:
        for bond in reversed(await BondRepository(ctx.session).outgoing(mortal.id, kind, active_only=False)):
            home = await living_entity(ctx.session, bond.target_node_id)
            if home is not None and home.entity_type in COMMUNITY_TYPES:
                return home
    return None


def is_hero(mortal: EntityRow, flags: set[EntityFlag]) -> bool:
    return mortal.mortal_role in HERO_ROLES or mortal.mortal_role is MortalRole.RULER or bool(flags & HERO_FLAGS)


async def remember_dead(ctx: TickContext, mortal: EntityRow, form: MemorialForm | None = None) -> list[int]:
    settings = ctx.rules.remembrance
    home = await home_of(ctx, mortal)
    killed = bool(await BondRepository(ctx.session).incoming(mortal.id, BondKind.KILLED, active_only=False))
    rng = ctx.rng(seed_of("hero_memory", mortal.id))
    choice = form
    if choice is None:
        if is_rich(ctx, home) and seat_of(home) is not None and rng.chance(settings.hero_monument_chance):
            choice = MemorialForm.MONUMENT
        else:
            choice = MemorialForm.LAMENT if killed else MemorialForm.TALE
    if choice is MemorialForm.MONUMENT and home is not None and seat_of(home) is not None:
        record = await memorial(
            ctx,
            MemorialForm.MONUMENT,
            f"{mortal.name} Tomb",
            "tomb",
            f"{home.name} built a stone tomb for {mortal.name}; travellers stop before it and say the name.",
            location_id=seat_of(home),
            world_id=mortal.world_id,
        )
        await connect(ctx.session, home.id, record.id, BondKind.BUILT, ctx.epoch, description=f"in memory of {mortal.name}")
    elif choice in (MemorialForm.LAMENT, MemorialForm.EPIC):
        singers = f"the women of {home.name}" if home is not None else "the bards"
        record = await memorial(
            ctx,
            choice,
            f"{mortal.name} {'Lament' if choice is MemorialForm.LAMENT else 'Epic'}",
            choice.value,
            f"After {mortal.name} died, {singers} made a song for them.",
            location_id=seat_of(home),
            world_id=mortal.world_id,
        )
        if home is not None:
            await connect(ctx.session, home.id, record.id, BondKind.PRODUCED, ctx.epoch, description=f"for {mortal.name}")
    else:
        among = f"among {home.name}" if home is not None else "among mortals"
        record = await memorial(
            ctx,
            MemorialForm.TALE,
            f"{mortal.name} Saga",
            "hero's saga",
            f"After {mortal.name} died, their deeds began to be told {among}, larger with every telling.",
            location_id=None,
            world_id=mortal.world_id,
        )
        if home is not None:
            await connect(ctx.session, home.id, record.id, BondKind.TELLS_OF, ctx.epoch, description="tells the saga")
    await _tell(ctx, record, [mortal.id], "remembers")
    return [record.id]


async def _named(ctx: TickContext, ids: list[int]) -> str:
    names = [entity.name for entity in [await ctx.session.get(EntityRow, entity_id) for entity_id in ids] if entity is not None]
    return ", ".join(names)


async def wars_remembered(ctx: TickContext, budget: int) -> int:
    settings = ctx.rules.remembrance
    rng = ctx.rng("wars")
    made = 0
    for war in await ctx.session.scalars(select(WarRow).where(WarRow.ended_epoch == ctx.epoch - 1).order_by(WarRow.id)):
        if made >= budget:
            break
        if await is_remembered(ctx, war.event_entity_id):
            continue
        great = war.battles >= settings.great_war_battles or (war.ended_epoch or ctx.epoch) - war.started_epoch >= settings.great_war_epochs
        if not rng.chance(settings.war_chance if great else settings.small_war_chance):
            continue
        memory = await remember_war(ctx, war)
        if not memory.ids:
            continue
        made += 1
        event = await ctx.session.get(EntityRow, war.event_entity_id)
        war_name = plain_name(event.name) if event is not None else "the war"
        if memory.victor is not None:
            mourned = f"; {memory.loser.name} sang a lament for its defeat" if memory.loser is not None else ""
            text = f"{memory.victor.name} remembered the victory of {war_name}{mourned}: {await _named(ctx, memory.ids)}."
        else:
            text = f"{' and '.join(side.name for side in memory.sides)} swore a peace oath in memory of {war_name}."
        await note(ctx, text, key="remembrance.war", ids=[war.event_entity_id, *memory.ids, *(side.id for side in memory.sides)])
    return made


async def disasters_remembered(ctx: TickContext, budget: int) -> int:
    settings = ctx.rules.remembrance
    rng = ctx.rng("disasters")
    made = 0
    events = await ctx.session.scalars(
        select(EntityRow)
        .where(EntityRow.entity_type == EntityType.EVENT, EntityRow.birth_epoch == ctx.epoch - 1, EntityRow.engine_kind.in_(list(DISASTER_KINDS)))
        .order_by(EntityRow.id)
    )
    for event in list(events):
        if made >= budget:
            break
        if await is_remembered(ctx, event.id):
            continue
        toll, _ = await disaster_toll(ctx, event)
        if (stat(event, "severity") or 0) < settings.disaster_severity and toll < settings.disaster_losses:
            continue
        if not rng.chance(settings.disaster_chance):
            continue
        ids = await remember_disaster(ctx, event)
        made += 1
        await note(ctx, f"{plain_name(event.name)} was not forgotten: {await _named(ctx, ids)} remembers it.", key="remembrance.disaster", ids=[event.id, *ids])
    return made


async def heroes_remembered(ctx: TickContext, budget: int) -> int:
    settings = ctx.rules.remembrance
    rng = ctx.rng("heroes")
    made = 0
    dead = await ctx.session.scalars(
        select(EntityRow)
        .where(EntityRow.entity_type == EntityType.MORTAL, EntityRow.status == EntityStatus.DEAD, EntityRow.end_epoch == ctx.epoch - 1)
        .order_by(EntityRow.id)
    )
    flagged = {flag: await flags_by_entity(ctx.session, flag) for flag in HERO_FLAGS}
    for mortal in list(dead):
        if made >= budget:
            break
        flags = {flag for flag, holders in flagged.items() if mortal.id in holders}
        if not is_hero(mortal, flags) or await is_remembered(ctx, mortal.id) or not rng.chance(settings.hero_chance):
            continue
        ids = await remember_dead(ctx, mortal)
        made += 1
        await note(ctx, f"{mortal.name} was not forgotten: {await _named(ctx, ids)} remembers them.", key="remembrance.hero", ids=[mortal.id, *ids])
    return made


async def _plague_god(ctx: TickContext, community: EntityRow, current: SonRow | None, plague: EntityRow | None = None) -> SonRow | None:
    loosed = await disease_god(ctx.session, plague) if plague is not None else None
    if (
        loosed is not None
        and loosed.status is SonStatus.ACTIVE
        and loosed.current_world_id == community.world_id
        and (current is None or loosed.id != current.id)
    ):
        return loosed
    sons = await ctx.session.scalars(select(SonRow).where(SonRow.status == SonStatus.ACTIVE, SonRow.current_world_id == community.world_id).order_by(SonRow.id))
    fitting = [
        son for son in sons if (son.domain_primary in PLAGUE_DOMAINS or son.domain_secondary in PLAGUE_DOMAINS) and (current is None or son.id != current.id)
    ]
    return max(fitting, key=lambda son: (son.charisma, -son.id), default=None)


async def plague_faith(ctx: TickContext) -> int:
    settings = ctx.rules.remembrance
    plagues = await ctx.session.scalars(
        select(EntityRow)
        .where(EntityRow.entity_type == EntityType.EVENT, EntityRow.engine_kind == EngineKind.PLAGUE, EntityRow.birth_epoch == ctx.epoch)
        .order_by(EntityRow.id)
    )
    seen: set[int] = set()
    shaken = 0
    cults = await canon(ctx.session, [EntityType.CULT])
    for plague in list(plagues):
        if (stat(plague, "severity") or 0) < settings.plague_severity:
            continue
        _, struck = await disaster_toll(ctx, plague)
        name = plain_name(plague.name)
        for community in struck:
            if shaken >= settings.plague_cap:
                return shaken
            if community.id in seen or community.entity_type is EntityType.FACTION:
                continue
            seen.add(community.id)
            current = await living_patron(ctx.session, community)
            roll = ctx.rng(seed_of("plague_faith", plague.id, community.id)).random() * 100
            turned_to = await _plague_god(ctx, community, current, plague)
            if (
                turned_to is not None
                and roll < settings.plague_turn_chance
                and await change_religion(ctx.session, community, turned_to.id, ctx.epoch, f"turned to it during {name}", syncretic=current is not None)
            ):
                text = f"During {name}, {community.name} turned to {turned_to.name}."
                await note(ctx, text, key="remembrance.plague_turned", ids=[plague.id, community.id], son_id=turned_to.id)
            elif roll < settings.plague_turn_chance + settings.plague_estrange_chance:
                shift_stat(community, "piety", -settings.plague_piety_loss)
                await add_flag(ctx.session, community.id, EntityFlag.ESTRANGED_BY_PLAGUE, ctx.epoch)
                god = current.name if current is not None else "the sky"
                await note(
                    ctx,
                    f"While the dead of {name} were buried, {community.name} turned away from {god}; the temples emptied.",
                    key="remembrance.plague_estranged",
                    ids=[plague.id, community.id],
                    son_id=current.id if current is not None else None,
                )
            else:
                shift_stat(community, "piety", settings.plague_piety_gain)
                god = current.name if current is not None else "its prayers"
                await note(
                    ctx,
                    f"Facing {name}, {community.name} clung tighter to {god}.",
                    key="remembrance.plague_clung",
                    ids=[plague.id, community.id],
                    son_id=current.id if current is not None else None,
                )
            for cult in cults:
                if community.id in (cult.location_id, cult.id):
                    low, high = headcount_bounds(ctx.rules, cult)
                    set_stats(cult, followers=clamp_int((stat(cult, "followers") or low) * (1 + settings.plague_followers_pct / 100), low, high))
            shaken += 1
    return shaken


@reads(
    "event.severity",
    "people.piety",
    "people.population",
    "people.prosperity",
    "people.wealth",
    "settlement.piety",
    "settlement.population",
    "settlement.prosperity",
    "table.bonds",
    "table.community_relations",
    "table.culture_values",
    "table.entity_flags",
    "table.epoch_year_cursors",
    "table.memories",
    "table.minds",
    "table.name_registry",
    "table.nodes",
    "table.personality_values",
    "table.traits",
    "table.war_sides",
    "table.wars",
)
@writes(
    "people.piety",
    "settlement.piety",
    "table.bonds",
    "table.chronicle",
    "table.chronicle_entities",
    "table.community_relations",
    "table.entities",
    "table.entity_flags",
    "table.epoch_year_cursors",
    "table.incident_participants",
    "table.incidents",
    "table.memories",
    "table.name_registry",
)
async def remembrance(ctx: TickContext) -> None:
    cap = ctx.rules.remembrance.epoch_cap
    made = await wars_remembered(ctx, cap)
    made += await disasters_remembered(ctx, cap - made)
    made += await heroes_remembered(ctx, cap - made)
    ctx.count("memorials", made)
    ctx.count("plague_shaken", await plague_faith(ctx))
    await ctx.session.flush()


async def commemorate(ctx: TickContext, target_id: int, form: MemorialForm) -> list[int]:
    target = await ctx.session.get(EntityRow, target_id)
    if target is None:
        raise ValidationFailedError("No such record to remember.")
    if target.entity_type is EntityType.MORTAL and target.status is EntityStatus.DEAD:
        return await remember_dead(ctx, target, form if form in (MemorialForm.MONUMENT, MemorialForm.LAMENT, MemorialForm.EPIC) else MemorialForm.TALE)
    if target.entity_type is EntityType.EVENT and target.engine_kind in DISASTER_KINDS:
        return await remember_disaster(ctx, target, form if form in (MemorialForm.MONUMENT, MemorialForm.TRADITION) else MemorialForm.TALE)
    if target.entity_type is EntityType.EVENT and target.engine_kind in WAR_KINDS:
        war_event_id = target.id
        if target.engine_kind is not EngineKind.WAR:
            parent = await ctx.session.scalar(
                select(BondRow.target_node_id).where(BondRow.source_node_id == target.id, BondRow.kind == BondKind.PART_OF).limit(1)
            )
            war_event_id = parent if parent is not None else target.id
        war = await ctx.session.scalar(select(WarRow).where(WarRow.event_entity_id == war_event_id))
        if war is None:
            raise ValidationFailedError(f"{target.name} belongs to no war.")
        memory = await remember_war(ctx, war, MemorialForm.EPIC if form is MemorialForm.TALE else form)
        if war_event_id != target.id:
            for record_id in memory.ids:
                await BondRepository(ctx.session).connect(BondDraft(record_id, target.id, BondKind.TELLS_OF, ctx.epoch, "remembers"))
        if not memory.ids:
            raise ValidationFailedError(f"No place was found to raise a memorial for {target.name}.")
        return memory.ids
    raise ValidationFailedError("Only a war, battle, siege, disaster or a dead mortal can be remembered.")


PHASES = (Phase("remembrance", remembrance),)
