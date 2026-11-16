from sqlalchemy import func, select

from aerona.db.tables.entities import EntityRow
from aerona.db.tables.intrigue import SecretRow
from aerona.db.tables.networks import NetworkNodeRow
from aerona.db.tables.powers import PowerRow
from aerona.db.tables.sacred import ForesightRow
from aerona.db.write_guard import held
from aerona.domain.enums.arcana import SpellForm, SpellTechnique
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.intrigue import BeliefSource
from aerona.domain.enums.powers import PowerState
from aerona.engine.context import TickContext
from aerona.engine.economy.purse import points_of
from aerona.engine.intrigue.beliefs import believe
from aerona.engine.intrigue.sources import SourceTally, shown_facts
from aerona.engine.intrigue.talk import SECRET_SEVERITY
from aerona.engine.primitives.folk import present_among


async def network_reports(ctx: TickContext, tally: SourceTally) -> None:
    confidence = ctx.rules.belief_state.network_confidence
    members: dict[int, list[int]] = {}
    for network, member in await ctx.session.execute(select(NetworkNodeRow.network_entity_id, NetworkNodeRow.member_node_id).order_by(NetworkNodeRow.id)):
        members.setdefault(network, []).append(member)
    for joined in members.values():
        for watcher in joined:
            if held(watcher):
                continue
            for other_id in joined:
                other = await ctx.session.get(EntityRow, other_id) if other_id != watcher else None
                if other is None or other.status is not EntityStatus.CANON:
                    continue
                for attribute, truth in shown_facts(other):
                    if await believe(ctx, watcher, other.id, attribute, truth, source=BeliefSource.NETWORK, confidence=confidence):
                        tally.beliefs += 1


async def foreseen(ctx: TickContext, tally: SourceTally) -> None:
    rows = await ctx.session.scalars(
        select(ForesightRow).where(ForesightRow.due_epoch >= ctx.epoch, ForesightRow.subject_node_id.is_not(None)).order_by(ForesightRow.id)
    )
    for row in list(rows):
        subject = await ctx.session.get(EntityRow, row.subject_node_id)
        if subject is None or held(row.seer_node_id) or await ctx.session.get(EntityRow, row.seer_node_id) is None:
            continue
        for attribute, truth in shown_facts(subject):
            if await believe(ctx, row.seer_node_id, subject.id, attribute, truth, source=BeliefSource.FORESIGHT, confidence=row.certainty):
                tally.beliefs += 1


async def read_mind(ctx: TickContext, other: EntityRow) -> list[tuple[str, int]]:
    found = [("wealth", await points_of(ctx.session, other))]
    heaviest = await ctx.session.scalar(select(func.max(SecretRow.severity)).where(SecretRow.holder_node_id == other.id, SecretRow.exposed_epoch.is_(None)))
    if heaviest is not None:
        found.append((SECRET_SEVERITY, int(heaviest)))
    return found


async def minds_read(ctx: TickContext, tally: SourceTally) -> None:
    readers = await ctx.session.scalars(
        select(PowerRow.holder_node_id)
        .where(PowerRow.technique == SpellTechnique.PERCEIVE, PowerRow.form == SpellForm.MIND, PowerRow.state == PowerState.ACTIVE)
        .distinct()
        .order_by(PowerRow.holder_node_id)
    )
    confidence = ctx.rules.belief_state.mind_confidence
    for reader_id in list(readers):
        reader = await ctx.session.get(EntityRow, reader_id)
        if reader is None or reader.location_id is None or held(reader.id):
            continue
        here = await present_among(ctx.session, [reader.location_id])
        near = await ctx.session.scalars(
            select(EntityRow)
            .where(here, EntityRow.entity_type == EntityType.MORTAL, EntityRow.status == EntityStatus.CANON, EntityRow.id != reader.id)
            .order_by(EntityRow.id)
        )
        for other in list(near)[: ctx.rules.belief_state.minds_read]:
            for attribute, truth in await read_mind(ctx, other):
                if await believe(ctx, reader.id, other.id, attribute, truth, source=BeliefSource.MIND_READING, confidence=confidence):
                    tally.beliefs += 1


async def far_sources(ctx: TickContext, tally: SourceTally) -> None:
    await network_reports(ctx, tally)
    await foreseen(ctx, tally)
    await minds_read(ctx, tally)
