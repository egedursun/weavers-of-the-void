from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.units import PERCENT
from aerona.db.tables.arcana import LawUpkeepRow
from aerona.db.tables.cosmos import CreatorRow
from aerona.db.tables.divine import NaturalLawProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.foreign_gods import ForeignGodRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.arcana import LawSource, SpellForm
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.divine import LawScope
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.society import NaturalLaw
from aerona.domain.models.entity_stats import NaturalLawStats
from aerona.engine.arcana.vis import burn_for
from aerona.engine.context import TickContext
from aerona.engine.notes import note
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.records import RecordSpec, create_record
from aerona.rules.registry import Rules

ENCHANTMENT_POWER = 5


def essence_upkeep(rules: Rules, strength: int, source: LawSource) -> int:
    per = rules.global_enchantments.essence_per_strength_pct if source is LawSource.ENCHANTMENT else rules.natural_laws.upkeep_essence
    return max(1, round_half_up(per * strength / PERCENT))


async def upkeep_row(session: AsyncSession, rules: Rules, law: NaturalLawProfileRow) -> LawUpkeepRow | None:
    row = await session.get(LawUpkeepRow, law.law_entity_id)
    if row is not None or law.author_node_id is None:
        return row
    row = LawUpkeepRow(
        law_entity_id=law.law_entity_id,
        caster_node_id=law.author_node_id,
        source=LawSource.AUTHORED,
        essence_upkeep=essence_upkeep(rules, law.strength, LawSource.AUTHORED),
        vis_upkeep=0,
        dispel_resistance=rules.global_enchantments.dispel_resistance,
        unpaid_epochs=0,
        since_epoch=0,
        locked=[],
    )
    session.add(row)
    return row


async def pay_essence(session: AsyncSession, rules: Rules, caster_id: int, amount: int) -> bool:
    floor = rules.natural_laws.author_existence_floor
    son = await session.get(SonRow, caster_id)
    if son is not None:
        if son.essence < amount or son.existence < floor:
            return False
        son.essence -= amount
        return True
    creator = await session.get(CreatorRow, caster_id)
    if creator is not None:
        if creator.essence < amount:
            return False
        creator.essence -= amount
        return True
    return await pay_power(session, rules, caster_id, amount)


async def pay_power(session: AsyncSession, rules: Rules, caster_id: int, amount: int) -> bool:
    foreign = await session.get(ForeignGodRow, caster_id)
    cost = max(1, round_half_up(amount * rules.global_enchantments.foreign_power_pct / PERCENT))
    if foreign is None or foreign.power - cost < rules.natural_laws.author_existence_floor:
        return False
    foreign.power -= cost
    return True


async def paid(ctx: TickContext, row: LawUpkeepRow) -> bool:
    if row.caster_node_id is None:
        return False
    if row.essence_upkeep and not await pay_essence(ctx.session, ctx.rules, row.caster_node_id, row.essence_upkeep):
        return False
    if row.vis_upkeep:
        caster = await ctx.session.get(EntityRow, row.caster_node_id)
        return caster is not None and await burn_for(ctx, caster, row.vis_form, row.vis_upkeep)
    return True


async def keep_law(ctx: TickContext, law: NaturalLawProfileRow) -> bool | None:
    row = await upkeep_row(ctx.session, ctx.rules, law)
    if row is None:
        return None
    if await paid(ctx, row):
        row.unpaid_epochs = 0
        return True
    row.unpaid_epochs += 1
    if row.source is LawSource.ENCHANTMENT and row.unpaid_epochs >= ctx.rules.global_enchantments.lapse_after:
        entity = await ctx.session.get(EntityRow, law.law_entity_id)
        if entity is not None and entity.status is EntityStatus.CANON:
            entity.status, entity.end_epoch = EntityStatus.DESTROYED, ctx.epoch
            await note(
                ctx, f"{entity.name} lapsed: no one kept paying for it.", key="arcana.enchantment_lapsed", ids=[entity.id], kind=ChronicleKind.COSMIC_LAW
            )
    return False


async def lay_enchantment(
    ctx: TickContext,
    caster: int,
    *,
    name: str,
    effect: NaturalLaw,
    world_id: int | None,
    region_id: int | None,
    strength: int,
    vis_form: SpellForm | None,
) -> NaturalLawProfileRow:
    table = ctx.rules.global_enchantments
    law = await create_record(
        ctx,
        RecordSpec(
            name=name,
            entity_type=EntityType.NATURAL_LAW,
            stats=NaturalLawStats(),
            body=f"A global enchantment laid and kept by its caster: {effect.value.replace('_', ' ')}.",
            power=ENCHANTMENT_POWER,
            world_id=world_id,
            natural_law=effect,
            pending=False,
        ),
    )
    scope = LawScope.REGION if region_id is not None else LawScope.WORLD if world_id is not None else LawScope.COSMOS
    profile = NaturalLawProfileRow(
        law_entity_id=law.id,
        effect=effect,
        scope=scope,
        world_id=world_id,
        region_entity_id=region_id,
        strength=clamp_int(strength, 0, PERCENT),
        stability=PERCENT,
        author_node_id=caster,
        updated_epoch=ctx.epoch,
        locked=[],
    )
    ctx.session.add(profile)
    mortal = await ctx.session.get(EntityRow, caster)
    ctx.session.add(
        LawUpkeepRow(
            law_entity_id=law.id,
            caster_node_id=caster,
            source=LawSource.ENCHANTMENT,
            essence_upkeep=0 if mortal is not None else essence_upkeep(ctx.rules, strength, LawSource.ENCHANTMENT),
            vis_form=vis_form if mortal is not None else None,
            vis_upkeep=table.vis_upkeep if mortal is not None else 0,
            dispel_resistance=table.dispel_resistance,
            unpaid_epochs=0,
            since_epoch=ctx.epoch,
            locked=[],
        )
    )
    await ctx.session.flush()
    await note(
        ctx, f"{law.name} was laid over the world as a global enchantment.", key="arcana.enchantment_laid", ids=[law.id, caster], kind=ChronicleKind.COSMIC_LAW
    )
    return profile
