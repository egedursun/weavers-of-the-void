from collections.abc import Callable, Mapping
from dataclasses import dataclass, field

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.stars import STAR_TYPE_LABELS
from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.tables.celestial import StarRow, WorldRow
from aerona.db.tables.cosmography import DimensionRow, RiftRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.foreign_gods import ForeignGodRow
from aerona.db.tables.physics import ImpactEventRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.agent import TurnCounter
from aerona.domain.enums.cosmography import OPEN_RIFT_STATES
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.foreign_god import ForeignGodStatus
from aerona.domain.enums.physics import ImpactOutcome
from aerona.domain.enums.son import SonStatus
from aerona.domain.enums.world import EXTINGUISHED_STAR_TYPES, SonDistribution
from aerona.prompts import SonToolId
from aerona.prompts.contexts.cosmos import StarLine
from aerona.rules.registry import Rules
from aerona.tools.framework.turn import counter_value

T = SonToolId


@dataclass(frozen=True)
class SonWorldState:
    world_count: int
    automatic_distribution: bool
    dead_sibling: bool
    dead_star: bool
    free_spirit: bool
    contacted_foreign_god: bool
    outer_being: bool
    open_rift: bool = False
    cosmic_being: bool = False
    phenomenon: bool = False
    dimensions: int = 0
    pending_impact: bool = False
    spent: Mapping[TurnCounter, int] = field(default_factory=dict)


async def world_state(session: AsyncSession, son: SonRow) -> SonWorldState:
    cosmos = await CosmosRepository(session).get()
    worlds = int(await session.scalar(select(func.count(WorldRow.id))) or 0)
    dead_sibling = await session.scalar(select(SonRow.id).where(SonRow.status == SonStatus.DEAD, SonRow.id != son.id).limit(1)) is not None
    dead_star = await session.scalar(select(StarRow.id).where(StarRow.star_type.in_(list(EXTINGUISHED_STAR_TYPES))).limit(1)) is not None
    spirit = await session.scalar(select(EntityRow.id).where(EntityRow.entity_type == EntityType.SPIRIT, EntityRow.status == EntityStatus.CANON).limit(1))
    god = await session.scalar(select(ForeignGodRow.id).where(ForeignGodRow.contacted.is_(True), ForeignGodRow.status == ForeignGodStatus.AWAKE).limit(1))
    outer = await session.scalar(select(EntityRow.id).where(EntityRow.entity_type == EntityType.OUTER_BEING, EntityRow.status == EntityStatus.CANON).limit(1))
    return SonWorldState(
        world_count=worlds,
        automatic_distribution=cosmos is None or cosmos.son_distribution is SonDistribution.AUTO,
        dead_sibling=dead_sibling,
        dead_star=dead_star,
        free_spirit=spirit is not None,
        contacted_foreign_god=god is not None,
        outer_being=outer is not None,
        open_rift=await session.scalar(select(RiftRow.id).where(RiftRow.state.in_(list(OPEN_RIFT_STATES))).limit(1)) is not None,
        cosmic_being=await session.scalar(
            select(EntityRow.id).where(EntityRow.entity_type == EntityType.COSMIC_BEING, EntityRow.status == EntityStatus.CANON).limit(1)
        )
        is not None,
        phenomenon=await session.scalar(
            select(EntityRow.id).where(EntityRow.entity_type == EntityType.PHENOMENON, EntityRow.status == EntityStatus.CANON).limit(1)
        )
        is not None,
        dimensions=int(await session.scalar(select(func.count(DimensionRow.id))) or 0),
        pending_impact=await session.scalar(select(ImpactEventRow.id).where(ImpactEventRow.outcome == ImpactOutcome.PENDING).limit(1)) is not None,
        spent={counter: await counter_value(session, son.id, cosmos.epoch, counter) for counter, _cap in AGE_LIMITS.values()} if cosmos is not None else {},
    )


Condition = Callable[[Rules, SonWorldState], bool]
C = TurnCounter
AGE_LIMITS: dict[SonToolId, tuple[TurnCounter, Callable[[Rules], int]]] = {
    SonToolId.REORDER_SEASONS: (C.SEASON_ORDER, lambda rules: rules.son_tools.reorder_seasons_per_epoch),
    SonToolId.SHAPE_WEATHER: (C.WEATHER_SHAPING, lambda rules: rules.son_tools.shape_weather_per_epoch),
    SonToolId.DECLARE_HOLY_WORLD: (C.HOLY_WORLD, lambda rules: rules.son_tools.holy_world_per_epoch),
    SonToolId.SEAL_LEAK: (C.LEAK_STITCHED, lambda rules: rules.son_tools.seal_per_epoch),
    SonToolId.BARGAIN_WITH_OUTSIDER: (C.OUTER_BARGAIN, lambda rules: rules.son_tools.outer_bargain_per_epoch),
    SonToolId.MAKE_BOND: (C.NARRATIVE_BONDS, lambda rules: rules.son_tools.link_per_epoch),
    SonToolId.TAKE_LIFE: (C.TAKE_LIFE, lambda rules: rules.death.take_life_per_epoch),
    SonToolId.CALL_SIBLING: (C.SIBLING_MESSAGES, lambda rules: rules.son_tools.sibling_message_per_epoch),
    SonToolId.GIVE_GIFT: (C.GIFTS, lambda rules: rules.son_tools.gift_per_epoch),
    SonToolId.COIN_WORDS: (C.WORDS_COINED, lambda rules: rules.son_tools.coin_word_per_epoch),
    SonToolId.CHOOSE_ANCHOR: (C.ANCHOR_CHOSEN, lambda rules: rules.son_tools.anchor_per_epoch),
    SonToolId.PRAY_TO_CREATOR: (C.PRAYERS, lambda rules: rules.son_tools.prayer_per_epoch),
}


