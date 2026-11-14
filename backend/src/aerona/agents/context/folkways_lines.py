from sqlalchemy import select

from aerona.agents.context.cycle_lines import named, words
from aerona.agents.context.scope import Scope
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.folkways import (
    AccusationRow,
    BiasWeightRow,
    CharmRow,
    LuckBeliefRow,
    MishapRow,
    NutritionScoreRow,
    PurityRankRow,
    PurityRow,
    WitchHuntRow,
)
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.folkways import AccusationOutcome, PurityState
from aerona.engine.body.customs import people_of
from aerona.engine.folkways.biases import MIDDLE
from aerona.engine.sacred.places import town_of

LIST_LINES = 3
STRONG = 20


async def body_lines(scope: Scope, me: EntityRow) -> list[str]:
    found: list[str] = []
    score = await scope.session.get(NutritionScoreRow, me.id)
    if score is not None:
        lack = f", short of {words(score.deficiency.value)}" if score.deficiency is not None else ""
        found.append(f"your nutrition: {score.score} of 100{lack}")
    purity = await scope.session.get(PurityRow, me.id)
    if purity is not None:
        rank = await scope.session.get(PurityRankRow, purity.rank_id) if purity.rank_id is not None else None
        if rank is not None:
            found.append(f"your rank: {rank.name}")
        if purity.state is not PurityState.PURE:
            source = f" by {words(purity.source.value)}" if purity.source is not None else ""
            found.append(f"your purity: {purity.state.value}{source}; gatherings and unions are closed to you until you purify")
    return found


async def luck_lines(scope: Scope, me: EntityRow) -> list[str]:
    found: list[str] = []
    folk = await people_of(scope.session, me)
    if folk is not None:
        for belief in await scope.session.scalars(
            select(LuckBeliefRow).where(LuckBeliefRow.people_entity_id == folk.id).order_by(LuckBeliefRow.id).limit(LIST_LINES)
        ):
            found.append(f"your people hold {belief.name} for {belief.reach.value}")
    owned = await scope.session.scalars(
        select(CharmRow).where(CharmRow.item_entity_id.in_(select(EntityRow.id).where(EntityRow.location_id == me.id))).limit(LIST_LINES)
    )
    for charm in owned:
        found.append(f"you carry {await named(scope, charm.item_entity_id)}, a charm of {charm.power.value}")
    town = await town_of(scope.session, me)
    if town is not None:
        hunt = await scope.session.scalar(select(WitchHuntRow).where(WitchHuntRow.settlement_entity_id == town.id, WitchHuntRow.ended_epoch.is_(None)))
        if hunt is not None:
            found.append(f"a witch hunt burns in {town.name} at fervour {hunt.fervour}")
        for mishap in await scope.session.scalars(
            select(MishapRow).where(MishapRow.settlement_entity_id == town.id).order_by(MishapRow.id.desc()).limit(LIST_LINES)
        ):
            blamed = f", blamed on {words(mishap.attribution.value)}" if mishap.attribution is not None else ""
            found.append(f"{town.name} suffered {words(mishap.kind.value)} in epoch {mishap.epoch}{blamed}")
    accused = await scope.session.scalar(
        select(AccusationRow).where(AccusationRow.accused_node_id == me.id, AccusationRow.outcome == AccusationOutcome.PENDING).limit(1)
    )
    if accused is not None:
        found.append("you stand accused of witchcraft and await trial")
    return found


async def mortal_folkways_lines(scope: Scope, me: EntityRow) -> list[str]:
    return [*await body_lines(scope, me), *await luck_lines(scope, me)]


async def son_folkways_lines(scope: Scope, son: SonRow) -> list[str]:
    found: list[str] = []
    for row in await scope.session.scalars(select(BiasWeightRow).where(BiasWeightRow.holder_node_id == son.id).order_by(BiasWeightRow.bias)):
        if abs(row.weight - MIDDLE) >= STRONG:
            lean = "strong" if row.weight > MIDDLE else "faint"
            found.append(f"your {words(row.bias.value)} runs {lean} ({row.weight})")
    if son.current_world_id is None:
        return found
    towns = select(EntityRow.id).where(EntityRow.world_id == son.current_world_id)
    for hunt in await scope.session.scalars(
        select(WitchHuntRow).where(WitchHuntRow.settlement_entity_id.in_(towns), WitchHuntRow.ended_epoch.is_(None)).order_by(WitchHuntRow.id).limit(LIST_LINES)
    ):
        found.append(f"a witch hunt burns in {await named(scope, hunt.settlement_entity_id)} at fervour {hunt.fervour}")
    for mishap in await scope.session.scalars(
        select(MishapRow)
        .where(MishapRow.settlement_entity_id.in_(towns), MishapRow.epoch >= scope.cosmos.epoch - 1)
        .order_by(MishapRow.id.desc())
        .limit(LIST_LINES)
    ):
        blamed = f"; its folk blame {words(mishap.attribution.value)}" if mishap.attribution is not None else ""
        found.append(f"misfortune {mishap.id}: {await named(scope, mishap.settlement_entity_id)} suffered {words(mishap.kind.value)}{blamed}")
    return found
