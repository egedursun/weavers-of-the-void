import re
from dataclasses import dataclass

from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.lifecycle import DesignatedHeirRow
from aerona.db.tables.polity import OfficeRow, PolityProfileRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import EntityFlag, EntityType, MortalRole
from aerona.domain.enums.polity import OfficeKind
from aerona.domain.models.entity_stats import MortalStats
from aerona.engine.context import TickContext
from aerona.engine.lifecycle.ruler_roles import ruler_role
from aerona.engine.mortal.life import sex_of_stats, window_end_pct
from aerona.engine.primitives.faith import living_patron
from aerona.engine.primitives.naming import Namer, seed_of
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.primitives.queries import active_bonds, close, connect, living_entity, spoken_language
from aerona.engine.primitives.records import RecordSpec, open_record
from aerona.engine.primitives.society import class_shares
from aerona.engine.primitives.stats import stat, stat_or
from aerona.language.titles import holder_title_of
from aerona.rules.registry import Rules

RULED_PRIMARY_TYPES = (EntityType.SETTLEMENT, EntityType.PEOPLE, EntityType.FACTION, EntityType.CULT, EntityType.REGION, EntityType.PLACE)
REGNAL_SUFFIX = re.compile(r"\s+[IVXLCDM]+$")
HEIR_SUBTYPE = "heir"


def dynasty_root(name: str) -> str:
    return REGNAL_SUFFIX.sub("", name).strip() or name


async def _shared_throne(ctx: TickContext, bond: BondRow, dead_id: int) -> bool:
    for other in await active_bonds(ctx.session, [BondKind.RULES], targets=[bond.target_node_id]):
        if other.source_node_id == dead_id:
            continue
        ruler = await living_entity(ctx.session, other.source_node_id)
        if ruler is not None and ruler.entity_type is EntityType.MORTAL:
            return True
    return False


async def _designated(ctx: TickContext, dead: EntityRow) -> EntityRow | None:
    row = await ctx.session.get(DesignatedHeirRow, dead.id)
    if row is None:
        return None
    heir = await living_entity(ctx.session, row.heir_entity_id)
    await ctx.session.delete(row)
    return heir if heir is not None and heir.entity_type is EntityType.MORTAL else None


async def _spawn_heir(ctx: TickContext, dead: EntityRow, primary: EntityRow | None) -> EntityRow:
    rules = ctx.rules
    effects = rules.world_effects
    rng = ctx.rng(seed_of("heir", dead.id))
    sources = [dead] if primary is None else [dead, primary]
    name = await Namer(ctx.session, rules).person(sources, seed_of(dead.id, ctx.epoch, HEIR_SUBTYPE), dead.world_id)
    root = dynasty_root(dead.name)
    title = holder_title_of(primary.entity_type, primary.name) if primary is not None else f"of the line of {root}"
    deviation = effects.inheritance_deviation

    def inherit(key: str) -> int:
        value = stat(dead, key)
        base = value if value is not None else effects.inheritance_default_stat
        return clamp_int(base + rng.integer(-deviation, deviation), 0, PERCENT)

    lifespan_base = stat_or(dead, "lifespan", effects.default_lifespan)
    lifespan = clamp_int(
        lifespan_base + rng.integer(-effects.heir_lifespan_deviation, effects.heir_lifespan_deviation), effects.heir_min_lifespan, rules.deep_life.lifespan_cap
    )
    flags = [EntityFlag.NAME_FROM_LANGUAGE] if name else []
    born = heir_age(rules, dead, effects.heir_age_base + rng.die(effects.heir_age_die), lifespan)
    heir = await open_record(
        ctx.session,
        ctx.epoch,
        RecordSpec(
            entity_type=EntityType.MORTAL,
            name=name or root,
            body=f"{dead.name} died and left what they ruled to them.",
            stats=MortalStats(
                hp=effects.heir_hp,
                strength=inherit("strength"),
                agility=inherit("agility"),
                intellect=inherit("intellect"),
                charisma=inherit("charisma"),
                age=born.age,
                lifespan=lifespan,
            ),
            power=max(1, dead.power_level - 1),
            location_id=dead.location_id,
            world_id=dead.world_id,
            subtype=ruler_role(rules, primary, await class_shares(ctx.session, rules, primary.id) if primary is not None else {}, rng),
            mortal_role=MortalRole.RULER,
            title=title,
            flags=flags,
        ),
    )
    if born.child:
        await connect(ctx.session, dead.id, heir.id, BondKind.PARENT_OF, ctx.epoch, description="named heir")
    else:
        await connect(ctx.session, heir.id, dead.id, BondKind.DESCENDS_FROM, ctx.epoch, description="heir of the line")
    language = await spoken_language(ctx.session, dead.id) or (await spoken_language(ctx.session, primary.id) if primary is not None else None)
    if language is not None:
        await connect(ctx.session, heir.id, language.id, BondKind.SPEAKS, ctx.epoch)
    patron = await living_patron(ctx.session, dead)
    if patron is not None:
        await connect(ctx.session, heir.id, patron.id, BondKind.WORSHIPS, ctx.epoch)
    return heir


