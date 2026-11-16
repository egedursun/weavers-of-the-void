from collections.abc import Awaitable, Callable, Mapping

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.mind import CRAFT_SKILLS, SKILLS
from aerona.db.tables.culture import HolderLevelRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.mind import InspirationRow, SkillRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.body import ConditionKind, HarmCause
from aerona.domain.enums.culture import ItemClass
from aerona.domain.enums.economy import GoodsFlow
from aerona.domain.enums.entity import EntityType, MortalRole
from aerona.domain.enums.material import MaterialKind
from aerona.domain.enums.mind import InspirationKind, InspirationState, MoodState, PreferenceKind, SkillFamily, ThoughtKind
from aerona.domain.enums.renown import ReputationAxis
from aerona.domain.models.entity_stats import ItemStats
from aerona.engine.body.bands import banded
from aerona.engine.body.conditions import gain_condition
from aerona.engine.context import TickContext
from aerona.engine.economy.stocks import goods_of, lots_of
from aerona.engine.gods.queries import community_of
from aerona.engine.lore.items import profile_of
from aerona.engine.lore.research_depth import add_progress, research_choices
from aerona.engine.mind.preferences import favourite
from aerona.engine.mind.thoughts import think
from aerona.engine.notes import note
from aerona.engine.primitives.naming import seed_of
from aerona.engine.primitives.records import RecordSpec, create_record
from aerona.engine.primitives.stats import shift_stat
from aerona.engine.renown.deeds import acclaim_deed, best_craft

SEERS = frozenset({MortalRole.PRIEST, MortalRole.SAGE})
FIGHTERS = frozenset({MortalRole.WARRIOR, MortalRole.KNIGHT, MortalRole.HERO, MortalRole.CAPTAIN, MortalRole.HUNTER, MortalRole.OFFICER, MortalRole.PILOT})
FEVER_MATERIALS = (MaterialKind.GOLD, MaterialKind.SILVER, MaterialKind.IRON, MaterialKind.BRONZE, MaterialKind.STONE, MaterialKind.WOOD, MaterialKind.GLASS)
ITEM_POWER = 3


async def burning(session: AsyncSession, mortal_id: int, kind: InspirationKind | None = None) -> InspirationRow | None:
    statement = select(InspirationRow).where(InspirationRow.holder_node_id == mortal_id, InspirationRow.state == InspirationState.BURNING)
    if kind is not None:
        statement = statement.where(InspirationRow.kind == kind)
    return await session.scalar(statement.limit(1))


async def best_in(session: AsyncSession, mortal_id: int, family: SkillFamily) -> int:
    rows = await session.scalars(select(SkillRow).where(SkillRow.holder_node_id == mortal_id))
    return max((row.level for row in rows if SKILLS[row.skill].family is family), default=0)


async def kind_for(ctx: TickContext, mortal: EntityRow) -> InspirationKind | None:
    floor = ctx.rules.aspirations.inspiration_skill
    if await best_in(ctx.session, mortal.id, SkillFamily.CRAFT) >= floor:
        return InspirationKind.MASTERWORK_FEVER
    if await best_in(ctx.session, mortal.id, SkillFamily.KNOWLEDGE) >= floor:
        return InspirationKind.RESEARCH_INSIGHT
    if mortal.mortal_role in FIGHTERS:
        return InspirationKind.HEROIC_RESOLVE
    return await other_kind(ctx, mortal, floor)


async def other_kind(ctx: TickContext, mortal: EntityRow, floor: int) -> InspirationKind | None:
    if mortal.mortal_role is MortalRole.ENGINEER:
        return InspirationKind.TECHNICAL_BREAKTHROUGH
    if mortal.mortal_role in SEERS or await best_in(ctx.session, mortal.id, SkillFamily.FAITH) >= floor:
        return InspirationKind.SPIRITUAL_INSIGHT
    if await best_in(ctx.session, mortal.id, SkillFamily.SOCIAL) >= floor:
        return InspirationKind.ARTISTIC_VISION
    return None


async def fever_material(ctx: TickContext, mortal: EntityRow) -> str:
    loved = await favourite(ctx.session, mortal.id, PreferenceKind.MATERIAL)
    if loved is not None and loved.target in MaterialKind._value2member_map_:
        return loved.target
    return ctx.rng(seed_of("fever", mortal.id, ctx.epoch)).pick(list(FEVER_MATERIALS)).value


async def insight(ctx: TickContext, mortal: EntityRow, row: InspirationRow) -> None:
    community = await community_of(ctx.session, mortal)
    holder = community.id if community is not None else mortal.id
    rows = list(await ctx.session.scalars(select(HolderLevelRow).where(HolderLevelRow.holder_entity_id == holder)))
    open_rows = [level for level in rows if "progress" not in (level.locked or [])]
    if open_rows:
        target = min(open_rows, key=lambda level: (level.level, level.branch.value))
        target.progress += ctx.rules.aspirations.insight_progress
        row.result_node_id = holder
    row.state = InspirationState.FULFILLED


async def breakthrough(ctx: TickContext, mortal: EntityRow, row: InspirationRow) -> None:
    community = await community_of(ctx.session, mortal)
    holder = community.id if community is not None else mortal.id
    choices = await research_choices(ctx.session, holder)
    if choices:
        await add_progress(ctx, holder, choices[0], ctx.rules.aspirations.breakthrough_progress)
        row.result_node_id = holder
    row.state = InspirationState.FULFILLED


