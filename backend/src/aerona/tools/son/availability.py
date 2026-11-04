from collections.abc import Callable
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.stars import STAR_TYPE_LABELS
from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.tables.celestial import StarRow, WorldRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.foreign_gods import ForeignGodRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.foreign_god import ForeignGodStatus
from aerona.domain.enums.son import SonStatus
from aerona.domain.enums.world import EXTINGUISHED_STAR_TYPES, SonDistribution
from aerona.prompts import SonToolId
from aerona.prompts.contexts.cosmos import StarLine
from aerona.rules.registry import Rules

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
    )


Condition = Callable[[Rules, SonWorldState], bool]

CONDITIONS: dict[SonToolId, Condition] = {
    T.CHOOSE_ANCHOR: lambda rules, _state: rules.son_tools.anchor_per_epoch > 0,
    T.COIN_WORDS: lambda rules, _state: rules.son_tools.coin_word_per_epoch > 0,
    T.CALL_SIBLING: lambda rules, _state: rules.son_tools.sibling_message_per_epoch > 0,
    T.GIVE_GIFT: lambda rules, _state: rules.son_tools.gift_per_epoch > 0,
    T.PRAY_TO_FATHER: lambda rules, _state: rules.son_tools.prayer_per_epoch > 0,
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
    T.STITCH_LEAK: lambda rules, _state: rules.son_tools.stitch_per_epoch > 0,
    T.BARGAIN_WITH_OUTSIDER: lambda rules, state: state.outer_being and rules.son_tools.outer_bargain_per_epoch > 0,
}


def condition_holds(tool_id: SonToolId, rules: Rules, state: SonWorldState) -> bool:
    condition = CONDITIONS.get(tool_id)
    return condition is None or condition(rules, state)


async def star_lines(session: AsyncSession) -> list[StarLine]:
    stars = await session.scalars(select(StarRow).order_by(StarRow.id))
    return [StarLine(id=star.id, name=star.name, type_label=STAR_TYPE_LABELS[star.star_type]) for star in stars]
