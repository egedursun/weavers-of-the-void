from dataclasses import dataclass, field

from sqlalchemy import select

from aerona.catalog.goods_traits import materials_with
from aerona.catalog.life.constructs import MAKE_CONSTRUCT_COMMAND_TOKENS, MAKING_SKILLS, TOKEN_CLASS
from aerona.catalog.materials import MATERIALS
from aerona.constants.units import PERCENT
from aerona.core.grammar import spoken
from aerona.db.tables.constructs import ConstructRow, InstructionOrderRow, InstructionSetRow
from aerona.db.tables.ecology import BeastProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.faith import SpiritProfileRow
from aerona.db.tables.mind import SkillRow
from aerona.db.write_guard import held
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.constructs import CommandToken, InstructionBinding, MindWill, OrderCondition, OrderKind
from aerona.domain.enums.culture import MagicSource
from aerona.domain.enums.ecology import BeastTemper, SizeClass
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.faith import AfterlifeState, BindingKind
from aerona.domain.enums.goods_traits import MaterialTrait
from aerona.domain.enums.material import MaterialKind
from aerona.domain.enums.mind import SkillKind
from aerona.domain.enums.minds import MindAffect, MindMaking, MindPurpose, MindSeat, MindUpkeep
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.society import KnowledgeBranch
from aerona.domain.enums.transform import TransformKind
from aerona.domain.models.entity_stats import BeastStats, ItemStats
from aerona.engine.body.customs import people_id_of
from aerona.engine.context import TickContext
from aerona.engine.lore.items import profile_of
from aerona.engine.mind.book import skill_level
from aerona.engine.minds.making import Making, make_mind
from aerona.engine.primitives.knowledge import KnowledgeMap
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import connect
from aerona.engine.primitives.quota import WorldQuota
from aerona.engine.primitives.records import RecordSpec, create_record
from aerona.engine.recording.record import record
from aerona.engine.sacred.places import town_of
from aerona.engine.transform.record import record_transformation

CONSTRUCT = "construct"
SKILL_FLOOR = 3
AGELESS = 1_000_000
BODIES = materials_with(MaterialTrait.CONSTRUCT_BODY)
SOURCE_POWER = {
    MagicSource.LEY: 80,
    MagicSource.DIVINE: 75,
    MagicSource.BLOOD: 85,
    MagicSource.SOUL: 90,
    MagicSource.REAGENT: 70,
    MagicSource.VOID: 100,
}
DEFAULT_ORDERS = ((OrderKind.OBEY_HOLDER, 1), (OrderKind.GUARD, 2))


@dataclass
class Design:
    material: MaterialKind | None = None
    source: MagicSource | None = None
    token: CommandToken | None = None
    binding: InstructionBinding = InstructionBinding.ORDER
    orders: list[tuple[OrderKind, int | None]] = field(default_factory=list)
    name: str | None = None


@dataclass
class MakingTally:
    made: int = 0
    souled: int = 0


async def body_material(ctx: TickContext, maker: EntityRow) -> MaterialKind:
    knowledge = await KnowledgeMap.load(ctx.session)
    town = await town_of(ctx.session, maker)
    holders = [holder for holder in (town.id if town else None, await people_id_of(ctx.session, town)) if holder is not None]
    level = max((knowledge.level(holder, KnowledgeBranch.METALLURGY) for holder in holders), default=0)
    reachable = [kind for kind in BODIES if MATERIALS[kind].level <= level]
    return max(reachable or [MaterialKind.CLAY], key=lambda kind: (MATERIALS[kind].hardness, kind.value))


def body_source(ctx: TickContext, maker: EntityRow) -> MagicSource:
    return ctx.rng(f"construct.source.{maker.id}.{ctx.epoch}").pick(list(MagicSource))


