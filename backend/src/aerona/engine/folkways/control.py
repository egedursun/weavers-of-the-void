from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.core.errors import ValidationFailedError
from aerona.db.base import Base
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.folkways import (
    ACCUSATION_FIELDS,
    BIAS_FIELDS,
    CHARM_FIELDS,
    DIET_FIELDS,
    HUNT_FIELDS,
    IMPURITY_FIELDS,
    LUCK_FIELDS,
    MISHAP_FIELDS,
    NEED_FIELDS,
    PURIFICATION_FIELDS,
    PURITY_FIELDS,
    RANK_FIELDS,
    SCORE_FIELDS,
    AccusationRow,
    BiasWeightRow,
    CharmRow,
    DietRow,
    ImpuritySourceRow,
    LuckBeliefRow,
    MishapRow,
    NutrientNeedRow,
    NutritionScoreRow,
    PurificationRow,
    PurityRankRow,
    PurityRow,
    WitchHuntRow,
)
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.folkways import CharmPower, DecisionBias, ImpuritySource, LuckReach, LuckSign, MishapKind, Nutrient, Purification, PurityState
from aerona.domain.enums.kind_crafts import ColourFocus
from aerona.domain.enums.mind import Profession
from aerona.engine.body.customs import people_of
from aerona.engine.collective.control import of_type, saved
from aerona.engine.context import TickContext
from aerona.engine.cycles.control import node_exists
from aerona.engine.divine.control import apply
from aerona.engine.folkways.biases import BiasTally, derive
from aerona.engine.folkways.mishaps import MishapTally, answer, attribute, is_real
from aerona.engine.folkways.nutrition import NutritionTally, keep_nutrition
from aerona.engine.folkways.purity import purity_of
from aerona.engine.folkways.witchcraft import WitchTally, accuse
from aerona.engine.gatherings.control import Values, allowed, found

PEOPLES = frozenset({EntityType.PEOPLE})
TOWNS = frozenset({EntityType.SETTLEMENT})
MORTALS = frozenset({EntityType.MORTAL})
ITEMS = frozenset({EntityType.ITEM})


async def set_diet(ctx: TickContext, holder_id: int, values: Values) -> DietRow:
    await node_exists(ctx, holder_id, "holder")
    row = await ctx.session.get(DietRow, holder_id) or await saved(ctx, DietRow(holder_node_id=holder_id, updated_epoch=ctx.epoch, locked=[]))
    apply(row, allowed(values, DIET_FIELDS, "diet"), [])
    await ctx.session.flush()
    return row


async def set_need(ctx: TickContext, people_id: int, nutrient: Nutrient, weight: int) -> NutrientNeedRow:
    await of_type(ctx, people_id, PEOPLES, "a people")
    row = await ctx.session.get(NutrientNeedRow, (people_id, nutrient)) or await saved(
        ctx, NutrientNeedRow(people_entity_id=people_id, nutrient=nutrient, locked=[])
    )
    apply(row, {"weight": weight}, [])
    await ctx.session.flush()
    return row


async def set_score(ctx: TickContext, holder_id: int, values: Values) -> NutritionScoreRow:
    await node_exists(ctx, holder_id, "holder")
    row = await ctx.session.get(NutritionScoreRow, holder_id) or await saved(
        ctx, NutritionScoreRow(holder_node_id=holder_id, updated_epoch=ctx.epoch, locked=[])
    )
    apply(row, allowed(values, SCORE_FIELDS, "nutrition score"), [])
    await ctx.session.flush()
    return row


async def feed_now(ctx: TickContext) -> NutritionTally:
    tally = NutritionTally()
    await keep_nutrition(ctx, tally)
    return tally


async def set_bias(ctx: TickContext, holder_id: int, bias: DecisionBias, weight: int) -> BiasWeightRow:
    await node_exists(ctx, holder_id, "holder")
    row = await ctx.session.get(BiasWeightRow, (holder_id, bias)) or await saved(
        ctx, BiasWeightRow(holder_node_id=holder_id, bias=bias, last_shift=0, locked=[])
    )
    apply(row, {"weight": weight}, [])
    await ctx.session.flush()
    return row


