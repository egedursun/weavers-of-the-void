from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.preferences import SPECIES_KINDS, STATIC_TARGETS
from aerona.constants.units import PERCENT
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.mind import MemoryRow, PreferenceRow
from aerona.db.tables.place import PlaceProfileRow
from aerona.db.write_guard import write_blocked
from aerona.domain.enums.mind import PreferenceKind
from aerona.engine.context import TickContext
from aerona.engine.mind.preferences import PREFERENCES_KEY, STRENGTH_SPAN, home_terrain, prefs_of, rows_of, write_pref
from aerona.engine.primitives.numbers import clamp_int
from aerona.rules.registry import Rules

FASHIONED = (PreferenceKind.TECHNOLOGY, PreferenceKind.MADE_THING, PreferenceKind.GAME, PreferenceKind.STORY_FORM)
SHARED_KINDS = tuple(kind for kind in PreferenceKind if kind not in SPECIES_KINDS)


async def seed_new_kinds(ctx: TickContext, people: EntityRow) -> int:
    held_kinds = {row.kind for row in await rows_of(ctx.session, people.id)}
    if not held_kinds:
        return 0
    table = ctx.rules.preferences
    made = 0
    for kind in SHARED_KINDS:
        if kind in held_kinds:
            continue
        rng = ctx.rng(f"prefs.{people.id}.{kind.value}")
        pool = sorted(STATIC_TARGETS[kind], key=lambda _target: rng.random())
        liked = pool[: table.likes_per_kind]
        for target in liked:
            made += fresh_pref(ctx, people.id, kind, target, table.seed_strength + rng.integer(-table.seed_jitter, table.seed_jitter))
        for target in pool[::-1][: table.dislikes_per_kind]:
            if target not in liked:
                made += fresh_pref(ctx, people.id, kind, target, -table.seed_strength + rng.integer(-table.seed_jitter, table.seed_jitter))
    if made:
        await ctx.session.flush()
    return made


def fresh_pref(ctx: TickContext, holder_id: int, kind: PreferenceKind, target: str, strength: int) -> int:
    if write_blocked(holder_id, PREFERENCES_KEY):
        return 0
    value = clamp_int(strength, -STRENGTH_SPAN, STRENGTH_SPAN)
    ctx.session.add(PreferenceRow(holder_node_id=holder_id, kind=kind, target=target, target_node_id=None, strength=value, locked=[]))
    return 1


async def sour(ctx: TickContext, mortals: list[EntityRow]) -> int:
    ids = [mortal.id for mortal in mortals]
    if not ids:
        return 0
    floor = ctx.rules.preference_depth.sour_at
    liked = select(PreferenceRow).where(PreferenceRow.holder_node_id.in_(ids), PreferenceRow.target_node_id.is_not(None), PreferenceRow.strength > 0)
    rows = list(await ctx.session.scalars(liked.order_by(PreferenceRow.id)))
    if not rows:
        return 0
    wounds = select(MemoryRow.holder_node_id, MemoryRow.subject_node_id).where(MemoryRow.holder_node_id.in_(ids), MemoryRow.magnitude <= floor)
    hurt = {(holder, subject) for holder, subject in (await ctx.session.execute(wounds)).all()}
    soured = 0
    for row in rows:
        if (row.holder_node_id, row.target_node_id) in hurt and "strength" not in (row.locked or []):
            row.strength = -row.strength
            soured += 1
    return soured


async def follow_fashion(ctx: TickContext, mortal: EntityRow) -> bool:
    rng = ctx.rng(f"fashion.{mortal.id}.{ctx.epoch}")
    if not rng.chance(ctx.rules.preference_depth.fashion_pct):
        return False
    kind = rng.pick(list(FASHIONED))
    target = rng.pick(list(STATIC_TARGETS[kind]))
    current = (await prefs_of(ctx.session, mortal.id)).get((kind, target), 0)
    await write_pref(ctx.session, mortal.id, kind, target, current + ctx.rules.preferences.experience_gain)
    return True


async def keep_tastes(ctx: TickContext, mortals: list[EntityRow]) -> int:
    followed = 0
    for mortal in mortals:
        followed += 1 if await follow_fashion(ctx, mortal) else 0
    return await sour(ctx, mortals) + followed


async def place_pull(session: AsyncSession, rules: Rules, holder_id: int | None, town: EntityRow) -> int:
    if holder_id is None:
        return 0
    prefs = await prefs_of(session, holder_id)
    terrain = await home_terrain(session, town)
    profile = await session.get(PlaceProfileRow, town.id)
    liked = prefs.get((PreferenceKind.TERRAIN, terrain), 0) if terrain is not None else 0
    liked += prefs.get((PreferenceKind.PLACE_KIND, profile.kind.value), 0) if profile is not None else 0
    return liked * rules.preference_depth.migration_pull // PERCENT


async def shared_taste(session: AsyncSession, rules: Rules, first_id: int, second_id: int) -> int:
    mine, theirs = await prefs_of(session, first_id), await prefs_of(session, second_id)
    agree = sum(1 for key, value in mine.items() if key in theirs and (value > 0) == (theirs[key] > 0))
    return agree * rules.preference_depth.partner_pull
