from collections import defaultdict
from collections.abc import Iterable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.calendar_slots import SLOTS
from aerona.catalog.preferences import ACTIVITY_VALUES, DRINKS, SPECIES_KINDS, STATIC_TARGETS
from aerona.constants.units import PERCENT
from aerona.db.read_memo import memoized
from aerona.db.tables.culture import ArtworkProfileRow, TraditionProfileRow
from aerona.db.tables.demography import PeopleCultureRow
from aerona.db.tables.ecology import SpeciesRangeRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.mind import PreferenceRow, SkillRow
from aerona.db.write_guard import write_blocked
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.culture import TraditionFunction
from aerona.domain.enums.domain import Domain
from aerona.domain.enums.entity import EntityStatus, EntityType, MortalRole
from aerona.domain.enums.mind import PreferenceKind, ValueAxis, ValueHolder
from aerona.domain.models.entity_stats import TraditionStats
from aerona.engine.body.customs import people_of
from aerona.engine.context import TickContext
from aerona.engine.ecology.totems import found_totem, totem_of
from aerona.engine.lore.style import favoured_modes, style_of
from aerona.engine.lore.traditions import cost_for
from aerona.engine.mind.book import is_locked, mind_of, stored_values
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.faith import living_patron
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.primitives.queries import active_bonds, connect
from aerona.engine.primitives.records import RecordSpec, create_record
from aerona.rules.registry import Rules

PREFERENCE_LOCK = "preferences"
PREFERENCES_KEY = "preferences"
STRENGTH_FIELD = "strength"
STRENGTH_SPAN = 100
TABOO_KINDS = frozenset({PreferenceKind.FOOD, PreferenceKind.DRINK})
HUNTER_ROLES = frozenset({MortalRole.HUNTER, MortalRole.EXPLORER})

Prefs = dict[tuple[PreferenceKind, str], int]


@memoized(PreferenceRow)
async def preference_rows(session: AsyncSession, holder_id: int) -> tuple[PreferenceRow, ...]:
    return tuple(await session.scalars(select(PreferenceRow).where(PreferenceRow.holder_node_id == holder_id).order_by(PreferenceRow.kind, PreferenceRow.id)))


async def rows_of(session: AsyncSession, holder_id: int) -> list[PreferenceRow]:
    return list(await preference_rows(session, holder_id))


async def prefs_of(session: AsyncSession, holder_id: int | None) -> Prefs:
    if holder_id is None:
        return {}
    return {(row.kind, row.target): row.strength for row in await rows_of(session, holder_id)}


async def write_pref(
    session: AsyncSession, holder_id: int, kind: PreferenceKind, target: str, strength: float, *, target_node_id: int | None = None
) -> PreferenceRow | None:
    if write_blocked(holder_id, PREFERENCES_KEY):
        return None
    row = await session.scalar(
        select(PreferenceRow).where(PreferenceRow.holder_node_id == holder_id, PreferenceRow.kind == kind, PreferenceRow.target == target)
    )
    value = clamp_int(strength, -STRENGTH_SPAN, STRENGTH_SPAN)
    if row is None:
        row = PreferenceRow(holder_node_id=holder_id, kind=kind, target=target, target_node_id=target_node_id, strength=value, locked=[])
        session.add(row)
    elif STRENGTH_FIELD not in (row.locked or []):
        row.strength = value
    await session.flush()
    return row


def set_pref(
    session: AsyncSession,
    rows: dict[tuple[PreferenceKind, str], PreferenceRow],
    holder_id: int,
    kind: PreferenceKind,
    target: str,
    *,
    strength: float,
    target_node_id: int | None = None,
) -> None:
    if write_blocked(holder_id, PREFERENCES_KEY):
        return
    value = clamp_int(strength, -STRENGTH_SPAN, STRENGTH_SPAN)
    row = rows.get((kind, target))
    if row is None:
        row = rows[(kind, target)] = PreferenceRow(holder_node_id=holder_id, kind=kind, target=target, target_node_id=target_node_id, strength=value, locked=[])
        session.add(row)
    elif STRENGTH_FIELD not in (row.locked or []):
        row.strength = value


async def prefs_by_holder(session: AsyncSession, holder_ids: list[int]) -> dict[int, Prefs]:
    found: dict[int, Prefs] = {holder: {} for holder in holder_ids}
    statement = select(PreferenceRow).where(PreferenceRow.holder_node_id.in_(holder_ids)).order_by(PreferenceRow.kind, PreferenceRow.id)
    for row in await session.scalars(statement):
        found[row.holder_node_id][(row.kind, row.target)] = row.strength
    return found


def fit(prefs: Prefs, kind: PreferenceKind, target: str | None) -> int:
    return prefs.get((kind, target), 0) if target is not None else 0


