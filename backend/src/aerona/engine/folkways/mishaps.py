from collections.abc import Mapping
from dataclasses import dataclass

from sqlalchemy import select

from aerona.catalog.life.folkways import ANSWER_MISHAP_RESPONSES, EXPLAINERS, LEANINGS, RESPONSES, SIGN_WORDS, WEIGHTS_FOR_MISHAP_ATTRIBUTIONS
from aerona.catalog.life_traits import CHARM_POWER_TRAITS, DEATH_CAUSE_TRAITS, LIFE_STAGE_TRAITS, having
from aerona.constants.units import PERCENT
from aerona.core.total import total
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.concealment import HiddenTruthRow
from aerona.db.tables.culture import CastingRow, ItemEnchantmentRow, ItemProfileRow
from aerona.db.tables.disease import OutbreakRow
from aerona.db.tables.economy import GoodsFlowRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import NotableYearRow
from aerona.db.tables.folkways import CharmRow, LuckBeliefRow, MishapRow
from aerona.db.tables.minds import MindProfileRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.economy import CommodityKind, GoodsFlow
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.environment import NotableYearKind
from aerona.domain.enums.folkways import CharmPower, LuckReach, LuckSign, MishapAttribution, MishapKind, MishapResponse, PurityState
from aerona.domain.enums.fortune import FortuneSourceKind
from aerona.domain.enums.life_traits import CharmPowerTrait, DeathCauseTrait, LifeStageTrait
from aerona.domain.enums.mind import MemoryKind, ValueAxis
from aerona.domain.enums.minds import MindOrigin
from aerona.domain.enums.mortal import DeathCause
from aerona.domain.enums.society import KnowledgeBranch
from aerona.engine.body.customs import people_of
from aerona.engine.context import TickContext
from aerona.engine.folkways.fed import charm_powers, real_charm
from aerona.engine.folkways.purity import purity_of, sources_of
from aerona.engine.fortune.everyday import everyday
from aerona.engine.fortune.profiles import shift_fortune
from aerona.engine.lore.rumours import enemies_of
from aerona.engine.mind.book import values_for
from aerona.engine.mortal.profile import is_held
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.folk import present_in
from aerona.engine.primitives.knowledge import branch_level
from aerona.engine.primitives.naming import seed_of
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.services.community_relations import change_relation

WITNESSES = 3
YOUNG = having(LIFE_STAGE_TRAITS, LifeStageTrait.GROWING)
VIOLENT = having(DEATH_CAUSE_TRAITS, DeathCauseTrait.VIOLENT)
WARDS = having(CHARM_POWER_TRAITS, CharmPowerTrait.WARDS)
HEALTH = frozenset({LuckReach.HEALTH})
HARVEST = frozenset({LuckReach.HARVEST})
JOURNEY = frozenset({LuckReach.JOURNEY})
REACHES: Mapping[MishapKind, frozenset[LuckReach]] = total(
    MishapKind,
    {
        MishapKind.ILLNESS: HEALTH,
        MishapKind.CROP_FAILURE: HARVEST,
        MishapKind.CHILD_DEATH: frozenset({LuckReach.BIRTH}),
        MishapKind.LIVESTOCK_DEATH: HARVEST,
        MishapKind.ACCIDENT: JOURNEY,
        MishapKind.BAD_LUCK: frozenset(LuckReach),
        MishapKind.FALL: HEALTH,
        MishapKind.CRUSH: HEALTH,
        MishapKind.CUT: HEALTH,
        MishapKind.BURN: HEALTH,
        MishapKind.SCALD: HEALTH,
        MishapKind.DROWNING: JOURNEY,
        MishapKind.BEAST: HARVEST,
        MishapKind.TOOL: HEALTH,
        MishapKind.MACHINE: HEALTH,
        MishapKind.VEHICLE: JOURNEY,
        MishapKind.COLLAPSE: HEALTH,
        MishapKind.HOUSE_FIRE: HEALTH,
        MishapKind.POISONING: HEALTH,
        MishapKind.CHOKING: HEALTH,
        MishapKind.EXPOSURE: JOURNEY,
        MishapKind.LIGHTNING: JOURNEY,
        MishapKind.SPORT: frozenset({LuckReach.BATTLE}),
        MishapKind.BRAWL: frozenset({LuckReach.BATTLE}),
        MishapKind.LOST_WAY: JOURNEY,
        MishapKind.STORES_SPOILED: HARVEST,
        MishapKind.GOODS_LOST: JOURNEY,
        MishapKind.PURSE_LOST: JOURNEY,
        MishapKind.THEFT_SUFFERED: JOURNEY,
        MishapKind.TOOL_BROKEN: HARVEST,
        MishapKind.NEAR_MISS: frozenset(LuckReach),
    },
)


