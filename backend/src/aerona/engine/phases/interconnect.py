from sqlalchemy import delete, select

from aerona.constants.units import PERCENT
from aerona.db.repositories.chronicle import QUIET_ROLES
from aerona.db.tables.body import ConditionRow
from aerona.db.tables.interconnect import IncidentParticipantRow, IncidentRow, ModifierRow
from aerona.domain.enums.entity import COMMUNITY_TYPES, EntityFlag
from aerona.domain.enums.modifier import ModifierOp, ModifierSource
from aerona.engine.context import TickContext
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.interconnect.derived import derive_environment_modifiers, derive_tick_modifiers
from aerona.engine.interconnect.incident_backfill import backfill_incident_roles
from aerona.engine.interconnect.incidents import chains_in
from aerona.engine.interconnect.sources import CONDITION_EFFECTS, DERIVED_SOURCES
from aerona.engine.phase import Phase
from aerona.engine.primitives.derivation import identity_of
from aerona.engine.primitives.modifiers import NEUTRAL_MULTIPLIER, ModifierDraft, add_modifier, decayed
from aerona.engine.primitives.queries import flags_by_entity, living_entity
from aerona.engine.primitives.stats import has_stat
from aerona.engine.primitives.threads import open_story

WONDER_REASON = "modifier.wonder"
WONDER_GROUP = "wonder"


@reads(
    "artwork.renown",
    "structure.function",
    "table.artwork_profiles",
    "table.bodies",
    "table.bonds",
    "table.conditions",
    "table.cult_doctrines",
    "table.cult_tenets",
    "table.entities",
    "table.entity_flags",
    "table.law_jurisdictions",
    "table.law_profiles",
    "table.modifiers",
    "table.nodes",
    "table.polity_members",
    "table.son_powers",
    "table.sons",
    "table.tradition_participation",
    "table.tradition_profiles",
    "table.traits",
    "table.treaty_clauses",
    "table.treaty_parties",
    "table.treaty_profiles",
    "table.world_maps",
)
@writes("table.modifiers")
async def modifier_upkeep(ctx: TickContext) -> None:
    rules = ctx.rules.modifiers
    expired = await ctx.session.execute(delete(ModifierRow).where(ModifierRow.end_epoch.is_not(None), ModifierRow.end_epoch < ctx.epoch))
    ctx.count("modifiers_expired", int(getattr(expired, "rowcount", 0) or 0))
    faded = 0
    fading = select(ModifierRow).where(ModifierRow.decay_pct.is_not(None), ModifierRow.decay_pct > 0, ModifierRow.held.is_(False))
    for row in list(await ctx.session.scalars(fading)):
        if row.start_epoch >= ctx.epoch:
            continue
        row.magnitude = decayed(row)
        spent = (
            abs(row.magnitude) < rules.decayed_add_drop_below
            if row.op is ModifierOp.ADD
            else abs(row.magnitude - NEUTRAL_MULTIPLIER) * PERCENT < rules.decayed_multiplier_drop_within_pct
        )
        if spent:
            await ctx.session.delete(row)
            faded += 1
    ctx.count("modifiers_faded", faded)
    ctx.count("modifiers_derived", await derive_modifiers(ctx))
    ctx.count("modifiers_derived_sources", await derive_tick_modifiers(ctx))


@reads(
    "table.calendars",
    "table.entities",
    "table.forced_weather",
    "table.modifiers",
    "table.place_environment",
    "table.region_environment",
    "table.sky_events",
    "table.stars",
    "table.world_maps",
    "table.world_seasons",
    "table.worlds",
)
@writes("table.modifiers")
async def environment_modifiers(ctx: TickContext) -> None:
    ctx.count("modifiers_derived", await derive_environment_modifiers(ctx))


async def derive_modifiers(ctx: TickContext) -> int:
    rules = ctx.rules
    held = {
        identity_of(row)
        for row in await ctx.session.scalars(select(ModifierRow).where(ModifierRow.source_kind.in_(list(DERIVED_SOURCES)), ModifierRow.held.is_(True)))
    }
    await ctx.session.execute(delete(ModifierRow).where(ModifierRow.source_kind.in_(list(DERIVED_SOURCES)), ModifierRow.held.is_(False)))
    made = 0
    for wonder_id in sorted(await flags_by_entity(ctx.session, EntityFlag.WONDER)):
        wonder = await living_entity(ctx.session, wonder_id)
        holder = await living_entity(ctx.session, wonder.location_id) if wonder is not None else None
        if wonder is None or holder is None or holder.entity_type not in COMMUNITY_TYPES:
            continue
        for key, size in (("prosperity", rules.modifiers.wonder_prosperity), ("piety", rules.modifiers.wonder_piety)):
            if size and has_stat(holder, key):
                draft = ModifierDraft(
                    holder.id, key, ModifierOp.ADD, size, ModifierSource.WONDER, WONDER_REASON, ctx.epoch, source_node_id=wonder.id, stacking_group=WONDER_GROUP
                )
                if identity_of(draft) not in held:
                    await add_modifier(ctx.session, draft)
                    made += 1
    for condition in await ctx.session.scalars(select(ConditionRow).order_by(ConditionRow.id)):
        bearer = await living_entity(ctx.session, condition.bearer_node_id)
        if bearer is None or condition.ended_epoch is not None:
            continue
        for effect in CONDITION_EFFECTS.get(condition.kind, ()):
            if not has_stat(bearer, effect.key):
                continue
            reason = f"modifier.condition.{condition.kind.value}"
            group = f"condition.{condition.kind.value}"
            draft = ModifierDraft(bearer.id, effect.key, effect.op, effect.magnitude(rules), ModifierSource.CONDITION, reason, ctx.epoch, stacking_group=group)
            if identity_of(draft) not in held:
                await add_modifier(ctx.session, draft)
                made += 1
    await ctx.session.flush()
    return made


@reads(
    "table.applied_fixups",
    "table.chronicle",
    "table.entities",
    "table.incident_participants",
    "table.incidents",
    "table.thread_links",
    "table.war_sides",
    "table.wars",
)
@writes("table.applied_fixups", "table.incident_participants", "table.incidents", "table.thread_links", "table.threads")
async def incident_threads(ctx: TickContext) -> None:
    table = ctx.rules.incidents
    ctx.count("incident_roles_backfilled", await backfill_incident_roles(ctx))
    chains = await chains_in(ctx.session, ctx.epoch, table.thread_chain_min, table.chain_depth)
    opened = 0
    for chain in sorted(chains, key=lambda item: (-len(item.incident_ids), item.incident_ids)):
        if opened >= table.threads_per_epoch:
            break
        root = await ctx.session.get(IncidentRow, chain.incident_ids[0])
        if root is None or root.thread_id is not None:
            continue
        related = list(
            await ctx.session.scalars(
                select(IncidentParticipantRow.node_id).where(
                    IncidentParticipantRow.incident_id.in_(list(chain.incident_ids)), IncidentParticipantRow.role.not_in(QUIET_ROLES)
                )
            )
        )
        text = f"{chain.texts[0]} What followed has not ended: {chain.texts[-1]}"
        thread = await open_story(ctx.session, text, related, ctx.epoch)
        if thread is None:
            continue
        for incident_id in chain.incident_ids:
            row = await ctx.session.get(IncidentRow, incident_id)
            if row is not None:
                row.thread_id = thread.id
        opened += 1
    ctx.count("chain_threads", opened)


PHASES = (Phase("modifier_upkeep", modifier_upkeep), Phase("environment_modifiers", environment_modifiers))
THREAD_PHASES = (Phase("incident_threads", incident_threads),)
