from sqlalchemy import delete, select

from aerona.constants.units import PERCENT
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.foreign_gods import ForeignGodRow
from aerona.db.tables.intrigue import HookRow, TrueNameRow
from aerona.db.tables.node import NodeRow
from aerona.db.tables.relations import RelationshipRow
from aerona.db.tables.sons import SonRow
from aerona.db.write_guard import held
from aerona.domain.enums.customs import NameForm
from aerona.domain.enums.entity import EntityStatus, EntityType, MortalRole
from aerona.domain.enums.intrigue import HookSource, TrueNameCause
from aerona.domain.enums.modifier import IncidentRole
from aerona.engine.context import TickContext
from aerona.engine.customs.taboo import name_tabooed
from aerona.engine.intrigue.secrets import grant_hook
from aerona.engine.mortal.kin import partners_of
from aerona.engine.primitives.naming import Namer, seed_of
from aerona.engine.primitives.queries import living_entity
from aerona.engine.recording.record import record

ALWAYS_NAMED = frozenset({EntityType.SPIRIT, EntityType.OUTER_BEING})
SOMETIMES_NAMED = frozenset({EntityType.MORTAL, EntityType.PLACE, EntityType.ITEM, EntityType.SPECIES})
SCHOLARS = frozenset({MortalRole.SAGE, MortalRole.SCRIBE, MortalRole.SEER, MortalRole.SCIENTIST, MortalRole.JOURNALIST})
KNOWN = "known_by"
INTIMATE_AT = 70


async def name_bearer(ctx: TickContext, bearer_id: int, name: str, language_id: int | None = None) -> TrueNameRow | None:
    if not name or held(bearer_id) or await ctx.session.get(TrueNameRow, bearer_id) is not None:
        return None
    row = TrueNameRow(bearer_node_id=bearer_id, name=name, language_node_id=language_id, known_by=[bearer_id], since_epoch=ctx.epoch, locked=[])
    ctx.session.add(row)
    return row


async def seed_true_names(ctx: TickContext, namer: Namer) -> int:
    named = set(await ctx.session.scalars(select(TrueNameRow.bearer_node_id)))
    made = 0
    for son in await ctx.session.scalars(select(SonRow).order_by(SonRow.id)):
        if son.id not in named:
            given = son.existence_profile.true_name if son.existence_profile is not None else None
            drawn = given or await namer.person([], seed_of("true_name", son.id), son.current_world_id)
            made += bool(drawn and await name_bearer(ctx, son.id, drawn))
    for god in await ctx.session.scalars(select(ForeignGodRow).order_by(ForeignGodRow.id)):
        if god.id not in named and god.existence_profile is not None and god.existence_profile.true_name:
            made += bool(await name_bearer(ctx, god.id, god.existence_profile.true_name))
    kinds = list(ALWAYS_NAMED | SOMETIMES_NAMED)
    for entity in await ctx.session.scalars(
        select(EntityRow).where(EntityRow.entity_type.in_(kinds), EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id)
    ):
        if entity.id in named or held(entity.id):
            continue
        if entity.entity_type not in ALWAYS_NAMED and not ctx.rng(f"intrigue.true_name.{entity.id}").chance(ctx.rules.intrigue.true_name_chance_pct):
            continue
        name = await namer.person([entity], seed_of("true_name", entity.id), entity.world_id)
        if name:
            made += bool(await name_bearer(ctx, entity.id, name))
    return made


async def teach_name(ctx: TickContext, row: TrueNameRow, learner_id: int) -> bool:
    if learner_id in row.known_by or KNOWN in (row.locked or []) or held(learner_id):
        return False
    if await name_tabooed(ctx.session, row.bearer_node_id, ctx.epoch):
        return False
    row.known_by = sorted({*row.known_by, learner_id})
    await grant_hook(ctx, learner_id, row.bearer_node_id, HookSource.TRUE_NAME, strong=True)
    return True


async def research_names(ctx: TickContext) -> int:
    learned = 0
    scholars = await ctx.session.scalars(
        select(EntityRow)
        .where(EntityRow.entity_type == EntityType.MORTAL, EntityRow.status == EntityStatus.CANON, EntityRow.mortal_role.in_(list(SCHOLARS)))
        .order_by(EntityRow.id)
    )
    names = list(await ctx.session.scalars(select(TrueNameRow).order_by(TrueNameRow.bearer_node_id)))
    for scholar in scholars:
        if held(scholar.id) or not ctx.rng(f"intrigue.research.{scholar.id}.{ctx.epoch}").chance(ctx.rules.intrigue.research_name_pct):
            continue
        for row in names:
            bearer = await living_entity(ctx.session, row.bearer_node_id)
            if bearer is not None and bearer.world_id == scholar.world_id and scholar.id not in row.known_by and await teach_name(ctx, row, scholar.id):
                learned += 1
                break
    return learned