@dataclass
class MishapTally:
    befell: int = 0
    explained: int = 0
    accusations: int = 0
    charms: int = 0
    beliefs: int = 0
    warded: int = 0


@dataclass
class Befell:
    kind: MishapKind
    cause: str
    victim: int | None = None
    cause_node: int | None = None
    severity: int = 0
    died: bool = False


async def deaths_in(ctx: TickContext, town: EntityRow) -> list[Befell]:
    found: list[Befell] = []
    rows = await ctx.session.execute(
        select(EntityRow.id, MortalProfileRow.cause_of_death, MortalProfileRow.life_stage)
        .join(MortalProfileRow, MortalProfileRow.entity_id == EntityRow.id)
        .where(EntityRow.status == EntityStatus.DEAD, EntityRow.end_epoch == ctx.epoch, MortalProfileRow.death_place_id == town.id)
        .order_by(EntityRow.id)
    )
    for mortal_id, cause, stage in rows:
        if cause is None or cause in VIOLENT:
            continue
        if stage in YOUNG:
            found.append(Befell(MishapKind.CHILD_DEATH, cause.value.replace("_", " "), mortal_id))
        elif cause is DeathCause.ACCIDENT:
            found.append(Befell(MishapKind.ACCIDENT, "an accident", mortal_id))
        elif cause is DeathCause.DISEASE:
            found.append(Befell(MishapKind.ILLNESS, "disease", mortal_id))
    return found


async def land_losses(ctx: TickContext, town: EntityRow, region: int | None) -> list[Befell]:
    found: list[Befell] = []
    if region is not None:
        hunger = await ctx.session.scalar(
            select(NotableYearRow.id)
            .where(NotableYearRow.region_entity_id == region, NotableYearRow.epoch == ctx.epoch, NotableYearRow.kind == NotableYearKind.HUNGER)
            .limit(1)
        )
        if hunger is not None:
            found.append(Befell(MishapKind.CROP_FAILURE, "a hungry year in the region"))
        for outbreak in await ctx.session.scalars(
            select(OutbreakRow).where(OutbreakRow.region_entity_id == region, OutbreakRow.started_epoch == ctx.epoch).order_by(OutbreakRow.id)
        ):
            found.append(Befell(MishapKind.ILLNESS, "an outbreak of disease", None, outbreak.disease_entity_id))
    herds = await ctx.session.scalar(
        select(GoodsFlowRow.quantity).where(
            GoodsFlowRow.epoch == ctx.epoch,
            GoodsFlowRow.community_entity_id == town.id,
            GoodsFlowRow.commodity == CommodityKind.LIVESTOCK,
            GoodsFlowRow.flow == GoodsFlow.LOSS,
        )
    )
    if herds:
        found.append(Befell(MishapKind.LIVESTOCK_DEATH, "a loss of herds"))
    return found


async def castings_on(ctx: TickContext, folk: list[int]) -> list[Befell]:
    if not folk:
        return []
    rows = await ctx.session.scalars(
        select(CastingRow).where(CastingRow.epoch == ctx.epoch, CastingRow.target_entity_id.in_(folk), CastingRow.succeeded.is_(True)).order_by(CastingRow.id)
    )
    return [Befell(MishapKind.BAD_LUCK, "a casting by a caster", row.target_entity_id, row.caster_entity_id) for row in rows]