async def read_biases(ctx: TickContext, holder_id: int) -> int:
    await node_exists(ctx, holder_id, "holder")
    tally = BiasTally()
    rows = await derive(ctx, holder_id, tally)
    if not rows:
        raise ValidationFailedError("It has no character to read biases from; only mortals and gods decide.")
    await ctx.session.flush()
    return len(rows)


async def set_purity(ctx: TickContext, mortal_id: int, values: Values) -> PurityRow:
    await of_type(ctx, mortal_id, MORTALS, "a mortal")
    row = await purity_of(ctx, mortal_id)
    await ctx.session.flush()
    rank = values.get("rank_id")
    if rank is not None and await ctx.session.get(PurityRankRow, rank) is None:
        raise ValidationFailedError("No such rank.")
    apply(row, allowed(values, PURITY_FIELDS, "purity"), [])
    await ctx.session.flush()
    return row


async def cleanse(ctx: TickContext, mortal_id: int) -> PurityRow:
    mortal = await of_type(ctx, mortal_id, MORTALS, "a mortal")
    row = await purity_of(ctx, mortal_id)
    if row.state is PurityState.PURE:
        raise ValidationFailedError(f"{mortal.name} is already pure.")
    row.state, row.source, row.until_epoch, row.since_epoch = PurityState.PURE, None, None, ctx.epoch
    row.locked = [field for field in row.locked if field != "state"]
    await ctx.session.flush()
    return row


async def set_source(ctx: TickContext, people_id: int, source: ImpuritySource, weight: int, lasts: int) -> ImpuritySourceRow:
    await of_type(ctx, people_id, PEOPLES, "a people")
    row = await ctx.session.get(ImpuritySourceRow, (people_id, source)) or await saved(
        ctx, ImpuritySourceRow(people_entity_id=people_id, source=source, locked=[])
    )
    apply(row, {"weight": weight, "lasts": lasts}, [])
    await ctx.session.flush()
    return row


async def set_method(ctx: TickContext, people_id: int, method: Purification, values: Values) -> PurificationRow:
    await of_type(ctx, people_id, PEOPLES, "a people")
    row = await ctx.session.get(PurificationRow, (people_id, method)) or await saved(ctx, PurificationRow(people_entity_id=people_id, method=method, locked=[]))
    apply(row, allowed(values, PURIFICATION_FIELDS, "purification"), [])
    await ctx.session.flush()
    return row


async def add_rank(ctx: TickContext, people_id: int, name: str, standing: int, professions: list[str]) -> PurityRankRow:
    await of_type(ctx, people_id, PEOPLES, "a people")
    if await ctx.session.scalar(select(PurityRankRow.id).where(PurityRankRow.people_entity_id == people_id, PurityRankRow.name == name)) is not None:
        raise ValidationFailedError(f"A rank named {name} already exists.")
    return await saved(ctx, PurityRankRow(people_entity_id=people_id, name=name, standing=standing, professions=professions, locked=[]))


async def rank_profession(ctx: TickContext, rank_id: int, profession: Profession, *, member: bool) -> PurityRankRow:
    row = await found(ctx, PurityRankRow, rank_id, "rank")
    jobs = [job for job in row.professions if job != profession.value]
    row.professions = [*jobs, profession.value] if member else jobs
    row.locked = sorted({*row.locked, "professions"})
    await ctx.session.flush()
    return row


async def add_mishap(ctx: TickContext, town_id: int, kind: MishapKind, victim_id: int | None, cause_id: int | None) -> MishapRow:
    town = await of_type(ctx, town_id, TOWNS, "a town")
    for node, label in ((victim_id, "victim"), (cause_id, "cause")):
        if node is not None:
            await node_exists(ctx, node, label)
    cause = await ctx.session.get(EntityRow, cause_id) if cause_id is not None else None
    row = await saved(
        ctx,
        MishapRow(
            settlement_entity_id=town.id,
            victim_node_id=victim_id,
            cause_node_id=cause_id,
            kind=kind,
            true_cause=f"the hand of {cause.name}" if cause is not None else "a hand from beyond",
            explained=False,
            epoch=ctx.epoch,
            locked=[],
        ),
    )
    await attribute(ctx, town, row, await people_of(ctx.session, town))
    await answer(ctx, town, row, MishapTally())
    await ctx.session.flush()
    return row


