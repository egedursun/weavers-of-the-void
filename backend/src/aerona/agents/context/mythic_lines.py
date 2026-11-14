from collections import Counter

from sqlalchemy import select

from aerona.agents.context.dominion_lines import god_called, place_name, spoken
from aerona.agents.context.scope import Scope
from aerona.catalog.mythic import REALM_PHRASES, trial_at
from aerona.core.grammar import agree, several
from aerona.db.tables.arcana import LawUpkeepRow, LongevityRow, VisStockRow, WarpingRow
from aerona.db.tables.culture import LegendProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.mythic import CosmicOfficeRow, GeasRow, HeroquestRow, MantlingRow, ServitorRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.entity import EntityStatus
from aerona.domain.enums.mythic import GeasState, HeroquestState, MantlingState
from aerona.engine.gods.queries import community_of


async def office_lines(scope: Scope, son: SonRow) -> list[str]:
    rows = list(await scope.session.scalars(select(CosmicOfficeRow).order_by(CosmicOfficeRow.office)))
    found = [
        f"You hold the cosmic office of {spoken(row.office.value)} (duty {row.duty}, neglect {row.neglect})" for row in rows if row.holder_node_id == son.id
    ]
    empty = [spoken(row.office.value) for row in rows if row.holder_node_id is None]
    if empty:
        found.append(f"Cosmic offices standing empty: {', '.join(empty)}")
    return found


async def servant_lines(scope: Scope, son: SonRow) -> list[str]:
    rows = list(await scope.session.scalars(select(ServitorRow).where(ServitorRow.god_node_id == son.id)))
    if not rows:
        return []
    roles = Counter(row.role.value for row in rows)
    loyal = round(sum(row.loyalty for row in rows) / len(rows))
    return [f"Your servitors: {', '.join(f'{count} {role}' for role, count in sorted(roles.items()))}; their loyalty averages {loyal}"]


async def kept_lines(scope: Scope, son: SonRow) -> list[str]:
    session = scope.session
    found = []
    for row in await session.scalars(select(LawUpkeepRow).where(LawUpkeepRow.caster_node_id == son.id).order_by(LawUpkeepRow.law_entity_id)):
        law = await session.get(EntityRow, row.law_entity_id)
        if law is not None and law.status is EntityStatus.CANON:
            found.append(
                f"You keep {law.name} ({row.source.value}): {row.essence_upkeep} essence each epoch, unpaid for {several(row.unpaid_epochs, 'epoch', 'epochs')}"
            )
    geasa = list(await session.scalars(select(GeasRow).where(GeasRow.layer_node_id == son.id)))
    if geasa:
        kept = sum(1 for row in geasa if row.state is GeasState.KEPT)
        found.append(f"Geasa you laid: {kept} kept, {len(geasa) - kept} broken")
    return found


async def myth_lines(scope: Scope, son: SonRow) -> list[str]:
    session = scope.session
    found = []
    questing = list(await session.scalars(select(HeroquestRow).where(HeroquestRow.god_node_id == son.id, HeroquestRow.state == HeroquestState.QUESTING)))
    if questing:
        found.append(f"{several(len(questing), 'mortal', 'mortals')} {agree(len(questing), 'walks', 'walk')} your myths in heroquests")
    for row in await session.scalars(select(MantlingRow).where(MantlingRow.god_node_id == son.id, MantlingRow.state == MantlingState.WALKING)):
        found.append(
            f"{await place_name(scope, row.mortal_entity_id)} #{several(row.mortal_entity_id, 'walk', 'walks')} your path toward godhood ({row.progress}%)"
        )
    return found


async def mythic_lines(scope: Scope, son: SonRow) -> list[str]:
    return [*await office_lines(scope, son), *await servant_lines(scope, son), *await kept_lines(scope, son), *await myth_lines(scope, son)]


async def vis_line(scope: Scope, holder_id: int, whose: str) -> list[str]:
    rows = [
        row for row in await scope.session.scalars(select(VisStockRow).where(VisStockRow.holder_node_id == holder_id).order_by(VisStockRow.form)) if row.amount
    ]
    return [f"{whose} vis: {', '.join(f'{row.form.value} {row.amount}' for row in rows)}"] if rows else []


async def mortal_magic_lines(scope: Scope, me: EntityRow) -> list[str]:
    session = scope.session
    found = await vis_line(scope, me.id, "your")
    community = await community_of(session, me)
    if community is not None:
        found.extend(await vis_line(scope, community.id, f"{community.name}'s"))
    warp = await session.get(WarpingRow, me.id)
    if warp is not None and warp.value:
        found.append(f"long exposure to magic has warped you ({warp.value}, stage {warp.stage})")
    long_life = await session.get(LongevityRow, me.id)
    if long_life is not None:
        dose = f"{long_life.dose} {long_life.form.value} vis each epoch"
        found.append(f"longevity magic keeps you: {dose}, dependence {long_life.dependence}, {long_life.years_gained} borrowed years")
    for geas in await session.scalars(select(GeasRow).where(GeasRow.bearer_entity_id == me.id).order_by(GeasRow.id)):
        layer = await god_called(scope, geas.layer_node_id) if geas.layer_node_id is not None else "a seer"
        found.append(f"a geas of {layer}: {geas.mode.value} {spoken(geas.act.value)} ({geas.state.value})")
    quest = await session.scalar(select(HeroquestRow).where(HeroquestRow.quester_entity_id == me.id, HeroquestRow.state == HeroquestState.QUESTING).limit(1))
    if quest is not None:
        legend = await session.get(LegendProfileRow, quest.legend_entity_id) if quest.legend_entity_id is not None else None
        trial = trial_at(legend.archetype if legend is not None else None, quest.step)
        found.append(f"your heroquest into {REALM_PHRASES[quest.realm]} stands at step {quest.step} of {quest.steps}; next comes a trial of {trial.value}")
    path = await session.get(MantlingRow, me.id)
    if path is not None and path.state is MantlingState.WALKING and path.god_node_id is not None:
        found.append(f"you walk the path of {await god_called(scope, path.god_node_id)} toward godhood ({path.progress}%)")
    return found