async def bad_luck(ctx: TickContext, town: EntityRow, folk: list[int], tally: MishapTally) -> list[Befell]:
    table = ctx.rules.mishaps
    rng = ctx.rng(seed_of("mishap.luck", town.id, ctx.epoch))
    careful = await ctx.session.scalar(
        select(MishapRow.id)
        .where(
            MishapRow.settlement_entity_id == town.id,
            MishapRow.response == MishapResponse.SAFETY_CUSTOM,
            MishapRow.epoch >= ctx.epoch - ctx.rules.witchcraft.hunt_memory,
        )
        .limit(1)
    )
    chance = table.bad_luck_chance / 2 if careful is not None else table.bad_luck_chance
    if not folk or not rng.chance(chance):
        return []
    victim = rng.pick(folk)
    ward = await real_charm(ctx.session, victim, WARDS)
    if ward and rng.chance(table.charm_ward * ward / PERCENT):
        tally.warded += 1
        return []
    return [Befell(MishapKind.BAD_LUCK, "chance", victim)]


async def explained(ctx: TickContext, town: EntityRow, befell: Befell) -> bool:
    if befell.cause_node is not None and befell.kind is MishapKind.BAD_LUCK:
        return False
    branch = EXPLAINERS[befell.kind]
    if branch is None:
        return befell.kind is not MishapKind.BAD_LUCK
    need = ctx.rules.mishaps.explained_medicine if branch is KnowledgeBranch.MEDICINE else ctx.rules.mishaps.explained_farming
    return await branch_level(ctx.session, town.id, branch) >= need


async def beliefs_of(ctx: TickContext, people_id: int | None) -> list[LuckBeliefRow]:
    if people_id is None:
        return []
    return list(await ctx.session.scalars(select(LuckBeliefRow).where(LuckBeliefRow.people_entity_id == people_id).order_by(LuckBeliefRow.id)))


async def weights_for(ctx: TickContext, town: EntityRow, row: MishapRow, people: EntityRow | None) -> dict[MishapAttribution, float]:
    table = ctx.rules.mishaps
    values = await values_for(ctx.session, people.id) if people is not None else {}
    weights: dict[MishapAttribution, float] = {}
    for attribution, axes in LEANINGS.items():
        lean = sum(max(0, values.get(axis, 0)) for axis in axes) / len(axes)
        weights[attribution] = table.base_weight + lean * table.value_weight_pct / PERCENT
    weights[MishapAttribution.KNOWN_CAUSE] = table.known_cause_weight if row.explained else 0
    if values.get(ValueAxis.SUPERSTITION, 0) < ctx.rules.witchcraft.belief_from:
        weights[MishapAttribution.WITCHCRAFT] = 0
    if people is None or not await sources_of(ctx, people.id):
        weights[MishapAttribution.IMPURITY] = 0
    if not await enemies_of(ctx, town.id):
        weights[MishapAttribution.ENEMY_SCHEME] = 0
    if not await made_minds_near(ctx, town.id):
        weights[MishapAttribution.MADE_MIND] = 0
    if not await hidden_near(ctx, town.id):
        weights[MishapAttribution.HIDDEN_PEOPLE] = 0
    reaching = sum(1 for belief in await beliefs_of(ctx, people.id if people is not None else None) if belief.reach in REACHES[row.kind])
    for attribution in WEIGHTS_FOR_MISHAP_ATTRIBUTIONS:
        weights[attribution] += reaching * table.luck_weight
    return weights


async def made_minds_near(ctx: TickContext, town_id: int) -> bool:
    here = select(EntityRow.id).where(EntityRow.location_id == town_id)
    return (
        await ctx.session.scalar(select(MindProfileRow.node_id).where(MindProfileRow.node_id.in_(here), MindProfileRow.origin != MindOrigin.BORN).limit(1))
        is not None
    )


async def hidden_near(ctx: TickContext, town_id: int) -> bool:
    here = select(EntityRow.id).where(EntityRow.location_id == town_id)
    return await ctx.session.scalar(select(HiddenTruthRow.id).where(HiddenTruthRow.subject_node_id.in_(here)).limit(1)) is not None


