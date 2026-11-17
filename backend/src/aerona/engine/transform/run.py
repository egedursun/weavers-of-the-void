from sqlalchemy import select

from aerona.catalog.transformations import TRANSFORMS, WARNED_KINDS
from aerona.constants.units import PERCENT
from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.db.repositories.notifications import NotificationDraft, NotificationRepository
from aerona.db.tables.node import NodeRow
from aerona.db.tables.transform import StarModifierRow, TransformationRow, TransformProspectRow
from aerona.db.write_guard import held
from aerona.domain.enums.chronicle import NotificationCategory
from aerona.domain.enums.transform import ProspectStance, TransformKind, TransformTrigger
from aerona.engine.context import TickContext
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.primitives.numbers import clamp_percent
from aerona.engine.transform.cosmos import spread_star_light
from aerona.engine.transform.gods import tend_fallen
from aerona.engine.transform.kinds import KINDS
from aerona.engine.transform.ledger import Ledger
from aerona.engine.transform.moves import carry_bonds
from aerona.engine.transform.record import record_transformation

WARNINGS = {
    TransformKind.FALL: (NotificationCategory.ASCENSION, "{name} may fall from godhood", "Block the fall from the son's drawer, or let it come."),
    TransformKind.CORRUPTION: (
        NotificationCategory.HORROR,
        "{name} is near corruption",
        "Cleanse, forbid bargains, chain, call the council or send a redemption heroquest, or block it outright.",
    ),
}


async def prospect_of(ctx: TickContext, kind: TransformKind, subject_id: int) -> TransformProspectRow | None:
    return await ctx.session.scalar(select(TransformProspectRow).where(TransformProspectRow.kind == kind, TransformProspectRow.subject_node_id == subject_id))


async def open_prospect(ctx: TickContext, kind: TransformKind, subject_id: int, trigger: TransformTrigger) -> TransformProspectRow:
    row = await prospect_of(ctx, kind, subject_id)
    if row is None:
        row = TransformProspectRow(
            kind=kind, subject_node_id=subject_id, progress=0, stance=ProspectStance.OPEN, trigger=trigger, updated_epoch=ctx.epoch, locked=[]
        )
        ctx.session.add(row)
        await ctx.session.flush()
    return row


async def warn(ctx: TickContext, row: TransformProspectRow) -> None:
    category, title, body = WARNINGS[row.kind]
    node = await ctx.session.get(NodeRow, row.subject_node_id)
    row.warned_epoch = ctx.epoch
    row.due_epoch = ctx.epoch + ctx.rules.transform.warn_epochs
    await NotificationRepository(ctx.session).add(
        NotificationDraft(
            category=category,
            title=title.format(name=node.name if node is not None else TRANSFORMS[row.kind].source.value),
            body=body,
            epoch=ctx.epoch,
            target_node_id=row.subject_node_id,
        )
    )


async def perform(ctx: TickContext, kind: TransformKind, subject_id: int, trigger: TransformTrigger) -> TransformationRow:
    ledger = Ledger()
    result = await KINDS[kind].perform(ctx, subject_id, ledger)
    ctx.count("bonds_carried", await carry_bonds(ctx, ledger, subject_id, result))
    row = await record_transformation(ctx, kind, subject_id, result, trigger=trigger, ledger=ledger)
    prospect = await prospect_of(ctx, kind, subject_id)
    if prospect is not None:
        await ctx.session.delete(prospect)
    await ctx.session.flush()
    return row


def ready(ctx: TickContext, row: TransformProspectRow) -> bool:
    if row.stance is ProspectStance.BLOCKED or held(row.subject_node_id):
        return False
    if row.progress < PERCENT and row.stance is not ProspectStance.FORCED:
        return False
    return row.kind not in WARNED_KINDS or (row.warned_epoch is not None and ctx.epoch >= (row.due_epoch or row.warned_epoch))


async def watch(ctx: TickContext, kind: TransformKind) -> int:
    spec = KINDS[kind]
    pushes = await spec.pressures(ctx)
    rows = {row.subject_node_id: row for row in await ctx.session.scalars(select(TransformProspectRow).where(TransformProspectRow.kind == kind))}
    for subject, (pressure, trigger) in sorted(pushes.items()):
        if held(subject):
            continue
        row = rows.get(subject) or await open_prospect(ctx, kind, subject, trigger)
        rows[subject] = row
        if "progress" not in row.locked:
            row.progress = clamp_percent(pressure if spec.direct else row.progress + spec.step(ctx.rules, pressure))
        if "trigger" not in row.locked and row.stance is not ProspectStance.FORCED:
            row.trigger = trigger
        row.updated_epoch = ctx.epoch
    for subject, row in list(rows.items()):
        if subject in pushes or held(subject) or "progress" in row.locked:
            continue
        row.progress = 0 if spec.direct else max(0, row.progress - ctx.rules.transform.decay)
        row.updated_epoch = ctx.epoch
        if row.progress == 0 and row.stance is ProspectStance.OPEN:
            await ctx.session.delete(row)
            del rows[subject]
    done = 0
    for row in sorted(rows.values(), key=lambda item: item.subject_node_id):
        if kind in WARNED_KINDS and row.warned_epoch is None and (row.progress > 0 or row.stance is ProspectStance.FORCED) and not held(row.subject_node_id):
            await warn(ctx, row)
        if not ready(ctx, row) or await spec.check(ctx, row.subject_node_id) is not None:
            continue
        await perform(ctx, kind, row.subject_node_id, row.trigger)
        done += 1
    await ctx.session.flush()
    return done