async def vision(ctx: TickContext, mortal: EntityRow, row: InspirationRow) -> None:
    shift_stat(mortal, "renown", ctx.rules.aspirations.vision_renown, 0)
    community = await community_of(ctx.session, mortal)
    if community is not None and not held(community.id):
        shift_stat(community, "prestige", ctx.rules.aspirations.vision_renown // 2, 0)
        row.result_node_id = community.id
    row.state = InspirationState.FULFILLED


async def revelation(ctx: TickContext, mortal: EntityRow, row: InspirationRow) -> None:
    shift_stat(mortal, "piety", ctx.rules.aspirations.vision_renown, 0)
    community = await community_of(ctx.session, mortal)
    if community is not None and not held(community.id):
        shift_stat(community, "piety", ctx.rules.aspirations.vision_renown // 2, 0)
        row.result_node_id = community.id
    row.state = InspirationState.FULFILLED


SUDDEN: Mapping[InspirationKind, Callable[[TickContext, EntityRow, InspirationRow], Awaitable[None]]] = {
    InspirationKind.TECHNICAL_BREAKTHROUGH: breakthrough,
    InspirationKind.ARTISTIC_VISION: vision,
    InspirationKind.SPIRITUAL_INSIGHT: revelation,
}


async def make_masterwork(ctx: TickContext, mortal: EntityRow, row: InspirationRow) -> bool:
    community = await community_of(ctx.session, mortal)
    if community is None or row.material is None:
        return False
    lots = [lot for lot in await lots_of(ctx.session, community.id) if lot.material is not None and lot.material.value == row.material and lot.quantity > 0]
    if not lots:
        return False
    if not await goods_of(ctx.session, ctx.epoch).shift_lot(lots[0], -1, GoodsFlow.INPUT):
        return False
    item = await create_record(
        ctx,
        RecordSpec(
            entity_type=EntityType.ITEM,
            name=f"The {row.material.replace('_', ' ').title()} Work of {mortal.name}",
            body=f"Made by {mortal.name} in a fever of inspiration.",
            stats=ItemStats(might=ctx.rules.aspirations.masterwork_quality),
            power=ITEM_POWER,
            location_id=community.id,
            world_id=community.world_id,
        ),
    )
    profile = await profile_of(ctx, item, ItemClass.JEWEL)
    profile.quality = ctx.rules.aspirations.masterwork_quality
    profile.maker_entity_id = mortal.id
    row.result_node_id = item.id
    row.state = InspirationState.FULFILLED
    await think(ctx.session, ctx.rules, mortal.id, ThoughtKind.MADE_MASTERWORK, ctx.epoch, subject_id=item.id)
    await note(ctx, f"In a fever of inspiration, {mortal.name} made {item.name}.", key="inspiration.masterwork", ids=[mortal.id, item.id])
    craft = await best_craft(ctx, mortal.id, CRAFT_SKILLS)
    await acclaim_deed(ctx, mortal.id, ReputationAxis.SKILL_RENOWN, ctx.rules.local_renown.masterwork_magnitude, place_id=community.id, skill=craft)
    return True


async def kindle(ctx: TickContext, mortal: EntityRow) -> str | None:
    profile = await ctx.session.get(MortalProfileRow, mortal.id)
    if profile is None or profile.mood is not MoodState.ELATED:
        return None
    if not ctx.rng(seed_of("inspiration", mortal.id, ctx.epoch)).chance(ctx.rules.aspirations.inspiration_pct):
        return None
    kind = await kind_for(ctx, mortal)
    if kind is None:
        return None
    row = InspirationRow(
        holder_node_id=mortal.id,
        kind=kind,
        material=await fever_material(ctx, mortal) if kind is InspirationKind.MASTERWORK_FEVER else None,
        started_epoch=ctx.epoch,
        deadline_epoch=ctx.epoch + ctx.rules.aspirations.inspiration_epochs,
        state=InspirationState.BURNING,
    )
    ctx.session.add(row)
    await ctx.session.flush()
    await think(ctx.session, ctx.rules, mortal.id, ThoughtKind.INSPIRED, ctx.epoch)
    if kind is InspirationKind.RESEARCH_INSIGHT:
        await insight(ctx, mortal, row)
        return "insight"
    if kind in SUDDEN:
        await SUDDEN[kind](ctx, mortal, row)
        return kind.value
    return "seized"


async def expire(ctx: TickContext, mortal: EntityRow, row: InspirationRow) -> str:
    if row.kind is InspirationKind.HEROIC_RESOLVE:
        row.state = InspirationState.FULFILLED
        return "resolve_spent"
    row.state = InspirationState.FAILED
    await think(ctx.session, ctx.rules, mortal.id, ThoughtKind.INSPIRATION_LOST, ctx.epoch)
    await gain_condition(ctx, mortal, ConditionKind.VISIONS, HarmCause.ACCIDENT, severity=banded(ctx, ctx.rules.harm_bands.failed_inspiration, mortal.id))
    return "failed"


async def tend_inspiration(ctx: TickContext, mortal: EntityRow) -> str | None:
    row = await burning(ctx.session, mortal.id)
    if row is None:
        return await kindle(ctx, mortal)
    if row.kind is InspirationKind.MASTERWORK_FEVER and await make_masterwork(ctx, mortal, row):
        return "masterwork"
    return await expire(ctx, mortal, row) if ctx.epoch >= row.deadline_epoch else None


async def resolute(session: AsyncSession, mortal_id: int) -> bool:
    return await burning(session, mortal_id, InspirationKind.HEROIC_RESOLVE) is not None