async def bind_soul(ctx: TickContext, row: ConstructRow, body: EntityRow, maker: EntityRow) -> bool:
    places = [place for place in (maker.location_id, (await town_of(ctx.session, maker) or maker).location_id) if place is not None]
    found = await ctx.session.scalar(
        select(SpiritProfileRow)
        .join(EntityRow, EntityRow.id == SpiritProfileRow.spirit_entity_id)
        .where(
            EntityRow.status == EntityStatus.CANON,
            EntityRow.location_id.in_(places),
            SpiritProfileRow.binding == BindingKind.NONE,
            SpiritProfileRow.state == AfterlifeState.WANDERING,
            SpiritProfileRow.sealed.is_(False),
        )
        .order_by(SpiritProfileRow.spirit_entity_id)
        .limit(1)
    )
    if found is None or held(found.spirit_entity_id) or "binding" in found.locked:
        return False
    found.binding, found.bound_entity_id = BindingKind.BEAST, body.id
    row.soul_entity_id = found.spirit_entity_id
    return True


async def token_item(ctx: TickContext, maker: EntityRow, construct: EntityRow, token: CommandToken) -> int | None:
    item_class = TOKEN_CLASS.get(token)
    if item_class is None:
        return None
    item = await create_record(
        ctx,
        RecordSpec(
            entity_type=EntityType.ITEM,
            name=f"Command {spoken(item_class)} of {construct.name}",
            body=f"Whoever holds it commands {construct.name}.",
            stats=ItemStats(),
            power=1,
            location_id=maker.location_id,
            world_id=maker.world_id,
            maker_entity_id=maker.id,
        ),
    )
    await profile_of(ctx, item, item_class)
    await connect(ctx.session, maker.id, item.id, BondKind.OWNS, ctx.epoch, description="made to command a construct")
    return item.id


def token_for(token: CommandToken, maker: EntityRow) -> int | None:
    return maker.affiliated_entity_id if token is CommandToken.OFFICE else None


async def make_construct(ctx: TickContext, maker: EntityRow, design: Design) -> ConstructRow:
    material = design.material or await body_material(ctx, maker)
    source = design.source or body_source(ctx, maker)
    token = design.token or ctx.rng(f"construct.token.{maker.id}.{ctx.epoch}").pick(MAKE_CONSTRUCT_COMMAND_TOKENS)
    spec = MATERIALS[material]
    body = await create_record(
        ctx,
        RecordSpec(
            entity_type=EntityType.BEAST,
            name=design.name or f"{spec.label} construct of {maker.name}",
            body=f"A body of {spec.label.lower()} made by {maker.name} and moved by {spoken(source)} power.",
            stats=BeastStats(hp=spec.toughness * 2, danger=spec.hardness, strength=spec.hardness, agility=PERCENT - spec.weight),
            power=max(1, maker.power_level),
            location_id=maker.location_id,
            world_id=maker.world_id,
            subtype=CONSTRUCT,
            maker_entity_id=maker.id,
        ),
    )
    ctx.session.add(
        BeastProfileRow(
            beast_entity_id=body.id,
            species_entity_id=None,
            endurance=clamp_int(spec.toughness, 0, PERCENT),
            perception=PERCENT // 4,
            willpower=PERCENT,
            intelligence=0,
            age=0,
            lifespan=AGELESS,
            size_class=SizeClass.LARGE,
            lair_place_id=None,
            temper=BeastTemper.BOUND,
            bound_to_node_id=maker.id,
            hoard={},
            raids=0,
            woke_epoch=None,
            updated_epoch=ctx.epoch,
            locked=[],
        )
    )
    row = ConstructRow(
        entity_id=body.id,
        material=material,
        power_source=source,
        power=SOURCE_POWER[source],
        upkeep=ctx.rules.constructs.upkeep * (2 if source is MagicSource.VOID else 1),
        maker_entity_id=maker.id,
        soul_entity_id=None,
        made_epoch=ctx.epoch,
        locked=[],
    )
    ctx.session.add(row)
    await ctx.session.flush()
    method = MindMaking.SUMMONING if source is MagicSource.SOUL else MindMaking.CRAFT
    making = Making(
        method,
        MindSeat.BODY,
        body.id,
        MindWill.INSTRUCTED,
        MindPurpose.SERVANT,
        MindAffect.NONE,
        MindUpkeep.MAINTENANCE,
        skill=await skill_level(ctx.session, maker.id, SkillKind.SPELLCRAFT),
    )
    await make_mind(ctx, body.id, maker.id, making)
    await record_transformation(ctx, TransformKind.CONSTRUCT, None, body.id)
    if source is MagicSource.SOUL:
        await bind_soul(ctx, row, body, maker)
    token_id = await token_item(ctx, maker, body, token) or token_for(token, maker)
    rules = InstructionSetRow(
        owner_entity_id=body.id,
        binding=design.binding,
        command_token=token,
        token_entity_id=token_id,
        holder_node_id=maker.id,
        kill_switch=False,
        literalness=clamp_int(round_half_up(PERCENT - spec.hardness / 2), 0, PERCENT),
        locked=[],
    )
    ctx.session.add(rules)
    await ctx.session.flush()
    town = await town_of(ctx.session, maker)
    for kind, priority in design.orders or [(kind, priority) for kind, priority in DEFAULT_ORDERS]:
        ctx.session.add(
            InstructionOrderRow(
                set_id=rules.id,
                kind=kind,
                target_node_id=town.id if town is not None and kind is not OrderKind.OBEY_HOLDER else None,
                priority=priority or 1,
                condition=OrderCondition.ALWAYS,
                locked=[],
            )
        )
    await connect(ctx.session, maker.id, body.id, BondKind.OWNS, ctx.epoch, description="made")
    await ctx.session.flush()
    return row


