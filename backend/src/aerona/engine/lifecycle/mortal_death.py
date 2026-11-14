from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.stats import max_essence
from aerona.catalog.worlds import WORLD_TYPES
from aerona.constants.schema import SINGLETON_ID
from aerona.constants.units import PERCENT
from aerona.core.errors import ValidationFailedError
from aerona.core.grammar import agree, several
from aerona.db.repositories.chronicle import CAUSE_SCOPE
from aerona.db.repositories.entities import EntityRepository
from aerona.db.repositories.nodes import NodeRepository
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.cosmos import CosmosRow
from aerona.db.tables.culture import ItemProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.crafts import InsuranceCover
from aerona.domain.enums.culture import ItemDeed
from aerona.domain.enums.divine import DomainHook
from aerona.domain.enums.entity import COMMUNITY_TYPES, EntityFlag, EntityOrigin, EntityStatus, EntityType
from aerona.domain.enums.faith import SpiritAlignment
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.mortal import DeathCause
from aerona.domain.enums.node import NodeKind
from aerona.domain.models.entity_stats import SpiritStats, TraditionStats
from aerona.engine.context import TickContext
from aerona.engine.crafts.cover import claim
from aerona.engine.crafts.heirs import pass_rights
from aerona.engine.demography.rites import mourning_factor, rite_of, spirit_factor
from aerona.engine.demography.rites import restless as restless_by_rite
from aerona.engine.divine.wounds import avatar_slain
from aerona.engine.faith.judgement import profile_for
from aerona.engine.folkways.wrongs import wrongly_condemned
from aerona.engine.interconnect.causes import killing_incident
from aerona.engine.lifecycle.aging import immortal, raise_lifespan_to_death_age
from aerona.engine.lifecycle.succession import dynasty_root, pass_rule
from aerona.engine.lore.history import record
from aerona.engine.mind.ethics import killing_act
from aerona.engine.mind.grief import bereave
from aerona.engine.mind.hooks import judged
from aerona.engine.mind.memories import inherit_memories, mourn
from aerona.engine.mortal.death import record_end
from aerona.engine.mortal.kin import children_of
from aerona.engine.notes import note
from aerona.engine.polity.law_effects import bequest_order
from aerona.engine.primitives.naming import seed_of
from aerona.engine.primitives.numbers import clamp_int, scaled_cap
from aerona.engine.primitives.queries import active_bonds, close, connect, count_communities, living_entity, living_sons
from aerona.engine.primitives.records import RecordSpec, append_sentence, open_record, sweep_dead_bonds
from aerona.engine.primitives.stats import set_stats, stat
from aerona.engine.relations.passions import bereaved
from aerona.engine.sacred.guards import unrest_shift

LIVING_DEATH_STATUSES = frozenset({EntityStatus.CANON, EntityStatus.FULFILLED})
RESTLESS_SPIRIT_SUBTYPE = "restless spirit"
ANCESTOR_SPIRIT_SUBTYPE = "ancestor spirit"
MOURNING_SUBTYPE = "mourning rite"
SPIRIT_SUBTYPES = (RESTLESS_SPIRIT_SUBTYPE, ANCESTOR_SPIRIT_SUBTYPE)
MOURNING_HOME_TYPES = frozenset({EntityType.SETTLEMENT, EntityType.PEOPLE})
DEFAULT_CAUSE = "died"


@dataclass(frozen=True)
class DeathResult:
    entity: EntityRow
    heir: EntityRow | None
    text: str


async def world_year(session: AsyncSession) -> int:
    cosmos = await session.get(CosmosRow, SINGLETON_ID)
    return cosmos.epoch_start_year if cosmos is not None else 0


