from sqlalchemy import select

from aerona.catalog.knowledge import NATURAL_LAWS
from aerona.constants.units import PERCENT
from aerona.db.tables.body import ConditionRow
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.cosmos import CreatorRow
from aerona.db.tables.divine import AvatarRow, NaturalLawProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.sons import SonRow
from aerona.db.write_guard import held
from aerona.domain.enums.body import ConditionKind
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.divine import LawException, LawScope
from aerona.domain.enums.entity import HERO_ROLES, EntityOrigin, EntityStatus, EntityType, MortalRole
from aerona.domain.enums.society import NaturalLaw
from aerona.engine.context import TickContext
from aerona.engine.divine.gods import god_of
from aerona.engine.notes import note
from aerona.engine.primitives.numbers import clamp_int, clamp_percent

L = NaturalLaw
CONTRADICTIONS: tuple[frozenset[NaturalLaw], ...] = (
    frozenset({L.IMMORTALITY, L.SHORT_LIFE}),
    frozenset({L.BOUNTY, L.DROUGHT}),
    frozenset({L.GIFT_FLOWERING, L.GIFT_WITHERING}),
    frozenset({L.DEAD_RETURN, L.SOULS_REINCARNATE}),
    frozenset({L.WAR_BAN, L.DISASTERS}),
)


async def profile_for(ctx: TickContext, law: EntityRow) -> NaturalLawProfileRow | None:
    if law.natural_law is None or law.natural_law is NaturalLaw.NONE:
        return None
    row = await ctx.session.get(NaturalLawProfileRow, law.id)
    if row is not None:
        return row
    table = ctx.rules.natural_laws
    creator = await ctx.session.scalar(select(CreatorRow.id).limit(1))
    author = law.creator_son_id if law.creator_son_id is not None else creator if law.origin is EntityOrigin.CREATOR else None
    row = NaturalLawProfileRow(
        law_entity_id=law.id,
        effect=law.natural_law,
        scope=LawScope.WORLD,
        world_id=law.world_id,
        strength=table.start_strength,
        stability=table.start_stability,
        author_node_id=author,
        exception=LawException.NONE,
        contested=False,
        updated_epoch=ctx.epoch,
        locked=[],
    )
    ctx.session.add(row)
    await ctx.session.flush()
    return row


async def upkeep(ctx: TickContext, row: NaturalLawProfileRow) -> bool:
    table = ctx.rules.natural_laws
    cost = max(1, round(table.upkeep_essence * row.strength / PERCENT))
    author = await god_of(ctx.session, row.author_node_id)
    if isinstance(author, SonRow):
        if author.essence >= cost and author.existence >= table.author_existence_floor:
            author.essence -= cost
            return True
        return False
    creator = await ctx.session.get(CreatorRow, row.author_node_id) if row.author_node_id is not None else None
    if creator is not None:
        if creator.essence >= cost:
            creator.essence -= cost
            return True
        return False
    return author is not None and author.power >= table.author_existence_floor


def overlap(first: NaturalLawProfileRow, second: NaturalLawProfileRow) -> bool:
    if LawScope.COSMOS in {first.scope, second.scope}:
        return True
    if first.scope is LawScope.REGION and second.scope is LawScope.REGION:
        return first.region_entity_id == second.region_entity_id
    return first.world_id == second.world_id


async def contest(ctx: TickContext, rows: list[NaturalLawProfileRow]) -> int:
    table = ctx.rules.natural_laws
    clashes = 0
    for row in rows:
        if "contested" not in row.locked:
            row.contested = False
    for index, first in enumerate(rows):
        for second in rows[index + 1 :]:
            if frozenset({first.effect, second.effect}) not in CONTRADICTIONS or not overlap(first, second):
                continue
            clashes += 1
            gap = first.strength - second.strength
            if abs(gap) <= table.stalemate_margin:
                for row in (first, second):
                    if "contested" not in row.locked:
                        row.contested = True
                world = await ctx.session.get(WorldRow, first.world_id or second.world_id) if (first.world_id or second.world_id) else None
                if world is not None:
                    world.leakage = clamp_percent(world.leakage + table.clash_leak)
                continue
            weaker = second if gap > 0 else first
            if "stability" not in weaker.locked:
                weaker.stability = clamp_int(weaker.stability - table.contest_erosion, 0, PERCENT)
    return clashes


async def tend_laws(ctx: TickContext) -> int:
    table = ctx.rules.natural_laws
    laws = list(
        await ctx.session.scalars(
            select(EntityRow).where(EntityRow.entity_type == EntityType.NATURAL_LAW, EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id)
        )
    )
    rows: list[NaturalLawProfileRow] = []
    for law in laws:
        row = await profile_for(ctx, law)
        if row is None:
            continue
        rows.append(row)
        if held(law.id):
            continue
        if not await upkeep(ctx, row) and "stability" not in row.locked:
            row.stability = clamp_int(row.stability - table.stability_decay, 0, PERCENT)
        if row.stability <= 0 and "strength" not in row.locked:
            row.strength = clamp_int(row.strength - table.strength_decay, 0, PERCENT)
            if row.strength <= 0:
                law.status, law.end_epoch = EntityStatus.DESTROYED, ctx.epoch
                await note(
                    ctx,
                    f"{law.name} was unmade: {NATURAL_LAWS[row.effect].label.lower()} no longer holds.",
                    key="divine.law_unmade",
                    ids=[law.id],
                    kind=ChronicleKind.COSMIC_LAW,
                )
        row.updated_epoch = ctx.epoch
    await contest(ctx, [row for row in rows if row.strength > 0])
    await ctx.session.flush()
    return len(rows)


async def exempt(ctx: TickContext, entity: EntityRow, law: NaturalLaw) -> bool:
    rows = await ctx.session.scalars(
        select(NaturalLawProfileRow).where(NaturalLawProfileRow.effect == law, NaturalLawProfileRow.exception != LawException.NONE)
    )
    for row in rows:
        if row.exception is LawException.HEROES and entity.mortal_role in HERO_ROLES:
            return True
        if row.exception is LawException.AVATARS and await ctx.session.get(AvatarRow, entity.id) is not None:
            return True
        if row.exception is LawException.CREATOR_CHOSEN:
            marked = await ctx.session.scalar(
                select(ConditionRow.id).where(
                    ConditionRow.bearer_node_id == entity.id, ConditionRow.kind == ConditionKind.CHOSEN_MARK, ConditionRow.ended_epoch.is_(None)
                )
            )
            if marked is not None or entity.mortal_role is MortalRole.CHOSEN:
                return True
        if row.exception is LawException.AUTHOR_WORSHIPPERS and row.author_node_id is not None:
            gods, _ = await (await ctx.divine()).faithful_of(ctx.session, entity.id)
            if row.author_node_id in gods:
                return True
    return False


async def binds(ctx: TickContext, law: NaturalLaw, entity: EntityRow) -> bool:
    laws = await ctx.laws()
    return laws.has(law, entity.world_id) and not await exempt(ctx, entity, law)