async def fade_star_modifiers(ctx: TickContext) -> int:
    faded = 0
    for row in await ctx.session.scalars(select(StarModifierRow).where(StarModifierRow.decay > 0).order_by(StarModifierRow.id)):
        if held(row.star_id) or "luminosity_pct" in row.locked:
            continue
        step = min(row.decay, abs(row.luminosity_pct))
        row.luminosity_pct += step if row.luminosity_pct < 0 else -step
        faded += 1
        if row.luminosity_pct == 0 and row.age_epochs == 0:
            await ctx.session.delete(row)
    return faded


@reads(
    "cult.zeal",
    "people.prosperity",
    "table.afflictions",
    "table.bonds",
    "table.cosmos",
    "table.creator",
    "table.cult_doctrines",
    "table.cult_tenets",
    "table.dimensional_events",
    "table.dimensions",
    "table.entities",
    "table.entity_flags",
    "table.faith_climates",
    "table.foreign_gods",
    "table.galactic_structures",
    "table.galaxies",
    "table.galaxy_clusters",
    "table.held_identities",
    "table.holder_techniques",
    "table.language_policies",
    "table.natural_law_profiles",
    "table.nodes",
    "table.phenomenon_profiles",
    "table.polity_members",
    "table.reputations",
    "table.reverences",
    "table.sons",
    "table.star_modifiers",
    "table.stars",
    "table.theory_adherents",
    "table.theory_profiles",
    "table.title_profiles",
    "table.transform_prospects",
    "table.worlds",
)
@writes("table.transform_prospects", "table.transformations")
async def transformations(ctx: TickContext) -> None:
    ctx.count("fallen_tended", await tend_fallen(ctx))
    ctx.count("star_light", await spread_star_light(ctx))
    ctx.count("star_modifiers_faded", await fade_star_modifiers(ctx))
    for kind in sorted(KINDS):
        ctx.count("transformations_done", await watch(ctx, kind))


async def force(ctx: TickContext, kind: TransformKind, subject_id: int) -> TransformationRow:
    spec = KINDS.get(kind)
    if spec is None:
        raise ValidationFailedError(f"{TRANSFORMS[kind].label} happens at its own moment; it can be blocked but not forced.")
    reason = await spec.check(ctx, subject_id)
    if reason is not None:
        raise ValidationFailedError(reason)
    return await perform(ctx, kind, subject_id, spec.forced_trigger)


async def order(ctx: TickContext, kind: TransformKind, subject_id: int, trigger: TransformTrigger) -> TransformProspectRow:
    row = await open_prospect(ctx, kind, subject_id, trigger)
    row.stance = ProspectStance.FORCED
    row.trigger = trigger
    row.progress = PERCENT
    row.updated_epoch = ctx.epoch
    if kind in WARNED_KINDS and row.warned_epoch is None:
        await warn(ctx, row)
    await ctx.session.flush()
    return row


async def press(ctx: TickContext, kind: TransformKind, subject_id: int, amount: int, trigger: TransformTrigger) -> TransformProspectRow:
    spec = KINDS.get(kind)
    if spec is None:
        raise ValidationFailedError(f"{TRANSFORMS[kind].label} happens at its own moment and cannot be pressed toward.")
    reason = await spec.check(ctx, subject_id)
    if reason is not None:
        raise ValidationFailedError(reason)
    row = await open_prospect(ctx, kind, subject_id, trigger)
    if row.stance is ProspectStance.BLOCKED:
        raise ValidationFailedError("The Creator has blocked this transformation.")
    row.progress = clamp_percent(row.progress + amount)
    row.trigger = trigger
    row.updated_epoch = ctx.epoch
    await ctx.session.flush()
    return row


async def set_stance(ctx: TickContext, kind: TransformKind, subject_id: int, stance: ProspectStance) -> TransformProspectRow:
    if await ctx.session.get(NodeRow, subject_id) is None:
        raise NotFoundError("No such thing.")
    row = await open_prospect(ctx, kind, subject_id, TransformTrigger.ENGINE)
    row.stance = stance
    await ctx.session.flush()
    return row
