from dataclasses import dataclass

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.life.mind import OPEN_STAGES
from aerona.constants.units import PERCENT
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.culture import TraditionProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.mind import GriefRow
from aerona.db.write_guard import write_blocked
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.culture import RiteStage, TraditionFunction
from aerona.domain.enums.entity import EntityStatus
from aerona.domain.enums.mind import Attribute, Facet, GriefStage, MemoryKind, ThoughtKind, TraitKind, TraitSource
from aerona.engine.context import TickContext
from aerona.engine.gods.queries import community_of
from aerona.engine.mind.book import add_trait, is_locked, locked_for, mind_of
from aerona.engine.mind.memories import remember
from aerona.engine.mind.split import attribute, facets_of
from aerona.engine.mind.thoughts import think, thinker
from aerona.engine.mortal.kin import close_kin_of, parents_of, partners_of, spouses_of
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.primitives.queries import active_bonds
from aerona.rules.registry import Rules

GRIEF_LOCK = "griefs"
GRIEFS_KEY = "griefs"
MOURNING_TRADITIONS = (TraditionFunction.MOURNING,)
MIDPOINT = 50
FACET_SPAN = 50


@dataclass(frozen=True)
class Loss:
    mourner_id: int
    thought: ThoughtKind
    strength: int


async def losses(session: AsyncSession, rules: Rules, deceased: EntityRow) -> list[Loss]:
    table = rules.grief
    found: dict[int, Loss] = {}
    spouses = set(await spouses_of(session, deceased.id)) | set(await partners_of(session, deceased.id))
    for kin in await close_kin_of(session, deceased.id):
        found[kin] = Loss(kin, ThoughtKind.SAW_KIN_DIE, table.kin_strength)
    for parent in await parents_of(session, deceased.id):
        found[parent] = Loss(parent, ThoughtKind.LOST_CHILD, table.child_strength)
    for spouse in spouses:
        found[spouse] = Loss(spouse, ThoughtKind.LOST_SPOUSE, table.spouse_strength)
    for bond in [
        *await active_bonds(session, [BondKind.COMPANION, BondKind.LOVES], sources=[deceased.id]),
        *await active_bonds(session, [BondKind.COMPANION, BondKind.LOVES], targets=[deceased.id]),
    ]:
        other = bond.other_end(deceased.id)
        found.setdefault(other, Loss(other, ThoughtKind.SAW_KIN_DIE, table.friend_strength))
    return [loss for loss in found.values() if loss.mourner_id != deceased.id and loss.strength >= table.min_strength]


async def mourning_stretch(session: AsyncSession, rules: Rules, mourner: EntityRow) -> float:
    community = await community_of(session, mourner)
    if community is None:
        return 1.0
    kept = select(BondRow.target_node_id).where(BondRow.source_node_id == community.id, BondRow.kind == BondKind.CELEBRATES, BondRow.state == BondState.ACTIVE)
    found = await session.scalar(
        select(TraditionProfileRow.tradition_entity_id)
        .where(
            TraditionProfileRow.tradition_entity_id.in_(kept),
            or_(TraditionProfileRow.kind.in_(MOURNING_TRADITIONS), TraditionProfileRow.stage == RiteStage.DEATH),
        )
        .limit(1)
    )
    return rules.grief.tradition_pct / PERCENT if found is not None else 1.0


async def start_grief(
    session: AsyncSession, rules: Rules, mourner_id: int, deceased_id: int, *, strength: int, epoch: int, forced: bool = False
) -> GriefRow | None:
    mourner = await thinker(session, mourner_id)
    if mourner is None or write_blocked(mourner_id, GRIEFS_KEY) or (not forced and await locked_for(session, mourner_id, GRIEF_LOCK)):
        return None
    existing = await session.scalar(select(GriefRow).where(GriefRow.mourner_node_id == mourner_id, GriefRow.deceased_node_id == deceased_id))
    if existing is not None:
        return existing
    length = max(1, round(rules.grief.mourning_epochs * strength / PERCENT * await mourning_stretch(session, rules, mourner)))
    row = GriefRow(
        mourner_node_id=mourner_id,
        deceased_node_id=deceased_id,
        stage=GriefStage.SHOCK,
        strength=clamp_int(strength, 0, PERCENT),
        started_epoch=epoch,
        stage_epoch=epoch,
        length_epochs=length,
    )
    session.add(row)
    await session.flush()
    return row