def within_age_limit(tool_id: SonToolId, rules: Rules, state: SonWorldState) -> bool:
    limit = AGE_LIMITS.get(tool_id)
    return limit is None or state.spent.get(limit[0], 0) < limit[1](rules)


CONDITIONS: dict[SonToolId, Condition] = {
    T.CHOOSE_ANCHOR: lambda rules, _state: rules.son_tools.anchor_per_epoch > 0,
    T.COIN_WORDS: lambda rules, _state: rules.son_tools.coin_word_per_epoch > 0,
    T.CALL_SIBLING: lambda rules, _state: rules.son_tools.sibling_message_per_epoch > 0,
    T.GIVE_GIFT: lambda rules, _state: rules.son_tools.gift_per_epoch > 0,
    T.PRAY_TO_CREATOR: lambda rules, _state: rules.son_tools.prayer_per_epoch > 0,
    T.MAKE_BOND: lambda rules, _state: rules.son_tools.link_per_epoch > 0,
    T.TAKE_LIFE: lambda rules, _state: rules.death.take_life_per_epoch > 0,
    T.RESURRECT_SIBLING: lambda rules, state: rules.death.sibling_intrigues_per_epoch > 0 and state.dead_sibling,
    T.SCATTER_BONES: lambda rules, state: rules.death.sibling_intrigues_per_epoch > 0 and state.dead_sibling,
    T.MOVE_TO_WORLD: lambda _rules, state: state.world_count >= 2 and state.automatic_distribution,
    T.DECLARE_HOLY_WORLD: lambda rules, state: state.world_count >= 2 and rules.son_tools.holy_world_per_epoch > 0,
    T.MAKE_INTERWORLD_TREATY: lambda _rules, state: state.world_count >= 2,
    T.REKINDLE_STAR: lambda _rules, state: state.dead_star,
    T.BIND_SPIRIT: lambda _rules, state: state.free_spirit,
    T.OPEN_REBIRTH_GATE: lambda _rules, state: state.free_spirit,
    T.TALK_TO_FOREIGN_GOD: lambda _rules, state: state.contacted_foreign_god,
    T.WAR_ON_FOREIGN_GOD: lambda _rules, state: state.contacted_foreign_god,
    T.SEAL_LEAK: lambda rules, _state: rules.son_tools.seal_per_epoch > 0,
    T.BARGAIN_WITH_OUTSIDER: lambda rules, state: state.outer_being and rules.son_tools.outer_bargain_per_epoch > 0,
    T.OPEN_RIFT: lambda _rules, state: state.dimensions >= 2,
    T.DEFLECT_IMPACT: lambda _rules, state: state.pending_impact,
    T.SEAL_RIFT: lambda _rules, state: state.open_rift,
    T.BIND_COSMIC_BEING: lambda _rules, state: state.cosmic_being,
    T.BANISH_COSMIC_BEING: lambda _rules, state: state.cosmic_being,
    T.CONTAIN_PHENOMENON: lambda _rules, state: state.phenomenon,
    T.RULE_DIMENSION: lambda _rules, state: state.dimensions >= 1,
    T.STIR_DIMENSION: lambda _rules, state: state.dimensions >= 1,
    T.BIND_LAW_ACROSS_DIMENSION: lambda _rules, state: state.dimensions >= 1,
    T.OPEN_BREACH: lambda _rules, state: state.outer_being,
    T.STRIKE_BEING: lambda _rules, state: state.outer_being or state.cosmic_being,
    T.OPEN_ROAD: lambda _rules, state: state.world_count >= 2,
}


def condition_holds(tool_id: SonToolId, rules: Rules, state: SonWorldState) -> bool:
    if not within_age_limit(tool_id, rules, state):
        return False
    condition = CONDITIONS.get(tool_id)
    return condition is None or condition(rules, state)


async def star_lines(session: AsyncSession) -> list[StarLine]:
    stars = await session.scalars(select(StarRow).order_by(StarRow.id))
    return [StarLine(id=star.id, name=star.name, type_label=STAR_TYPE_LABELS[star.star_type]) for star in stars]