async def skilled_makers(ctx: TickContext) -> list[EntityRow]:
    rows = await ctx.session.scalars(
        select(EntityRow)
        .join(SkillRow, SkillRow.holder_node_id == EntityRow.id)
        .where(
            EntityRow.entity_type == EntityType.MORTAL,
            EntityRow.status == EntityStatus.CANON,
            SkillRow.skill.in_(list(MAKING_SKILLS)),
            SkillRow.subject_node_id.is_(None),
            SkillRow.level >= SKILL_FLOOR,
        )
        .order_by(SkillRow.level.desc(), EntityRow.id)
    )
    return list({row.id: row for row in rows}.values())


async def knows_making(ctx: TickContext, knowledge: KnowledgeMap, maker: EntityRow) -> bool:
    town = await town_of(ctx.session, maker)
    holders = [holder for holder in (town.id if town else None, await people_id_of(ctx.session, town)) if holder is not None]
    return any(knowledge.level(holder, KnowledgeBranch.MAGIC) >= ctx.rules.constructs.maker_magic for holder in holders)


async def make_constructs(ctx: TickContext, tally: MakingTally) -> None:
    table = ctx.rules.constructs
    knowledge = await KnowledgeMap.load(ctx.session)
    quota = WorldQuota(table.constructs_per_epoch)
    for maker in await skilled_makers(ctx):
        if quota.full(maker.world_id):
            continue
        if held(maker.id) or not ctx.rng(f"construct.make.{maker.id}.{ctx.epoch}").chance(table.make_chance):
            continue
        if not await knows_making(ctx, knowledge, maker):
            continue
        row = await make_construct(ctx, maker, Design())
        quota.take(maker.world_id)
        tally.made += 1
        tally.souled += row.soul_entity_id is not None
        await record(
            ctx,
            "construct.made",
            roles={IncidentRole.MAKER: maker.id, IncidentRole.PRODUCT: row.entity_id},
            facts={"material": row.material, "power_source": row.power_source, "power": row.power, "souled": int(row.soul_entity_id is not None)},
            place=maker.location_id,
        )