async def intimates_of(ctx: TickContext, bearer_id: int) -> list[int]:
    close = await ctx.session.scalars(
        select(RelationshipRow.subject_node_id)
        .where(RelationshipRow.holder_node_id == bearer_id, RelationshipRow.friendship >= INTIMATE_AT)
        .order_by(RelationshipRow.friendship.desc(), RelationshipRow.subject_node_id)
    )
    return list(dict.fromkeys([*await partners_of(ctx.session, bearer_id), *close]))


async def confide_names(ctx: TickContext) -> int:
    confided = 0
    for row in list(await ctx.session.scalars(select(TrueNameRow).order_by(TrueNameRow.bearer_node_id))):
        bearer = await living_entity(ctx.session, row.bearer_node_id)
        if bearer is None or bearer.entity_type is not EntityType.MORTAL or held(bearer.id):
            continue
        if not ctx.rng(seed_of("intrigue.confide_name", bearer.id, ctx.epoch)).chance(ctx.rules.intrigue.confide_name_pct):
            continue
        for intimate in await intimates_of(ctx, bearer.id):
            if intimate not in row.known_by and await living_entity(ctx.session, intimate) is not None and await teach_name(ctx, row, intimate):
                confided += 1
                break
    return confided


async def knows_name(ctx: TickContext, knower_id: int, bearer_id: int | None) -> bool:
    if bearer_id is None:
        return False
    row = await ctx.session.get(TrueNameRow, bearer_id)
    return row is not None and knower_id in row.known_by


async def name_power(ctx: TickContext, caster_id: int, target: EntityRow | None) -> float:
    if target is None:
        return 1.0
    table = ctx.rules.intrigue
    factor = 1.0
    if await knows_name(ctx, caster_id, target.id):
        factor += table.true_name_power_pct / PERCENT
    if await knows_name(ctx, target.id, caster_id):
        factor -= table.true_name_ward_pct / PERCENT
    return max(0.0, factor)


async def rename(ctx: TickContext, namer: Namer, row: TrueNameRow, *, cause: TrueNameCause, name: str | None = None, form: NameForm | None = None) -> bool:
    node = await ctx.session.get(NodeRow, row.bearer_node_id)
    if node is not None:
        await ctx.session.refresh(node)
    bearer = await ctx.session.get(EntityRow, node.id) if isinstance(node, EntityRow) else None
    son = await ctx.session.get(SonRow, node.id) if isinstance(node, SonRow) else None
    sources = [bearer] if bearer is not None else []
    world_id = bearer.world_id if bearer is not None else None
    name = name or await namer.person(sources, seed_of("true_name", row.bearer_node_id, ctx.epoch), world_id)
    if not name and son is not None and son.existence_profile is not None:
        name = f"{son.existence_profile.true_name or son.name} {ctx.epoch}"
    if not name:
        return False
    row.name, row.known_by, row.since_epoch = name, [row.bearer_node_id], ctx.epoch
    await ctx.session.execute(
        delete(HookRow).where(HookRow.target_node_id == row.bearer_node_id, HookRow.source == HookSource.TRUE_NAME, HookRow.locked.is_(False))
    )
    if son is not None and son.existence_profile is not None:
        son.existence_profile = son.existence_profile.model_copy(update={"true_name": name})
    await record(
        ctx,
        "intrigue.true_name_changed",
        roles={IncidentRole.SUBJECT: row.bearer_node_id},
        facts={"cause": cause, "form": form},
        son_id=son.id if son is not None else None,
        world_id=world_id,
    )
    return True


async def renew_names(ctx: TickContext, namer: Namer) -> int:
    table = ctx.rules.intrigue
    renewed = 0
    for row in list(await ctx.session.scalars(select(TrueNameRow).order_by(TrueNameRow.bearer_node_id))):
        if held(row.bearer_node_id) or "name" in (row.locked or []) or len(row.known_by) - 1 < table.rename_known_at:
            continue
        node = await ctx.session.get(NodeRow, row.bearer_node_id)
        son = await ctx.session.get(SonRow, node.id) if isinstance(node, SonRow) else None
        if son is not None:
            if son.essence < table.rename_essence:
                continue
            son.essence -= table.rename_essence
            renewed += await rename(ctx, namer, row, cause=TrueNameCause.REBIRTH)
        elif ctx.rng(seed_of("intrigue.rename", row.bearer_node_id, ctx.epoch)).chance(table.rename_initiation_pct):
            renewed += await rename(ctx, namer, row, cause=TrueNameCause.INITIATION)
    return renewed