async def die(
    ctx: TickContext,
    mortal: EntityRow,
    *,
    cause: str = DEFAULT_CAUSE,
    manner: DeathCause | None = None,
    killer_id: int | None = None,
    year: int | None = None,
    natural: bool = False,
    forced: bool = False,
    event_id: int | None = None,
) -> DeathResult | None:
    session = ctx.session
    if mortal.entity_type is not EntityType.MORTAL or mortal.status not in LIVING_DEATH_STATUSES:
        return None
    flags = await EntityRepository(session).flags(mortal.id)
    if not forced and immortal(flags):
        return None
    rng = ctx.rng(seed_of("death", mortal.id))
    death_year = year if year is not None else await world_year(session) + rng.die(ctx.rules.time.years_per_epoch) - 1
    set_stats(mortal, death_year=death_year)
    age = stat(mortal, "age")
    age_text = str(age) if age is not None else "unknown"
    fate = (
        f"Epoch {ctx.epoch}, world year {death_year}: died at age {age_text}."
        if natural
        else f"Epoch {ctx.epoch}, world year {death_year}: {cause} (age {age_text})."
    )
    ending = f"Died in epoch {ctx.epoch}, at age {age_text}." if natural else f"In epoch {ctx.epoch} {cause} (age {age_text})."
    mortal.description = append_sentence(mortal.description, ending)
    await EntityRepository(session).set_status(mortal, EntityStatus.DEAD, ctx.epoch, append_sentence(mortal.fate_note, fate))
    if event_id is not None:
        mortal.death_event_entity_id = event_id
    killer_kind = await NodeRepository(session).kind_of(killer_id) if killer_id is not None else None
    if killer_id is not None and killer_kind is not None:
        await connect(session, killer_id, mortal.id, BondKind.KILLED, ctx.epoch, description=cause)
    await record_end(ctx, mortal, manner or (DeathCause.OLD_AGE if natural else DeathCause.UNKNOWN))
    await avatar_slain(ctx, mortal.id)
    ctx.count("memories_inherited", await mourn(session, ctx.rules, mortal, killer_id, ctx.epoch))
    ctx.count("griefs", await bereave(ctx, mortal, killer_id))
    ctx.count("passions_bereaved", await bereaved(ctx, mortal, killer_id))
    act = await killing_act(session, mortal, killer_id, manner)
    if act is not None:
        await judged(ctx, killer_id or mortal.id, mortal.id, act)
    heir = await pass_rule(ctx, mortal)
    if heir is not None:
        await inherit_memories(session, ctx.rules, mortal, [heir.id], ctx.epoch)
        ctx.count("rights_inherited", await pass_rights(session, mortal.id, heir.id, ctx.epoch))
    if await claim(session, mortal.id, InsuranceCover.LIFE, ctx.rules.insurance.life_payout):
        ctx.count("lives_insured_paid")
    if natural:
        tail = "; an heir took their place" if heir is not None else ". Their name now lives only in the tales"
        text = f"{mortal.name} died at age {age_text}{tail}."
    else:
        text = f"{mortal.name} {cause}{'; an heir took their place' if heir is not None else ''}."
    ids = [mortal.id] + ([heir.id] if heir is not None else []) + ([killer_id] if killer_id is not None and killer_kind is NodeKind.ENTITY else [])
    son_id = killer_id if killer_kind is NodeKind.SON else mortal.creator_son_id
    roles = {mortal.id: IncidentRole.TARGET, **({killer_id: IncidentRole.ACTOR} if killer_id is not None else {})}
    cause_id = None if natural or killer_id is None or CAUSE_SCOPE.get() is not None else await killing_incident(ctx.session, mortal.id, killer_id)
    key = "mortal.death.natural" if natural else "mortal.death.cause"
    await note(ctx, text, key=key, ids=ids, son_id=son_id, roles=roles, cause_incident_id=cause_id)
    await after_death(ctx, mortal)
    await sweep_dead_bonds(session, ctx.epoch, mortal.id)
    if await raise_lifespan_to_death_age(session, ctx.rules, mortal):
        ctx.count("lifespans_raised")
    ctx.count("deaths")
    return DeathResult(mortal, heir, text)


async def underworld_of(session: AsyncSession, mortal: EntityRow) -> EntityRow | None:
    statement = select(EntityRow).where(
        EntityRow.entity_type == EntityType.REGION,
        EntityRow.status == EntityStatus.CANON,
        EntityRow.is_underworld.is_(True),
        EntityRow.world_id == mortal.world_id,
    )
    found: EntityRow | None = await session.scalar(statement.order_by(EntityRow.id).limit(1))
    if found is not None:
        return found
    world = await session.get(WorldRow, mortal.world_id)
    if world is None or not WORLD_TYPES[world.world_type].realm_of_dead:
        return None
    region: EntityRow | None = await session.scalar(
        select(EntityRow)
        .where(EntityRow.entity_type == EntityType.REGION, EntityRow.status == EntityStatus.CANON, EntityRow.world_id == mortal.world_id)
        .order_by(EntityRow.id)
        .limit(1)
    )
    return region


async def _reward_death_domains(ctx: TickContext) -> None:
    effects = ctx.rules.world_effects
    for son in await living_sons(ctx.session):
        toll = await ctx.god_share(son.id, DomainHook.DEATH_TOLL)
        if toll <= 0:
            continue
        son.essence = min(max_essence(ctx.rules, son.might), son.essence + round(effects.death_domain_essence * toll))
        son.existence = min(PERCENT, son.existence + round(effects.death_domain_existence * toll))


