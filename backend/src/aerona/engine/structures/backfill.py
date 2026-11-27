import re

from sqlalchemy import select

from aerona.catalog.backfill_words import STRUCTURE_WORDS
from aerona.catalog.life.domain import GONE_STATES
from aerona.catalog.structures import ENGINE_KIND_STRUCTURES, WORKSHOP_STRUCTURES
from aerona.db.fixups import fixup_due, marker
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.cosmos import AppliedFixupRow
from aerona.db.tables.economy import WorkshopRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.sons import SonRow
from aerona.db.tables.structures import StructureProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.entity import EntityFlag, EntityStatus, EntityType
from aerona.domain.enums.structure import ConstructionState, StructureKind
from aerona.engine.context import TickContext
from aerona.engine.primitives.queries import flags_by_entity
from aerona.engine.primitives.stats import stat_or
from aerona.engine.structures.profiles import ensure_profile, host_for, refresh, standing_state, style_for, style_snapshot
from aerona.engine.structures.spec import resolve

BACKFILL_FIXUP = "structures.typed_backfill"
STYLE_FIXUP = "structures.style_snapshot"
PREFIX_MIN = 4
FALLBACK = StructureKind.MONUMENT


def tokens_of(text: str) -> list[str]:
    return re.findall(r"[^\W\d_]+", text.casefold())


def matches(word: str, text: str, tokens: list[str]) -> bool:
    if " " in word:
        return word in text
    return any(token == word or (len(word) >= PREFIX_MIN and token.startswith(word)) for token in tokens)


def type_from_record(structure: EntityRow, *, legacy: bool) -> StructureKind:
    if structure.engine_kind is not None and structure.engine_kind in ENGINE_KIND_STRUCTURES:
        return ENGINE_KIND_STRUCTURES[structure.engine_kind]
    if not legacy:
        return FALLBACK
    text = f"{structure.subtype or ''} {structure.name}".casefold()
    tokens = tokens_of(text)
    for kind, words in STRUCTURE_WORDS.items():
        if any(matches(word, text, tokens) for word in words):
            return kind
    return FALLBACK


async def builder_of(ctx: TickContext, structure: EntityRow) -> EntityRow | None:
    bond = await ctx.session.scalar(select(BondRow).where(BondRow.target_node_id == structure.id, BondRow.kind == BondKind.BUILT).order_by(BondRow.id).limit(1))
    return await ctx.session.get(EntityRow, bond.source_node_id) if bond is not None else None


async def dedicated_of(ctx: TickContext, structure: EntityRow) -> int | None:
    rows = await ctx.session.scalars(
        select(BondRow.target_node_id).where(BondRow.source_node_id == structure.id, BondRow.kind == BondKind.WORSHIPS, BondRow.state == BondState.ACTIVE)
    )
    for node_id in rows:
        if await ctx.session.get(SonRow, node_id) is not None:
            return node_id
    return None


async def type_structure(ctx: TickContext, structure: EntityRow, ruined: bool, *, legacy: bool) -> StructureProfileRow:
    kind = type_from_record(structure, legacy=legacy)
    profile = await ensure_profile(
        ctx.session,
        ctx.rules,
        ctx.epoch,
        structure,
        kind,
        builder=await builder_of(ctx, structure),
        son_id=await dedicated_of(ctx, structure),
    )
    profile.built_epoch = structure.birth_epoch
    profile.condition = stat_or(structure, "durability", profile.condition)
    profile.construction_state = ConstructionState.RUINED if ruined else standing_state(ctx.rules, profile)
    await refresh(ctx.session, ctx.rules, structure, profile)
    return profile


async def link_workshops(ctx: TickContext, profiles: list[StructureProfileRow]) -> int:
    linked = 0
    by_host = {(profile.host_entity_id, resolve(profile.kind).workshop): profile for profile in profiles if profile.host_entity_id is not None}
    for workshop in await ctx.session.scalars(select(WorkshopRow).where(WorkshopRow.structure_entity_id.is_(None)).order_by(WorkshopRow.id)):
        if workshop.kind not in WORKSHOP_STRUCTURES:
            continue
        profile = by_host.get((workshop.community_entity_id, workshop.kind))
        if profile is not None and profile.construction_state not in GONE_STATES:
            workshop.structure_entity_id = profile.structure_entity_id
            linked += 1
    return linked


async def untyped(ctx: TickContext) -> list[EntityRow]:
    known = select(StructureProfileRow.structure_entity_id)
    rows = await ctx.session.scalars(
        select(EntityRow)
        .where(EntityRow.entity_type == EntityType.STRUCTURE, EntityRow.status == EntityStatus.CANON, EntityRow.id.not_in(known))
        .order_by(EntityRow.id)
    )
    return list(rows)


async def backfill_structures(ctx: TickContext) -> dict[str, int]:
    pending = await untyped(ctx)
    applied = await marker(ctx.session, BACKFILL_FIXUP)
    legacy = applied is None and await fixup_due(ctx.session, BACKFILL_FIXUP)
    if not pending and applied is not None:
        return {}
    ruins = await flags_by_entity(ctx.session, EntityFlag.RUIN)
    profiles = [await type_structure(ctx, structure, structure.id in ruins, legacy=legacy) for structure in pending]
    result = {"typed": len(profiles), "workshops": await link_workshops(ctx, profiles)}
    if applied is None:
        ctx.session.add(AppliedFixupRow(key=BACKFILL_FIXUP, result=result))
    else:
        previous = applied.result or {}
        applied.result = {key: int(previous.get(key, 0)) + value for key, value in result.items()}
    await ctx.session.flush()
    return result


async def snapshot_styles(ctx: TickContext) -> int:
    if not await fixup_due(ctx.session, STYLE_FIXUP):
        return 0
    taken = 0
    for profile in list(await ctx.session.scalars(select(StructureProfileRow).where(StructureProfileRow.style_ornament.is_(None)))):
        if held(profile.structure_entity_id):
            continue
        work = await ctx.session.get(EntityRow, profile.structure_entity_id)
        style = await style_for(ctx.session, await host_for(ctx.session, work)) if work is not None else None
        if style is None:
            continue
        for column, value in style_snapshot(style).items():
            if column not in profile.locked:
                setattr(profile, column, value)
        taken += 1
    ctx.session.add(AppliedFixupRow(key=STYLE_FIXUP, result={"styled": taken}))
    await ctx.session.flush()
    return taken