async def species_targets(session: AsyncSession, world_id: int | None, kind: PreferenceKind) -> list[tuple[str, int]]:
    wanted = EntityType.SPECIES if kind is PreferenceKind.CREATURE else EntityType.RESOURCE
    rows = await session.scalars(
        select(EntityRow.id)
        .where(EntityRow.entity_type == wanted, EntityRow.status == EntityStatus.CANON, EntityRow.world_id == world_id)
        .order_by(EntityRow.id)
    )
    return [(str(node), node) for node in rows]


async def home_region(session: AsyncSession, holder: EntityRow) -> RegionEnvironmentRow | None:
    atlas = await RegionAtlas.load(session)
    region = atlas.top_region(holder.id)
    return await session.get(RegionEnvironmentRow, region) if region is not None else None


async def home_terrain(session: AsyncSession, holder: EntityRow) -> str | None:
    found = await home_region(session, holder)
    return found.dominant_terrain.value if found is not None else None


async def leanings(session: AsyncSession, rules: Rules, people: EntityRow) -> dict[tuple[PreferenceKind, str], float]:
    values = await stored_values(session, ValueHolder.CULTURE, people.id)
    lean: dict[tuple[PreferenceKind, str], float] = defaultdict(float)
    terrain = await home_terrain(session, people)
    if terrain is not None:
        lean[(PreferenceKind.TERRAIN, terrain)] += 2
    patron = await living_patron(session, people)
    for domain in getattr(patron, "domains", ()) if patron is not None else ():
        if isinstance(domain, Domain):
            lean[(PreferenceKind.DEITY_ASPECT, domain.value)] += 2
    culture = await session.get(PeopleCultureRow, people.id)
    style = style_of(culture)
    for medium in favoured_modes(style, rules.customs.style_modes) if style is not None else []:
        lean[(PreferenceKind.ART_FORM, medium.value)] += 2
    for activity, weights in ACTIVITY_VALUES.items():
        lean[(PreferenceKind.ACTIVITY, activity)] += sum(values.get(axis, 0) * weight for axis, weight in weights.items()) / STRENGTH_SPAN
    lean[(PreferenceKind.MATERIAL, "gold")] += values.get(ValueAxis.WEALTH, 0) / STRENGTH_SPAN
    for slot, spec in SLOTS.items():
        lean[(PreferenceKind.SEASON, slot.value)] += values.get(spec.lean, 0) / STRENGTH_SPAN
    return lean


async def seed_culture(ctx: TickContext, people: EntityRow) -> int:
    if await rows_of(ctx.session, people.id):
        return 0
    table = ctx.rules.preferences
    rng = ctx.rng(f"prefs.{people.id}")
    lean = await leanings(ctx.session, ctx.rules, people)
    made = 0
    rows: dict[tuple[PreferenceKind, str], PreferenceRow] = {}
    for kind in PreferenceKind:
        pool = await species_targets(ctx.session, people.world_id, kind) if kind in SPECIES_KINDS else [(target, None) for target in STATIC_TARGETS[kind]]
        if not pool:
            continue
        ranked = sorted(pool, key=lambda item: (-(lean.get((kind, item[0]), 0.0) + rng.random()), item[0]))
        for target, node in ranked[: table.likes_per_kind]:
            set_pref(
                ctx.session,
                rows,
                people.id,
                kind,
                target,
                strength=table.seed_strength + rng.integer(-table.seed_jitter, table.seed_jitter),
                target_node_id=node,
            )
            made += 1
        for target, node in ranked[::-1][: table.dislikes_per_kind]:
            if (kind, target) in {(kind, item[0]) for item in ranked[: table.likes_per_kind]}:
                continue
            set_pref(
                ctx.session,
                rows,
                people.id,
                kind,
                target,
                strength=-table.seed_strength + rng.integer(-table.seed_jitter, table.seed_jitter),
                target_node_id=node,
            )
            made += 1
    if made:
        await ctx.session.flush()
    return made


async def seed_mortal(ctx: TickContext, mortal: EntityRow) -> int:
    if await rows_of(ctx.session, mortal.id):
        return 0
    table = ctx.rules.preferences
    people = await people_of(ctx.session, mortal)
    rng = ctx.rng(f"prefs.{mortal.id}")
    made = 0
    if write_blocked(mortal.id, PREFERENCES_KEY):
        return 0
    for row in await rows_of(ctx.session, people.id) if people is not None else []:
        if not rng.chance(table.personal_share_pct):
            continue
        strength = clamp_int(row.strength + rng.integer(-table.personal_deviation, table.personal_deviation), -STRENGTH_SPAN, STRENGTH_SPAN)
        ctx.session.add(
            PreferenceRow(holder_node_id=mortal.id, kind=row.kind, target=row.target, target_node_id=row.target_node_id, strength=strength, locked=[])
        )
        made += 1
    if made:
        await ctx.session.flush()
    return made