async def _bequeath(ctx: TickContext, mortal: EntityRow) -> None:
    session = ctx.session
    items = await active_bonds(session, [BondKind.OWNS], sources=[mortal.id])
    if not items:
        return
    children: list[EntityRow] = []
    for child_id in reversed(await children_of(session, mortal.id)):
        child = await living_entity(session, child_id)
        if child is not None:
            children.append(child)
    heirs = await bequest_order(session, mortal, children)
    receiver: EntityRow | None = heirs[0] if heirs else None
    if receiver is None:
        place = await living_entity(session, mortal.location_id)
        receiver = place if place is not None and place.entity_type in COMMUNITY_TYPES else None
    for index, bond in enumerate(items):
        receiver = heirs[index % len(heirs)] if len(heirs) > 1 else receiver
        await close(session, bond, ctx.epoch, "inheritance")
        if heirs:
            taker = heirs[index % len(heirs)]
            await connect(session, taker.id, bond.target_node_id, BondKind.OWNS, ctx.epoch, description=f"inherited from {mortal.name}")
            if await session.get(ItemProfileRow, bond.target_node_id) is not None:
                record(ctx, bond.target_node_id, ItemDeed.OWNED, taker.id, f"an heirloom of {mortal.name}")
    item_ids = [bond.target_node_id for bond in items]
    if receiver is None:
        for item_id in item_ids:
            if await session.get(ItemProfileRow, item_id) is not None:
                record(ctx, item_id, ItemDeed.BURIAL, mortal.id, f"laid in the grave of {mortal.name}")
    if receiver is not None:
        text = f"{several(len(items), 'item', 'items')} of {mortal.name} passed to {', '.join(heir.name for heir in heirs)}."
        ids = [mortal.id, *item_ids, *(heir.id for heir in heirs)]
    else:
        text = (
            f"{several(len(items), 'item', 'items')} of {mortal.name} {agree(len(items), 'was', 'were')} left ownerless; "
            f"{agree(len(items), 'it waits', 'they wait')} in the grave or on the battlefield."
        )
        ids = [mortal.id, *item_ids]
    await note(ctx, text, key="mortal.inheritance", ids=ids)


async def _born_this_epoch(session: AsyncSession, entity_type: EntityType, subtypes: tuple[str, ...], epoch: int) -> int:
    statement = (
        select(func.count())
        .select_from(EntityRow)
        .where(
            EntityRow.entity_type == entity_type,
            EntityRow.origin == EntityOrigin.ENGINE,
            EntityRow.birth_epoch == epoch,
            EntityRow.subtype.in_(list(subtypes)),
        )
    )
    return int(await session.scalar(statement) or 0)


async def _spirits_at(session: AsyncSession, place_id: int | None) -> int:
    if place_id is None:
        return 0
    statement = (
        select(func.count())
        .select_from(EntityRow)
        .where(EntityRow.entity_type == EntityType.SPIRIT, EntityRow.status == EntityStatus.CANON, EntityRow.location_id == place_id)
    )
    return int(await session.scalar(statement) or 0)


async def _is_famous(ctx: TickContext, mortal: EntityRow, flags: set[EntityFlag]) -> bool:
    charisma = stat(mortal, "charisma")
    if charisma is not None and charisma >= ctx.rules.world_effects.famous_min_charisma:
        return True
    if EntityFlag.CHOSEN in flags:
        return True
    return bool(await active_bonds(ctx.session, [BondKind.KILLED], sources=[mortal.id]))