async def attribute(ctx: TickContext, town: EntityRow, row: MishapRow, people: EntityRow | None) -> None:
    if "attribution" in row.locked and row.attribution is not None:
        return
    weights = await weights_for(ctx, town, row, people)
    choices = [item for item in MishapAttribution if weights[item] > 0]
    rng = ctx.rng(seed_of("mishap.blame", row.id))
    row.attribution = rng.weighted(choices, [weights[item] for item in choices]) if choices else MishapAttribution.CHANCE
    if "response" not in row.locked:
        row.response = RESPONSES[row.attribution]


async def answer(ctx: TickContext, town: EntityRow, row: MishapRow, tally: MishapTally) -> None:
    table = ctx.rules.mishaps
    victim = await ctx.session.get(EntityRow, row.victim_node_id) if row.victim_node_id is not None else None
    profile = await ctx.session.get(MortalProfileRow, victim.id) if victim is not None else None
    if victim is not None and held(victim.id):
        return
    if row.response in ANSWER_MISHAP_RESPONSES and profile is not None and not is_held(profile, "stress"):
        profile.stress = clamp_int(profile.stress - table.rite_calm, 0, PERCENT)
    if row.response is MishapResponse.OFFERING and profile is not None and not is_held(profile, "loyalty_god"):
        profile.loyalty_god = clamp_int(profile.loyalty_god + table.offering_loyalty, 0, PERCENT)
    if row.response is MishapResponse.PURIFICATION and victim is not None and victim.entity_type is EntityType.MORTAL:
        purity = await purity_of(ctx, victim.id)
        if "state" not in purity.locked and purity.state is PurityState.PURE:
            purity.state, purity.since_epoch, purity.until_epoch = PurityState.IMPURE, ctx.epoch, ctx.epoch + 1
    if row.response is MishapResponse.CHARM and victim is not None and await make_charm(ctx, victim.id, CharmPower.PROTECTION) is not None:
        tally.charms += 1
    if row.attribution is MishapAttribution.BROKEN_OATH and profile is not None and not is_held(profile, "honour"):
        profile.honour = clamp_int(profile.honour - table.oath_honour, 0, PERCENT)
    if row.attribution is MishapAttribution.ENEMY_SCHEME:
        for foe in sorted(await enemies_of(ctx, town.id))[:1]:
            await change_relation(ctx, town.id, foe, -table.scheme_opinion, MemoryKind.ILL_WILL, note="blamed for a misfortune")


async def charmable(ctx: TickContext, bearer_id: int) -> int | None:
    owned = select(BondRow.target_node_id).where(BondRow.source_node_id == bearer_id, BondRow.kind == BondKind.OWNS, BondRow.state == BondState.ACTIVE)
    charmed = select(CharmRow.item_entity_id)
    found = await ctx.session.scalar(
        select(ItemProfileRow.item_entity_id)
        .where(ItemProfileRow.item_entity_id.in_(owned), ItemProfileRow.item_entity_id.not_in(charmed))
        .order_by(ItemProfileRow.item_entity_id)
        .limit(1)
    )
    return int(found) if found is not None else None


async def is_real(ctx: TickContext, item_id: int) -> bool:
    item = await ctx.session.get(EntityRow, item_id)
    profile = await ctx.session.get(ItemProfileRow, item_id)
    enchanted = await ctx.session.scalar(select(ItemEnchantmentRow.item_entity_id).where(ItemEnchantmentRow.item_entity_id == item_id).limit(1))
    return (
        enchanted is not None
        or (item is not None and item.sacred_to_son_id is not None)
        or (profile is not None and profile.bound_spirit_entity_id is not None)
    )


async def make_charm(ctx: TickContext, bearer_id: int, power: CharmPower) -> CharmRow | None:
    item_id = await charmable(ctx, bearer_id)
    if item_id is None or held(item_id):
        return None
    row = CharmRow(item_entity_id=item_id, power=power, real=await is_real(ctx, item_id), strength=ctx.rules.mishaps.charm_strength, locked=[])
    ctx.session.add(row)
    await ctx.session.flush()
    return row