async def grow(ctx: TickContext, mortal: EntityRow) -> int:
    if is_locked(await mind_of(ctx.session, mortal.id), PREFERENCE_LOCK):
        return 0
    gain = ctx.rules.preferences.experience_gain
    rows = {(row.kind, row.target): row for row in await rows_of(ctx.session, mortal.id)}
    prefs = {key: row.strength for key, row in rows.items()}
    touched: list[tuple[PreferenceKind, str]] = []
    terrain = await home_terrain(ctx.session, mortal)
    if terrain is not None:
        touched.append((PreferenceKind.TERRAIN, terrain))
    practised = await ctx.session.scalars(select(SkillRow.skill).where(SkillRow.holder_node_id == mortal.id, SkillRow.last_used_epoch >= ctx.epoch))
    touched.extend((PreferenceKind.CRAFT, skill.value) for skill in practised if skill.value in STATIC_TARGETS[PreferenceKind.CRAFT])
    if mortal.mortal_role in HUNTER_ROLES:
        touched.append((PreferenceKind.ACTIVITY, "hunting"))
    patron = await living_patron(ctx.session, mortal)
    for domain in getattr(patron, "domains", ()) if patron is not None else ():
        if isinstance(domain, Domain):
            touched.append((PreferenceKind.DEITY_ASPECT, domain.value))
    for kind, target in touched:
        set_pref(ctx.session, rows, mortal.id, kind, target, strength=prefs.get((kind, target), 0) + gain)
    if touched:
        await ctx.session.flush()
    return len(touched)


async def pull_culture(ctx: TickContext, people: EntityRow, members: Iterable[EntityRow]) -> int:
    share = ctx.rules.preferences.culture_pull_pct / PERCENT
    sums: dict[tuple[PreferenceKind, str], list[int]] = defaultdict(list)
    listed = list(members)
    held_prefs = await prefs_by_holder(ctx.session, list(dict.fromkeys(member.id for member in listed)))
    for member in listed:
        for key, value in held_prefs[member.id].items():
            sums[key].append(value)
    moved = 0
    rows = {(row.kind, row.target): row for row in await rows_of(ctx.session, people.id)}
    own = {key: row.strength for key, row in rows.items()}
    for (kind, target), values in sums.items():
        if (kind, target) not in own:
            continue
        mean = sum(values) / len(values)
        current = own[(kind, target)]
        if round(current + (mean - current) * share) != current:
            set_pref(ctx.session, rows, people.id, kind, target, strength=current + (mean - current) * share)
            moved += 1
    if moved:
        await ctx.session.flush()
    return moved