async def _leave_spirit(ctx: TickContext, mortal: EntityRow, underworld: EntityRow | None) -> None:
    session = ctx.session
    effects = ctx.rules.world_effects
    rng = ctx.rng(seed_of("spirit", mortal.id))
    place_id = underworld.id if underworld is not None else mortal.location_id
    rite = await rite_of(session, mortal)
    if not rng.chance(min(PERCENT, ctx.rules.world_engine.famous_spirit_chance * spirit_factor(ctx.rules, rite))):
        return
    if await _spirits_at(session, place_id) >= ctx.rules.deep_world.spirits_per_place_cap:
        return
    if await _born_this_epoch(session, EntityType.SPIRIT, SPIRIT_SUBTYPES, ctx.epoch) >= scaled_cap(
        effects.afterdeath_cap, effects.afterdeath_cap_community_divisor, await count_communities(session)
    ):
        return
    murdered = bool(await active_bonds(session, [BondKind.KILLED], targets=[mortal.id]))
    wronged = ctx.rules.witchcraft.wrongful_unrest if await wrongly_condemned(session, mortal.id) else 0
    base = clamp_int((effects.spirit_unrest_murdered if murdered else effects.spirit_unrest_natural) + await unrest_shift(ctx, mortal) + wronged, 0, PERCENT)
    restless = restless_by_rite(ctx.rules, rite, base, effects.spirit_restless_threshold)
    strength = stat(mortal, "strength")
    origin = f"refused to descend to {underworld.name} or returned from there" if underworld is not None else "returned from the world"
    spirit = await open_record(
        session,
        ctx.epoch,
        RecordSpec(
            entity_type=EntityType.SPIRIT,
            name=f"Spirit of {mortal.name}",
            body=f"After {mortal.name} died, their spirit {origin}.",
            stats=SpiritStats(
                strength=clamp_int(
                    (strength if strength is not None else effects.inheritance_default_stat) / effects.spirit_strength_divisor + effects.spirit_strength_bonus,
                    0,
                    PERCENT,
                ),
                unrest=clamp_int(base + rng.die(effects.spirit_unrest_die), 0, PERCENT),
            ),
            power=max(effects.split_min_power, mortal.power_level - 1),
            location_id=place_id,
            world_id=mortal.world_id,
            subtype=RESTLESS_SPIRIT_SUBTYPE if restless else ANCESTOR_SPIRIT_SUBTYPE,
        ),
    )
    await connect(session, spirit.id, mortal.id, BondKind.DESCENDS_FROM, ctx.epoch, description="their spirit")
    profile = await profile_for(ctx, spirit, mortal)
    profile.alignment = SpiritAlignment.VENGEFUL if restless else SpiritAlignment.GUARDIAN
    manner = "as a restless spirit" if restless else "among the ancestors"
    await note(ctx, f"The spirit of {mortal.name} found no rest; it wanders {manner}.", key="mortal.spirit", ids=[mortal.id, spirit.id])


async def _start_mourning(ctx: TickContext, mortal: EntityRow) -> None:
    session = ctx.session
    effects = ctx.rules.world_effects
    place = await living_entity(session, mortal.location_id)
    if place is None:
        return
    rng = ctx.rng(seed_of("mourning", mortal.id))
    if not rng.chance(min(PERCENT, ctx.rules.world_engine.mourning_tradition_chance * mourning_factor(ctx.rules, await rite_of(session, mortal)))):
        return
    if await _born_this_epoch(session, EntityType.TRADITION, (MOURNING_SUBTYPE,), ctx.epoch) >= scaled_cap(
        effects.afterdeath_cap, effects.afterdeath_cap_community_divisor, await count_communities(session)
    ):
        return
    tradition = await open_record(
        session,
        ctx.epoch,
        RecordSpec(
            entity_type=EntityType.TRADITION,
            name=f"Mourning of {dynasty_root(mortal.name)}",
            body=f"After the death of {mortal.name}, the people of {place.name} began to commemorate them every year.",
            stats=TraditionStats(spread=effects.mourning_spread, rigidity=effects.mourning_rigidity),
            power=effects.mourning_power,
            world_id=mortal.world_id,
            subtype=MOURNING_SUBTYPE,
        ),
    )
    await connect(session, tradition.id, mortal.id, BondKind.TELLS_OF, ctx.epoch)
    if place.entity_type in MOURNING_HOME_TYPES:
        await connect(session, place.id, tradition.id, BondKind.CELEBRATES, ctx.epoch)
    await note(ctx, f"{place.name} began a mourning tradition for {mortal.name}.", key="mortal.mourning", ids=[mortal.id, place.id, tradition.id])


async def after_death(ctx: TickContext, mortal: EntityRow) -> None:
    underworld = await underworld_of(ctx.session, mortal)
    if underworld is not None:
        await connect(ctx.session, mortal.id, underworld.id, BondKind.SOUL_DESCENDED_TO, ctx.epoch, description="the soul descended there")
    await _reward_death_domains(ctx)
    await _bequeath(ctx, mortal)
    flags = await EntityRepository(ctx.session).flags(mortal.id)
    if not await _is_famous(ctx, mortal, flags):
        return
    await _leave_spirit(ctx, mortal, underworld)
    await _start_mourning(ctx, mortal)


async def force_death(ctx: TickContext, mortal_id: int, cause: str, manner: DeathCause = DeathCause.DIVINE) -> DeathResult:
    mortal = await living_entity(ctx.session, mortal_id)
    if mortal is None or mortal.entity_type is not EntityType.MORTAL:
        raise ValidationFailedError("Only a living, named mortal's life can be taken.")
    result = await die(ctx, mortal, cause=cause, manner=manner, forced=True)
    if result is None:
        raise ValidationFailedError("Only a living, named mortal's life can be taken.")
    return result
