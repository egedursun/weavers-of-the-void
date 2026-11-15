from collections import defaultdict
from collections.abc import Mapping
from dataclasses import dataclass

from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.db.tables.ages import IrregularSeasonRow
from aerona.db.tables.agrarian import FamineLoreRow
from aerona.db.tables.body import SEVERITY_MAX, SEVERITY_MIN
from aerona.db.tables.demography import PeopleBiologyRow
from aerona.db.tables.economy import CommunityStockRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.folkways import DietRow, NutrientNeedRow, NutritionScoreRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.ages import SeasonSpell
from aerona.domain.enums.body import ConditionKind, HarmCause
from aerona.domain.enums.demography import FolkDiet
from aerona.domain.enums.ecology import Biochemistry
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.folkways import Nutrient
from aerona.domain.enums.mind import Attribute, PressureKind
from aerona.domain.enums.mortal import LifeStage
from aerona.domain.enums.society import KnowledgeBranch, NaturalLaw, SocialClass
from aerona.engine.body.conditions import end_condition, gain_condition
from aerona.engine.body.customs import people_id_of, people_of
from aerona.engine.context import TickContext
from aerona.engine.mind.book import pressures_of
from aerona.engine.mind.split import MIDPOINT, attributes_of, has_attributes, store_attributes
from aerona.engine.mortal.profile import is_held
from aerona.engine.primitives.folk import present_in
from aerona.engine.primitives.knowledge import branch_level
from aerona.engine.primitives.numbers import clamp_int, round_half_up

SHARES = ("staple", "protein", "fat", "fresh", "mineral")
GROUPS: Mapping[str, frozenset[CommodityKind]] = {
    "staple": frozenset({CommodityKind.GRAIN, CommodityKind.BREAD, CommodityKind.TUBERS}),
    "protein": frozenset({CommodityKind.MEAT, CommodityKind.FISH, CommodityKind.EGGS, CommodityKind.LIVESTOCK}),
    "fat": frozenset({CommodityKind.MILK, CommodityKind.CHEESE}),
    "fresh": frozenset({CommodityKind.FRUIT, CommodityKind.HERBS}),
    "mineral": frozenset({CommodityKind.FISH, CommodityKind.HERBS}),
}
SPECIAL = frozenset({CommodityKind.LUXURIES, CommodityKind.MAGICAL_REAGENTS})
NEEDS: Mapping[FolkDiet, tuple[Nutrient, ...]] = {
    FolkDiet.OMNIVORE: (Nutrient.ENERGY, Nutrient.PROTEIN, Nutrient.FAT, Nutrient.FRESH, Nutrient.MINERAL),
    FolkDiet.HERBIVORE: (Nutrient.ENERGY, Nutrient.FRESH, Nutrient.MINERAL),
    FolkDiet.CARNIVORE: (Nutrient.ENERGY, Nutrient.PROTEIN, Nutrient.FAT, Nutrient.MINERAL),
    FolkDiet.PISCIVORE: (Nutrient.ENERGY, Nutrient.PROTEIN, Nutrient.FAT, Nutrient.MINERAL),
    FolkDiet.SCAVENGER: (Nutrient.ENERGY, Nutrient.PROTEIN, Nutrient.MINERAL),
    FolkDiet.SANGUIVORE: (Nutrient.ENERGY, Nutrient.PROTEIN),
    FolkDiet.LITHOVORE: (Nutrient.ENERGY, Nutrient.MINERAL),
    FolkDiet.ESSENCE_FEEDER: (Nutrient.ENERGY, Nutrient.ESSENCE),
    FolkDiet.PHOTOTROPH: (Nutrient.ENERGY, Nutrient.LIGHT, Nutrient.MINERAL),
}
CHARGED = frozenset({Biochemistry.CRYSTAL, Biochemistry.SILICON})
ELITE = frozenset({SocialClass.NOBLE, SocialClass.PRIEST, SocialClass.MERCHANT, SocialClass.PROFESSIONAL})
LOWLY = frozenset({SocialClass.SERF_OR_SLAVE, SocialClass.OUTCAST})
YOUNG = frozenset({LifeStage.INFANT, LifeStage.CHILD, LifeStage.YOUTH})
STATURE = (Attribute.STRENGTH, Attribute.TOUGHNESS)
COGNITION = (Attribute.ANALYTICAL_ABILITY, Attribute.MEMORY)