async def make_taboos(ctx: TickContext, people: EntityRow) -> int:
    made = 0
    for row in await rows_of(ctx.session, people.id):
        if row.kind not in TABOO_KINDS or row.strength > ctx.rules.preferences.taboo_below:
            continue
        drink = DRINKS.get(row.target) if row.kind is PreferenceKind.DRINK else None
        if row.kind is PreferenceKind.DRINK and drink is None:
            continue
        good = drink.value if drink is not None else row.target
        if await kept_taboo(ctx, people.id, good):
            continue
        tradition = await create_record(
            ctx,
            RecordSpec(
                name=f"The Shunning of {good.replace('_', ' ').title()}",
                entity_type=EntityType.TRADITION,
                stats=TraditionStats(spread=PERCENT // 4, rigidity=PERCENT // 2),
                body=f"The {people.name} will not touch {good.replace('_', ' ')}.",
                power=2,
                world_id=people.world_id,
                location_id=people.location_id,
            ),
        )
        ctx.session.add(
            TraditionProfileRow(
                tradition_entity_id=tradition.id,
                kind=TraditionFunction.TABOO,
                calendar_slot=None,
                cost=cost_for(ctx, TraditionFunction.TABOO),
                effects={},
                taboo_target=good,
                origin_entity_id=people.id,
                updated_epoch=ctx.epoch,
                locked=[],
            )
        )
        await connect(ctx.session, people.id, tradition.id, BondKind.CELEBRATES, ctx.epoch, description="a shunning born of disgust")
        made += 1
    return made


async def kept_taboo(ctx: TickContext, people_id: int, target: str) -> bool:
    kept = [bond.target_node_id for bond in await active_bonds(ctx.session, [BondKind.CELEBRATES], sources=[people_id])]
    if not kept:
        return False
    found = await ctx.session.scalar(
        select(TraditionProfileRow.tradition_entity_id).where(
            TraditionProfileRow.tradition_entity_id.in_(kept), TraditionProfileRow.kind == TraditionFunction.TABOO, TraditionProfileRow.taboo_target == target
        )
    )
    return found is not None


async def favourite(session: AsyncSession, holder_id: int, kind: PreferenceKind) -> PreferenceRow | None:
    rows = [row for row in await rows_of(session, holder_id) if row.kind is kind and row.strength > 0]
    return max(rows, key=lambda row: (row.strength, -row.id), default=None)


async def adopt_totem(ctx: TickContext, people: EntityRow) -> bool:
    if await totem_of(ctx, people.id) is not None:
        return False
    loved = await favourite(ctx.session, people.id, PreferenceKind.CREATURE)
    if loved is None or loved.strength < ctx.rules.preferences.totem_above or loved.target_node_id is None:
        return False
    species = await ctx.session.get(EntityRow, loved.target_node_id)
    if species is None or species.status is not EntityStatus.CANON:
        return False
    await found_totem(ctx, people, species)
    return True


async def paint(ctx: TickContext, work: EntityRow, row: ArtworkProfileRow) -> bool:
    if row.colour is not None and row.shape is not None:
        return False
    maker = await ctx.session.get(EntityRow, row.author_entity_id) if row.author_entity_id is not None else None
    people = await people_of(ctx.session, maker or work)
    if people is None:
        return False
    rng = ctx.rng(f"palette.{work.id}")
    colour = await favourite(ctx.session, people.id, PreferenceKind.COLOUR)
    shape = await favourite(ctx.session, people.id, PreferenceKind.SHAPE)
    if row.colour is None and "colour" not in row.locked:
        row.colour = colour.target if colour is not None else rng.pick(list(STATIC_TARGETS[PreferenceKind.COLOUR]))
    if row.shape is None and "shape" not in row.locked:
        row.shape = shape.target if shape is not None else rng.pick(list(STATIC_TARGETS[PreferenceKind.SHAPE]))
    return True


async def art_fit(session: AsyncSession, holder: EntityRow, row: ArtworkProfileRow) -> int:
    people = await people_of(session, holder)
    if people is None:
        return 0
    prefs = await prefs_of(session, people.id)
    subject = await session.get(EntityRow, row.subject_node_id) if row.subject_node_id is not None else None
    parts = [
        fit(prefs, PreferenceKind.ART_FORM, row.medium.value),
        fit(prefs, PreferenceKind.COLOUR, row.colour),
        fit(prefs, PreferenceKind.SHAPE, row.shape),
        fit(prefs, PreferenceKind.ARTWORK_SUBJECT, subject.entity_type.value if subject is not None else None),
    ]
    return round(sum(parts) / len(parts))


@memoized(PreferenceRow)
async def kept_prefs(session: AsyncSession, holder_id: int) -> Prefs:
    return await prefs_of(session, holder_id)


async def market_fit(session: AsyncSession, market_id: int) -> Prefs:
    market = await session.get(EntityRow, market_id)
    people = await people_of(session, market) if market is not None else None
    return dict(await kept_prefs(session, people.id)) if people is not None else {}


def demand_factor(rules: Rules, prefs: Prefs, commodity: str) -> float:
    loves = [fit(prefs, PreferenceKind.FOOD, commodity)]
    loves.extend(fit(prefs, PreferenceKind.DRINK, drink) for drink, good in DRINKS.items() if good is not None and good.value == commodity)
    lean = max(loves, key=abs) if loves else 0
    return max(0.0, 1 + lean / STRENGTH_SPAN * rules.preferences.demand_pct / PERCENT)


def material_factor(rules: Rules, prefs: Prefs, material: str | None) -> float:
    return max(0.0, 1 + fit(prefs, PreferenceKind.MATERIAL, material) / STRENGTH_SPAN * rules.preferences.material_premium_pct / PERCENT)


async def nature_bonus(session: AsyncSession, rules: Rules, mortal: EntityRow) -> int:
    prefs = await prefs_of(session, mortal.id)
    loved = {
        node
        for (kind, target), value in prefs.items()
        if kind in SPECIES_KINDS and value >= rules.preferences.noted_above and target.isdigit()
        for node in [int(target)]
    }
    if not loved:
        return 0
    atlas = await RegionAtlas.load(session)
    region = atlas.top_region(mortal.id)
    if region is None:
        return 0
    found = await session.scalar(
        select(SpeciesRangeRow.species_entity_id).where(SpeciesRangeRow.region_entity_id == region, SpeciesRangeRow.species_entity_id.in_(loved)).limit(1)
    )
    near = (
        found is not None
        or await session.scalar(select(EntityRow.id).where(EntityRow.id.in_(loved), EntityRow.location_id == mortal.location_id).limit(1)) is not None
    )
    return rules.preferences.nature_bonus if near else 0