async def bereave(ctx: TickContext, deceased: EntityRow, killer_id: int | None) -> int:
    started = 0
    for loss in await losses(ctx.session, ctx.rules, deceased):
        await think(ctx.session, ctx.rules, loss.mourner_id, loss.thought, ctx.epoch, subject_id=deceased.id)
        if await start_grief(ctx.session, ctx.rules, loss.mourner_id, deceased.id, strength=loss.strength, epoch=ctx.epoch) is not None:
            started += 1
    if killer_id is not None and killer_id != deceased.id:
        await think(ctx.session, ctx.rules, killer_id, ThoughtKind.KILLED_FOE, ctx.epoch, subject_id=deceased.id)
    return started


async def killer_of(session: AsyncSession, deceased_id: int) -> int | None:
    return await session.scalar(
        select(BondRow.source_node_id).where(BondRow.target_node_id == deceased_id, BondRow.kind == BondKind.KILLED).order_by(BondRow.id.desc()).limit(1)
    )


@dataclass
class GriefTally:
    mourning: int = 0
    accepted: int = 0
    complicated: int = 0


async def resolve(ctx: TickContext, mourner: EntityRow, row: GriefRow) -> GriefStage:
    table = ctx.rules.grief
    gloom = (await facets_of(ctx.session, mourner.id)).get(Facet.DEPRESSION, 0) / FACET_SPAN
    will = (await attribute(ctx.session, ctx.rules, mourner, Attribute.WILLPOWER) - MIDPOINT) / PERCENT
    chance = table.complicated_pct * row.strength / PERCENT * (1 + gloom * table.depression_pct / PERCENT) * (1 - will * table.willpower_pct / PERCENT)
    if not ctx.rng(f"grief.{row.id}.{ctx.epoch}").chance(max(0.0, chance)):
        await think(ctx.session, ctx.rules, mourner.id, ThoughtKind.MADE_PEACE_WITH_LOSS, ctx.epoch, subject_id=row.deceased_node_id)
        return GriefStage.ACCEPTANCE
    if not is_locked(await mind_of(ctx.session, mourner.id), "traits"):
        await add_trait(ctx.session, mourner.id, TraitKind.MELANCHOLIC, TraitSource.EXPERIENCE, ctx.epoch, source_node_id=row.deceased_node_id)
    killer = await killer_of(ctx.session, row.deceased_node_id)
    living = await ctx.session.get(EntityRow, killer) if killer is not None else None
    if living is not None and living.status is EntityStatus.CANON and living.id != mourner.id:
        await remember(
            ctx.session,
            ctx.rules,
            holder_id=mourner.id,
            subject_id=living.id,
            kind=MemoryKind.KILLED_KIN,
            magnitude=-table.vengeance_magnitude,
            epoch=ctx.epoch,
            note="a grief that would not heal",
        )
    return GriefStage.COMPLICATED


async def advance(ctx: TickContext, mourner: EntityRow, tally: GriefTally) -> None:
    if is_locked(await mind_of(ctx.session, mourner.id), GRIEF_LOCK) or write_blocked(mourner.id, GRIEFS_KEY):
        return
    table = ctx.rules.grief
    rows = await ctx.session.scalars(select(GriefRow).where(GriefRow.mourner_node_id == mourner.id, GriefRow.stage.in_(OPEN_STAGES)).order_by(GriefRow.id))
    for row in list(rows):
        if row.stage is GriefStage.SHOCK and ctx.epoch - row.stage_epoch >= table.shock_epochs:
            row.stage, row.stage_epoch = GriefStage.MOURNING, ctx.epoch
        if row.stage is GriefStage.MOURNING and ctx.epoch - row.stage_epoch >= row.length_epochs:
            row.stage = await resolve(ctx, mourner, row)
            row.stage_epoch = ctx.epoch
            if row.stage is GriefStage.ACCEPTANCE:
                tally.accepted += 1
            else:
                tally.complicated += 1
            continue
        await think(ctx.session, ctx.rules, mourner.id, ThoughtKind.MOURNED, ctx.epoch, subject_id=row.deceased_node_id, intensity=row.strength)
        tally.mourning += 1
    await ctx.session.flush()