@dataclass
class NutritionTally:
    diets: int = 0
    scored: int = 0
    deficient: int = 0
    grown: int = 0


def needs_for(biology: PeopleBiologyRow | None) -> tuple[Nutrient, ...]:
    if biology is None:
        return NEEDS[FolkDiet.OMNIVORE]
    found = NEEDS[biology.diet]
    return (*found, Nutrient.CHARGE) if biology.biochemistry in CHARGED else found


async def needs_of(ctx: TickContext, people: EntityRow) -> dict[Nutrient, int]:
    rows = {row.nutrient: row for row in await ctx.session.scalars(select(NutrientNeedRow).where(NutrientNeedRow.people_entity_id == people.id))}
    if rows or held(people.id):
        return {nutrient: row.weight for nutrient, row in rows.items()}
    for nutrient in needs_for(await ctx.session.get(PeopleBiologyRow, people.id)):
        rows[nutrient] = NutrientNeedRow(people_entity_id=people.id, nutrient=nutrient, weight=ctx.rules.nutrition.need_weight, locked=[])
        ctx.session.add(rows[nutrient])
    return {nutrient: row.weight for nutrient, row in rows.items()}


async def stocks_of(ctx: TickContext, town_id: int) -> tuple[dict[CommodityKind, int], int]:
    held_goods: dict[CommodityKind, int] = defaultdict(int)
    preserved = 0
    for row in await ctx.session.scalars(select(CommunityStockRow).where(CommunityStockRow.community_entity_id == town_id)):
        held_goods[row.commodity] += row.quantity
        preserved += min(row.preserved, row.quantity)
    return held_goods, preserved


async def derive_diet(ctx: TickContext, town: EntityRow, row: DietRow) -> None:
    goods, preserved = await stocks_of(ctx, town.id)
    weights = {share: sum(goods.get(kind, 0) for kind in kinds) for share, kinds in GROUPS.items()}
    total = sum(weights.values())
    food = sum(goods.get(kind, 0) for kinds in GROUPS.values() for kind in kinds)
    shares = {share: round_half_up(weight * PERCENT / total) for share, weight in weights.items()} if total else {"staple": PERCENT}
    for share in SHARES:
        if share not in row.locked:
            setattr(row, share, clamp_int(shares.get(share, 0), 0, PERCENT))
    if "preserved" not in row.locked:
        folk = await people_id_of(ctx.session, town)
        lore = await ctx.session.get(FamineLoreRow, folk) if folk is not None else None
        stored = lore.storage * ctx.rules.nutrition.stores_pct // PERCENT if lore is not None else 0
        row.preserved = clamp_int(max(round_half_up(preserved * PERCENT / food) if food else 0, stored), 0, PERCENT)
    if "special" not in row.locked:
        row.special = clamp_int(round_half_up(sum(goods.get(kind, 0) for kind in SPECIAL) * PERCENT / food) if food else 0, 0, PERCENT)
    if "energy" not in row.locked:
        row.energy = clamp_int(PERCENT - (await pressures_of(ctx.session, town.id)).get(PressureKind.HUNGER, 0), 0, PERCENT)
    row.updated_epoch = ctx.epoch


async def light_of(ctx: TickContext, world_id: int) -> int:
    if (await ctx.laws()).has(NaturalLaw.ETERNAL_NIGHT, world_id):
        return ctx.rules.nutrition.night_light
    season = await ctx.session.get(IrregularSeasonRow, world_id)
    return PERCENT - season.severity // 2 if season is not None and season.spell is SeasonSpell.WINTER else PERCENT