async def add_belief(
    ctx: TickContext,
    people_id: int,
    sign: LuckSign,
    reach: LuckReach,
    *,
    lucky: bool,
    name: str,
    species_id: int | None = None,
    colour: ColourFocus | None = None,
) -> LuckBeliefRow:
    await of_type(ctx, people_id, PEOPLES, "a people")
    if sign is LuckSign.ANIMAL and species_id is None:
        raise ValidationFailedError("A sign read in a creature names the kind of creature.")
    if sign is LuckSign.COLOUR and colour is None:
        raise ValidationFailedError("A sign read in a colour names the colour.")
    if species_id is not None:
        await node_exists(ctx, species_id, "kind of creature")
    row = LuckBeliefRow(
        people_entity_id=people_id,
        sign=sign,
        reach=reach,
        lucky=lucky,
        name=name,
        species_entity_id=species_id if sign is LuckSign.ANIMAL else None,
        colour=colour if sign is LuckSign.COLOUR else None,
        locked=[],
    )
    return await saved(ctx, row)


async def set_charm(ctx: TickContext, item_id: int, power: CharmPower, strength: int) -> CharmRow:
    await of_type(ctx, item_id, ITEMS, "an item")
    row = await ctx.session.get(CharmRow, item_id) or await saved(
        ctx, CharmRow(item_entity_id=item_id, power=power, real=await is_real(ctx, item_id), locked=[])
    )
    apply(row, {"power": power, "strength": strength}, [])
    await ctx.session.flush()
    return row


async def accuse_by_hand(ctx: TickContext, town_id: int, accuser_id: int | None, mishap_id: int | None) -> AccusationRow:
    town = await of_type(ctx, town_id, TOWNS, "a town")
    accuser = await of_type(ctx, accuser_id, MORTALS, "a mortal") if accuser_id is not None else None
    mishap = await found(ctx, MishapRow, mishap_id, "misfortune") if mishap_id is not None else None
    row = await accuse(ctx, town, accuser, WitchTally(), mishap=mishap)
    if row is None:
        raise ValidationFailedError(f"No one in {town.name} can be accused.")
    return row


async def start_hunt(ctx: TickContext, town_id: int, fervour: int) -> WitchHuntRow:
    town = await of_type(ctx, town_id, TOWNS, "a town")
    if await ctx.session.scalar(select(WitchHuntRow.id).where(WitchHuntRow.settlement_entity_id == town.id, WitchHuntRow.ended_epoch.is_(None))) is not None:
        raise ValidationFailedError(f"A witch hunt already burns in {town.name}.")
    return await saved(ctx, WitchHuntRow(settlement_entity_id=town.id, fervour=max(0, min(PERCENT, fervour)), started_epoch=ctx.epoch, locked=[]))


EDITABLE: dict[str, tuple[type[Base], tuple[str, ...], str]] = {
    "diet": (DietRow, DIET_FIELDS, "diet"),
    "nutrient_need": (NutrientNeedRow, NEED_FIELDS, "nutrient need"),
    "nutrition_score": (NutritionScoreRow, SCORE_FIELDS, "nutrition score"),
    "bias_weight": (BiasWeightRow, BIAS_FIELDS, "bias"),
    "purity": (PurityRow, PURITY_FIELDS, "purity"),
    "impurity_source": (ImpuritySourceRow, IMPURITY_FIELDS, "source of impurity"),
    "purification": (PurificationRow, PURIFICATION_FIELDS, "purification"),
    "purity_rank": (PurityRankRow, RANK_FIELDS, "rank"),
    "mishap": (MishapRow, MISHAP_FIELDS, "misfortune"),
    "luck_belief": (LuckBeliefRow, LUCK_FIELDS, "belief about luck"),
    "charm": (CharmRow, CHARM_FIELDS, "charm"),
    "accusation": (AccusationRow, ACCUSATION_FIELDS, "accusation"),
    "witch_hunt": (WitchHuntRow, HUNT_FIELDS, "witch hunt"),
}


async def edit_record(ctx: TickContext, kind: str, key: object, values: Values, release: list[str]) -> Base:
    table, fields, label = EDITABLE[kind]
    row = apply(await found(ctx, table, key, label), allowed(values, fields, label), release)
    await ctx.session.flush()
    return row


async def delete_record(ctx: TickContext, kind: str, key: object) -> None:
    table, _, label = EDITABLE[kind]
    await ctx.session.delete(await found(ctx, table, key, label))
    await ctx.session.flush()