async def keep_charms(ctx: TickContext) -> None:
    table = ctx.rules.mishaps
    for row in list(await ctx.session.scalars(select(CharmRow).order_by(CharmRow.item_entity_id))):
        if held(row.item_entity_id):
            continue
        if "real" not in row.locked:
            row.real = await is_real(ctx, row.item_entity_id)
    for bearer, powers in sorted((await charm_powers(ctx.session)).items()):
        real, strength = powers.get(CharmPower.LUCK, (False, 0))
        if real and strength:
            await shift_fortune(ctx, bearer, strength * ctx.rules.fortune.charm_pct // PERCENT, FortuneSourceKind.CHARM, epochs=0)
        profile = await ctx.session.get(MortalProfileRow, bearer)
        if profile is not None and not held(bearer) and not is_held(profile, "stress"):
            profile.stress = clamp_int(profile.stress - table.charm_calm, 0, PERCENT)


async def seed_luck(ctx: TickContext, people: EntityRow, tally: MishapTally) -> None:
    table = ctx.rules.mishaps
    if (await values_for(ctx.session, people.id)).get(ValueAxis.SUPERSTITION, 0) < table.luck_from or await beliefs_of(ctx, people.id):
        return
    rng = ctx.rng(seed_of("luck.seed", people.id))
    for sign in rng.sample(list(LuckSign), min(len(LuckSign), table.beliefs_per_people)):
        lucky = rng.chance(50)
        name = f"{'A lucky' if lucky else 'An unlucky'} {SIGN_WORDS[sign]} of {people.name}"
        ctx.session.add(LuckBeliefRow(people_entity_id=people.id, sign=sign, reach=rng.pick(list(LuckReach)), lucky=lucky, name=name, locked=[]))
        tally.beliefs += 1


async def keep_mishaps(ctx: TickContext, tally: MishapTally) -> None:
    atlas = await RegionAtlas.load(ctx.session)
    for people in list(
        await ctx.session.scalars(
            select(EntityRow).where(EntityRow.entity_type == EntityType.PEOPLE, EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id)
        )
    ):
        if not held(people.id):
            await seed_luck(ctx, people, tally)
    towns = list(
        await ctx.session.scalars(
            select(EntityRow).where(EntityRow.entity_type == EntityType.SETTLEMENT, EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id)
        )
    )
    for town in towns:
        if held(town.id):
            continue
        here = await present_in(ctx.session, town)
        folk = list(
            await ctx.session.scalars(
                select(EntityRow.id).where(here, EntityRow.entity_type == EntityType.MORTAL, EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id)
            )
        )
        befallen = [
            *await deaths_in(ctx, town),
            *await land_losses(ctx, town, atlas.top_region(town.id)),
            *await castings_on(ctx, folk),
            *await bad_luck(ctx, town, folk, tally),
            *[Befell(found.kind, found.cause, found.victim, severity=found.severity, died=found.died) for found in await everyday(ctx, folk)],
        ]
        folk_people = await people_of(ctx.session, town)
        draw = ctx.rng(f"mishap.witnesses.{town.id}.{ctx.epoch}")
        for befell in befallen:
            row = MishapRow(
                settlement_entity_id=town.id,
                victim_node_id=befell.victim,
                cause_node_id=befell.cause_node,
                kind=befell.kind,
                true_cause=befell.cause,
                explained=await explained(ctx, town, befell),
                severity=befell.severity,
                died=befell.died,
                witnesses=draw.sample([node for node in folk if node != befell.victim], WITNESSES),
                epoch=ctx.epoch,
                locked=[],
            )
            ctx.session.add(row)
            await ctx.session.flush()
            await attribute(ctx, town, row, folk_people)
            await answer(ctx, town, row, tally)
            tally.befell += 1
            tally.explained += row.explained
            tally.accusations += row.response is MishapResponse.ACCUSATION
    await keep_charms(ctx)
    await ctx.session.flush()