def adequacy(ctx: TickContext, diet: DietRow, nutrient: Nutrient, light: int, magic: int) -> int:
    table = ctx.rules.nutrition
    supply: Mapping[Nutrient, tuple[int, int]] = {
        Nutrient.ENERGY: (diet.energy, PERCENT),
        Nutrient.PROTEIN: (diet.protein, table.protein_share),
        Nutrient.FAT: (diet.fat, table.fat_share),
        Nutrient.FRESH: (diet.fresh + diet.preserved * table.preserved_fresh_pct // PERCENT, table.fresh_share),
        Nutrient.MINERAL: (diet.mineral, table.mineral_share),
        Nutrient.LIGHT: (light, PERCENT),
        Nutrient.ESSENCE: (magic, table.essence_share),
        Nutrient.CHARGE: (diet.mineral + magic, table.mineral_share),
    }
    have, want = supply[nutrient]
    return clamp_int(have * PERCENT // max(1, want), 0, PERCENT)


def score_from(ctx: TickContext, row: NutritionScoreRow, diet: DietRow, needs: Mapping[Nutrient, int], *, light: int, magic: int) -> None:
    table = ctx.rules.nutrition
    levels = {nutrient: adequacy(ctx, diet, nutrient, light, magic) for nutrient in needs}
    balanced = {nutrient: level for nutrient, level in levels.items() if nutrient is not Nutrient.ENERGY}
    weight = sum(needs[nutrient] for nutrient in balanced)
    balance = round_half_up(sum(level * needs[nutrient] for nutrient, level in balanced.items()) / weight) if weight else PERCENT
    energy = levels.get(Nutrient.ENERGY, diet.energy)
    low = min(balanced, key=lambda nutrient: (balanced[nutrient], nutrient.value), default=None)
    if "energy" not in row.locked:
        row.energy = energy
    if "balance" not in row.locked:
        row.balance = clamp_int(balance, 0, PERCENT)
    if "deficiency" not in row.locked:
        row.deficiency = low if low is not None and balanced[low] < table.deficient_below else None
    if "score" not in row.locked:
        row.score = clamp_int(
            round_half_up(row.energy * table.energy_weight_pct / PERCENT + row.balance * (PERCENT - table.energy_weight_pct) / PERCENT), 0, PERCENT
        )
    row.updated_epoch = ctx.epoch


def class_shift(ctx: TickContext, mortal: EntityRow) -> int:
    table = ctx.rules.nutrition
    if mortal.social_class in ELITE:
        return table.elite_bonus
    return -table.lowly_penalty if mortal.social_class in LOWLY else 0


async def score_row(ctx: TickContext, node_id: int) -> NutritionScoreRow:
    row = await ctx.session.get(NutritionScoreRow, node_id)
    if row is None:
        row = NutritionScoreRow(holder_node_id=node_id, locked=[])
        ctx.session.add(row)
    return row


async def grow(ctx: TickContext, mortal: EntityRow, row: NutritionScoreRow, tally: NutritionTally) -> None:
    table = ctx.rules.nutrition
    attributes = await attributes_of(ctx.session, mortal.id)
    if not attributes or not has_attributes(mortal):
        row.grown = True
        return
    gap = (row.childhood if row.childhood is not None else row.score) - table.childhood_mean
    for members, pct in ((STATURE, table.stature_pct), (COGNITION, table.cognition_pct)):
        for member in members:
            attributes[member] = attributes.get(member, MIDPOINT) + round_half_up(gap * pct / PERCENT)
    await store_attributes(ctx.session, mortal, attributes)
    row.grown = True
    tally.grown += 1


async def feed_mortal(ctx: TickContext, mortal: EntityRow, town_row: NutritionScoreRow, tally: NutritionTally) -> None:
    table = ctx.rules.nutrition
    profile = await ctx.session.get(MortalProfileRow, mortal.id)
    if profile is None:
        return
    row = await score_row(ctx, mortal.id)
    for name in ("energy", "balance", "deficiency"):
        if name not in row.locked:
            setattr(row, name, getattr(town_row, name))
    if "score" not in row.locked:
        row.score = clamp_int(town_row.score + class_shift(ctx, mortal), 0, PERCENT)
    row.updated_epoch = ctx.epoch
    if profile.life_stage in YOUNG:
        if "childhood" not in row.locked:
            row.childhood = row.score if row.childhood is None else round_half_up((row.childhood + row.score) / 2)
        row.grown = False
    elif not row.grown:
        await grow(ctx, mortal, row, tally)
    if row.deficiency is not None and not is_held(profile, "health"):
        profile.health = clamp_int(profile.health - table.deficiency_health, 0, PERCENT)
        tally.deficient += 1
    if row.deficiency is not None:
        severity = clamp_int(SEVERITY_MIN + (PERCENT - row.balance) * (SEVERITY_MAX - SEVERITY_MIN) // PERCENT, SEVERITY_MIN, SEVERITY_MAX)
        await gain_condition(ctx, mortal, ConditionKind.MALNUTRITION, HarmCause.EXPOSURE, chance=table.malnutrition_chance, severity=severity)
    else:
        await end_condition(ctx, mortal, ConditionKind.MALNUTRITION)
    tally.scored += 1


async def keep_nutrition(ctx: TickContext, tally: NutritionTally) -> None:
    towns = list(
        await ctx.session.scalars(
            select(EntityRow).where(EntityRow.entity_type == EntityType.SETTLEMENT, EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id)
        )
    )
    by_people: dict[int, list[NutritionScoreRow]] = defaultdict(list)
    for town in towns:
        if held(town.id):
            continue
        people = await people_of(ctx.session, town)
        diet = await ctx.session.get(DietRow, town.id) or DietRow(holder_node_id=town.id, locked=[])
        if diet not in ctx.session:
            ctx.session.add(diet)
        await derive_diet(ctx, town, diet)
        tally.diets += 1
        needs = await needs_of(ctx, people) if people is not None else {nutrient: ctx.rules.nutrition.need_weight for nutrient in NEEDS[FolkDiet.OMNIVORE]}
        row = await score_row(ctx, town.id)
        magic = await branch_level(ctx.session, town.id, KnowledgeBranch.MAGIC) * ctx.rules.nutrition.essence_per_magic
        score_from(ctx, row, diet, needs, light=await light_of(ctx, town.world_id), magic=magic)
        if people is not None:
            by_people[people.id].append(row)
        here = await present_in(ctx.session, town)
        for mortal in list(
            await ctx.session.scalars(
                select(EntityRow).where(here, EntityRow.entity_type == EntityType.MORTAL, EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id)
            )
        ):
            if not held(mortal.id):
                await feed_mortal(ctx, mortal, row, tally)
    for people_id, rows in sorted(by_people.items()):
        if held(people_id):
            continue
        row = await score_row(ctx, people_id)
        for name in ("energy", "balance", "score"):
            if name not in row.locked:
                setattr(row, name, round_half_up(sum(getattr(item, name) for item in rows) / len(rows)))
        row.updated_epoch = ctx.epoch
    await feed_the_unhoused(ctx, tally)
    await ctx.session.flush()


async def feed_the_unhoused(ctx: TickContext, tally: NutritionTally) -> None:
    peoples = list(
        await ctx.session.scalars(
            select(EntityRow).where(EntityRow.entity_type == EntityType.PEOPLE, EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id)
        )
    )
    for people in peoples:
        if not held(people.id):
            await needs_of(ctx, people)
    await ctx.session.flush()
    fed = select(NutritionScoreRow.holder_node_id).where(NutritionScoreRow.updated_epoch == ctx.epoch)
    for mortal in list(
        await ctx.session.scalars(
            select(EntityRow)
            .where(EntityRow.entity_type == EntityType.MORTAL, EntityRow.status == EntityStatus.CANON, EntityRow.id.not_in(fed))
            .order_by(EntityRow.id)
        )
    ):
        if held(mortal.id):
            continue
        folk = await people_of(ctx.session, mortal)
        if folk is None and mortal.affiliated_entity_id is not None:
            kin = await ctx.session.get(EntityRow, mortal.affiliated_entity_id)
            folk = kin if kin is not None and kin.entity_type is EntityType.PEOPLE else None
        source = await ctx.session.get(NutritionScoreRow, folk.id) if folk is not None else None
        if source is not None and source.updated_epoch == ctx.epoch:
            await feed_mortal(ctx, mortal, source, tally)