@dataclass(frozen=True)
class HeirAge:
    age: int
    child: bool


def heir_age(rules: Rules, parent: EntityRow, wanted: int, own_lifespan: int) -> HeirAge:
    lifespan = stat_or(parent, "lifespan", rules.world_effects.default_lifespan)
    youngest_parent = lifespan * rules.fertility.window_start_pct // PERCENT
    oldest_parent = max(youngest_parent, lifespan * window_end_pct(rules, sex_of_stats(parent)) // PERCENT)
    age = int(stat_or(parent, "age", wanted + youngest_parent))
    oldest_child = age - youngest_parent
    youngest_child = age - oldest_parent
    room = max(0, own_lifespan - rules.world_effects.rejuvenate_years_left - 1)
    if youngest_child > room:
        return HeirAge(max(0, min(wanted, room)), child=False)
    return HeirAge(max(0, min(oldest_child, room, max(wanted, youngest_child))), child=True)


async def pass_rule(ctx: TickContext, dead: EntityRow) -> EntityRow | None:
    ruled: list[BondRow] = []
    for bond in await active_bonds(ctx.session, [BondKind.RULES], sources=[dead.id]):
        if await _shared_throne(ctx, bond, dead.id):
            await close(ctx.session, bond, ctx.epoch, "shared rule")
        else:
            ruled.append(bond)
    if not ruled:
        return None
    targets = [target for target in [await living_entity(ctx.session, bond.target_node_id) for bond in ruled] if target is not None]
    primary = next((target for target in targets if target.entity_type in RULED_PRIMARY_TYPES), targets[0] if targets else None)
    heir = await _designated(ctx, dead) or await _spawn_heir(ctx, dead, primary)
    for bond in ruled:
        await close(ctx.session, bond, ctx.epoch, "succession")
        await connect(ctx.session, heir.id, bond.target_node_id, BondKind.RULES, ctx.epoch, description="inheritance")
    ctx.count("heirs")
    return heir


async def designate_heir(ctx: TickContext, ruler_id: int, heir_id: int) -> DesignatedHeirRow:
    ruler = await living_entity(ctx.session, ruler_id)
    heir = await living_entity(ctx.session, heir_id)
    if ruler is None or heir is None:
        raise NotFoundError("Both the ruler and the heir must be living records.")
    if ruler.entity_type is not EntityType.MORTAL or heir.entity_type is not EntityType.MORTAL or ruler.id == heir.id:
        raise ValidationFailedError("A living mortal ruler can only name another living mortal as heir.")
    if not await active_bonds(ctx.session, [BondKind.RULES], sources=[ruler.id]):
        raise ValidationFailedError(f"{ruler.name} rules nothing that could be inherited.")
    row = await ctx.session.get(DesignatedHeirRow, ruler.id)
    if row is None:
        row = DesignatedHeirRow(ruler_entity_id=ruler.id, heir_entity_id=heir.id, epoch=ctx.epoch)
        ctx.session.add(row)
    else:
        row.heir_entity_id = heir.id
        row.epoch = ctx.epoch
    for profile in await ctx.session.scalars(
        select(PolityProfileRow)
        .join(OfficeRow, OfficeRow.polity_entity_id == PolityProfileRow.polity_entity_id)
        .where(OfficeRow.kind == OfficeKind.RULER, OfficeRow.holder_entity_id == ruler.id)
    ):
        profile.locked = profile.locked if "heir" in profile.locked else [*profile.locked, "heir"]
        designate = await ctx.session.scalar(
            select(OfficeRow).where(OfficeRow.polity_entity_id == profile.polity_entity_id, OfficeRow.kind == OfficeKind.HEIR_DESIGNATE).limit(1)
        )
        if designate is None:
            ctx.session.add(
                OfficeRow(
                    polity_entity_id=profile.polity_entity_id,
                    kind=OfficeKind.HEIR_DESIGNATE,
                    holder_entity_id=heir.id,
                    since_epoch=ctx.epoch,
                    powers=[],
                    locked=[],
                )
            )
        else:
            designate.holder_entity_id = heir.id
    await ctx.session.flush()
    return row
