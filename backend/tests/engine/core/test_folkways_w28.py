from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.agents.context.folkways_lines import mortal_folkways_lines, son_folkways_lines
from aerona.agents.context.scope import load_scope
from aerona.db.repositories.cosmos import CosmosRepository
from aerona.db.tables.agrarian import FamineLoreRow
from aerona.db.tables.culture import CastingRow, ItemEnchantmentRow, ItemProfileRow
from aerona.db.tables.economy import CommunityStockRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.folkways import (
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
from aerona.db.tables.justice import CrimeCaseRow
from aerona.db.tables.mind import CultureValueRow, FacetRow, IdeaRow, PressureRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.db.tables.polity import OfficeRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.culture import ItemClass, RiteEffectKind
from aerona.domain.enums.economy import CommodityKind
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.folkways import (
    AccusationOutcome,
    BiasedDecision,
    CharmPower,
    DecisionBias,
    IdeaStrain,
    ImpuritySource,
    MishapAttribution,
    MishapResponse,
    Nutrient,
    Purification,
    PurityState,
)
from aerona.domain.enums.justice import Verdict
from aerona.domain.enums.mind import Attribute, Facet, IdeaKind, IdeaSource, IdeaState, PressureKind, Profession, ValueAxis
from aerona.domain.enums.mortal import CrimeKind, LifeStage
from aerona.domain.enums.polity import OfficeKind
from aerona.domain.models.entity_stats import ItemStats, RiteStats
from aerona.engine.context import TickContext
from aerona.engine.demography.kinship import may_wed
from aerona.engine.folkways.biases import BiasTally, keep_biases, lean, lean_community
from aerona.engine.folkways.control import start_hunt
from aerona.engine.folkways.mishaps import MishapTally, keep_mishaps
from aerona.engine.folkways.nutrition import NutritionTally, keep_nutrition
from aerona.engine.folkways.purity import PurityTally, barred_professions, keep_purity, unclean
from aerona.engine.folkways.witchcraft import WitchTally, keep_witchcraft
from aerona.engine.folkways.wrongs import wrongly_condemned
from aerona.engine.mind.ideas import turn_over
from aerona.engine.mind.split import effective_attributes, write_attributes
from aerona.engine.primitives.knowledge import KnowledgeMap
from aerona.engine.primitives.manual import manual_context
from aerona.services.integrity.folkways_links import mend_folkways_links
from tests.engine.core.factories import CoreWorld, bond, entity, mortal, settlement, tuned_rules


async def at(session: AsyncSession, epoch: int, **rules: dict[str, int]) -> TickContext:
    cosmos = await CosmosRepository(session).require_cosmos()
    cosmos.epoch = epoch
    await session.flush()
    return await manual_context(session, "folkways", rules=tuned_rules(**rules))


async def home(session: AsyncSession, world: CoreWorld, name: str, **values: int) -> tuple[EntityRow, EntityRow]:
    town = await settlement(session, name, world, world.regions[0])
    town.affiliated_entity_id = world.people.id
    await bond(session, town.id, world.people.id, BondKind.DESCENDS_FROM)
    for axis, value in values.items():
        session.add(CultureValueRow(entity_id=world.people.id, axis=ValueAxis(axis), value=value))
    await session.flush()
    return town, world.people


def profile(mortal_id: int, **values: object) -> MortalProfileRow:
    return MortalProfileRow(entity_id=mortal_id, locked=[], **values)


async def test_a_town_eats_what_it_stores_and_the_underfed_resist_disease_worse(session: AsyncSession, world: CoreWorld) -> None:
    town, folk = await home(session, world, "Barrowmead")
    session.add_all(
        [
            CommunityStockRow(community_entity_id=town.id, commodity=CommodityKind.GRAIN, quantity=80),
            CommunityStockRow(community_entity_id=town.id, commodity=CommodityKind.MEAT, quantity=20),
        ]
    )
    eater = await mortal(session, "Tollan", world, town.id)
    session.add(profile(eater.id))
    await session.flush()
    await write_attributes(session, eater.id, {Attribute.DISEASE_RESISTANCE: 50, Attribute.RECUPERATION: 50, Attribute.STRENGTH: 50})
    tally = NutritionTally()
    await keep_nutrition(await at(session, 3), tally)
    diet = await session.get(DietRow, town.id)
    needs = {row.nutrient for row in await session.scalars(select(NutrientNeedRow).where(NutrientNeedRow.people_entity_id == folk.id))}
    score = await session.get(NutritionScoreRow, eater.id)
    assert diet is not None and diet.staple == 80 and diet.protein == 20 and diet.fresh == 0
    assert Nutrient.FRESH in needs and score is not None and score.deficiency in (Nutrient.FAT, Nutrient.FRESH) and tally.deficient >= 1
    score.score, score.locked = 30, ["score"]
    await session.flush()
    attributes = await effective_attributes(session, tuned_rules(), eater)
    assert attributes[Attribute.DISEASE_RESISTANCE] < 50 and attributes[Attribute.RECUPERATION] < 50


async def test_what_a_child_was_fed_sets_the_strength_of_the_adult(session: AsyncSession, world: CoreWorld) -> None:
    town, _ = await home(session, world, "Lean Hollow")
    child = await mortal(session, "Pell", world, town.id)
    session.add(profile(child.id, life_stage=LifeStage.ADULT))
    session.add(NutritionScoreRow(holder_node_id=child.id, score=20, childhood=20, grown=False, locked=["score", "childhood"]))
    await session.flush()
    await write_attributes(session, child.id, {Attribute.STRENGTH: 50, Attribute.TOUGHNESS: 50})
    tally = NutritionTally()
    await keep_nutrition(await at(session, 3, nutrition={"stature_pct": 50, "childhood_mean": 60}), tally)
    attributes = await effective_attributes(session, tuned_rules(), child)
    row = await session.get(NutritionScoreRow, child.id)
    assert row is not None and row.grown and tally.grown == 1 and attributes[Attribute.STRENGTH] == 30


async def test_biases_come_from_character_and_lean_the_decisions_they_touch(session: AsyncSession, world: CoreWorld) -> None:
    town, _ = await home(session, world, "Crownfold")
    ruler = await mortal(session, "Vasha", world, town.id)
    session.add(profile(ruler.id))
    session.add_all([FacetRow(node_id=ruler.id, facet=Facet.PERSEVERANCE, value=50), FacetRow(node_id=ruler.id, facet=Facet.ABSTRACTION, value=-50)])
    await bond(session, ruler.id, town.id, BondKind.RULES)
    await session.flush()
    ctx = await at(session, 3, biases={"drift_pct": 100})
    await keep_biases(ctx, BiasTally())
    sunk = await session.get(BiasWeightRow, (ruler.id, DecisionBias.SUNK_COST))
    assert sunk is not None and sunk.weight == 100
    leaning = await lean(ctx, ruler.id, BiasedDecision.PEACE)
    assert leaning < 1 and sunk.last_decision is BiasedDecision.PEACE and sunk.last_shift < 0


async def test_a_culture_of_purity_shuts_the_impure_out_of_unions_until_they_purify(session: AsyncSession, world: CoreWorld) -> None:
    town, folk = await home(session, world, "Clearwater", purity=80)
    mourner = await mortal(session, "Ilva", world, town.id)
    other = await mortal(session, "Roan", world, town.id)
    dead = await mortal(session, "Old Sem", world, town.id)
    for row in (mourner, other, dead):
        session.add(profile(row.id))
    await bond(session, mourner.id, dead.id, BondKind.PARENT_OF)
    dead.status, dead.end_epoch = EntityStatus.DEAD, 3
    session.add(ImpuritySourceRow(people_entity_id=folk.id, source=ImpuritySource.THE_DEAD, weight=100, lasts=1, locked=[]))
    session.add(PurificationRow(people_entity_id=folk.id, method=Purification.WASHING, epochs=0, cost=0, success=100, locked=[]))
    await session.flush()
    await keep_purity(await at(session, 3), PurityTally())
    stained = await session.get(PurityRow, mourner.id)
    assert stained is not None and stained.state is not PurityState.PURE and stained.source is ImpuritySource.THE_DEAD
    assert await unclean(session, mourner.id) and not await may_wed(session, tuned_rules(), mourner, other)
    tally = PurityTally()
    await keep_purity(await at(session, 5), tally)
    after = await session.get(PurityRow, mourner.id)
    assert after is not None and after.state.value == PurityState.PURE.value and tally.purified == 1


async def test_a_caste_rank_passes_to_children_and_bars_the_work_of_other_ranks(session: AsyncSession, world: CoreWorld) -> None:
    town, folk = await home(session, world, "Tierholm", purity=80, hierarchy=80)
    session.add(ImpuritySourceRow(people_entity_id=folk.id, source=ImpuritySource.OUTSIDERS, weight=0, lasts=1, locked=[]))
    high = PurityRankRow(people_entity_id=folk.id, name="Upper", standing=90, professions=[Profession.PRIEST.value], locked=[])
    low = PurityRankRow(people_entity_id=folk.id, name="Lower", standing=10, professions=[Profession.MINER.value], locked=[])
    session.add_all([high, low])
    parent = await mortal(session, "Hesk", world, town.id)
    child = await mortal(session, "Hesk the Younger", world, town.id)
    session.add_all([profile(parent.id), profile(child.id)])
    await session.flush()
    session.add(PurityRow(holder_node_id=parent.id, state=PurityState.PURE, rank_id=low.id, locked=[]))
    await bond(session, parent.id, child.id, BondKind.PARENT_OF)
    await session.flush()
    await keep_purity(await at(session, 3), PurityTally())
    inherited = await session.get(PurityRow, child.id)
    assert inherited is not None and inherited.rank_id == low.id
    assert Profession.PRIEST.value in await barred_professions(session, child.id)
    noble = await mortal(session, "Upper Child", world, town.id)
    session.add(PurityRow(holder_node_id=noble.id, state=PurityState.PURE, rank_id=high.id, locked=[]))
    await session.flush()
    assert not await may_wed(session, tuned_rules(), child, noble)


async def test_misfortune_is_blamed_by_the_culture_and_witchcraft_brings_an_accusation_and_a_trial(session: AsyncSession, world: CoreWorld) -> None:
    town, folk = await home(session, world, "Grimsby", superstition=90)
    victim = await mortal(session, "Ada", world, town.id)
    caster = await mortal(session, "Morrow", world, town.id)
    for row in (victim, caster):
        session.add(profile(row.id))
    rite = await entity(session, "A Binding", EntityType.RITE, RiteStats(), world_id=world.world.id)
    session.add(CastingRow(rite_entity_id=rite.id, caster_entity_id=caster.id, target_entity_id=victim.id, epoch=3, succeeded=True))
    await session.flush()
    rules = {"bad_luck_chance": 0, "base_weight": 0, "known_cause_weight": 0, "luck_weight": 0}
    tally = MishapTally()
    await keep_mishaps(await at(session, 3, mishaps=rules), tally)
    mishap = await session.scalar(select(MishapRow).where(MishapRow.settlement_entity_id == town.id))
    beliefs = list(await session.scalars(select(LuckBeliefRow).where(LuckBeliefRow.people_entity_id == folk.id)))
    assert mishap is not None and mishap.cause_node_id == caster.id and not mishap.explained and beliefs
    assert mishap.attribution in (MishapAttribution.WITCHCRAFT, MishapAttribution.CURSE, MishapAttribution.OMEN)
    mishap.attribution, mishap.response = MishapAttribution.WITCHCRAFT, MishapResponse.ACCUSATION
    await session.flush()
    witch = WitchTally()
    await keep_witchcraft(await at(session, 3, witchcraft={"accuse_chance": 100}), witch)
    accusation = await session.scalar(select(AccusationRow).where(AccusationRow.mishap_id == mishap.id))
    assert accusation is not None and accusation.accused_node_id == caster.id and accusation.guilty_in_truth
    case = await session.get(CrimeCaseRow, accusation.case_id)
    assert case is not None and case.crime is CrimeKind.WITCHCRAFT and case.culprit_entity_id == caster.id
    case.verdict, case.penalty = Verdict.GUILTY, "death"
    await session.flush()
    await keep_witchcraft(await at(session, 4), witch)
    assert accusation.outcome is AccusationOutcome.KILLED and witch.killed == 1


async def test_hunger_turns_accusations_into_a_witch_hunt_and_the_wrongly_condemned_walk_restless(session: AsyncSession, world: CoreWorld) -> None:
    town, _ = await home(session, world, "Ashwick", superstition=90)
    folk = [await mortal(session, f"Townsman {index}", world, town.id) for index in range(4)]
    for row in folk:
        session.add(profile(row.id))
    for row in folk[:3]:
        session.add(AccusationRow(settlement_entity_id=town.id, accused_node_id=row.id, opened_epoch=3, locked=[]))
    session.add(PressureRow(entity_id=town.id, pressure=PressureKind.HUNGER, value=90))
    await session.flush()
    tally = WitchTally()
    await keep_witchcraft(await at(session, 3, witchcraft={"hunt_from": 3, "hunt_stress": 40, "hunt_accusations": 2}), tally)
    hunt = await session.scalar(select(WitchHuntRow).where(WitchHuntRow.settlement_entity_id == town.id))
    assert hunt is not None and tally.hunts == 1 and hunt.accused >= 1
    innocent = folk[3]
    session.add(CrimeCaseRow(crime=CrimeKind.WITCHCRAFT, accused_entity_id=innocent.id, verdict=Verdict.GUILTY, wrongful=True, opened_epoch=3, locked=[]))
    await session.flush()
    assert await wrongly_condemned(session, innocent.id)


async def test_a_real_charm_wards_off_bad_luck_and_any_charm_calms_its_bearer(session: AsyncSession, world: CoreWorld) -> None:
    town, _ = await home(session, world, "Luckmoor")
    bearer = await mortal(session, "Wren", world, town.id)
    session.add(profile(bearer.id, stress=40))
    item = await entity(session, "Blue Knot", EntityType.ITEM, ItemStats(), world_id=world.world.id, location_id=town.id)
    session.add(ItemProfileRow(item_entity_id=item.id, item_class=ItemClass.RING, locked=[]))
    session.add(ItemEnchantmentRow(item_entity_id=item.id, effect=RiteEffectKind(next(iter(RiteEffectKind)).value), strength=10))
    session.add(CharmRow(item_entity_id=item.id, power=CharmPower.PROTECTION, real=True, strength=100, locked=[]))
    await bond(session, bearer.id, item.id, BondKind.OWNS)
    await session.flush()
    tally = MishapTally()
    await keep_mishaps(await at(session, 3, mishaps={"bad_luck_chance": 100, "charm_ward": 100}), tally)
    charm = await session.get(CharmRow, item.id)
    assert charm is not None and charm.real and tally.warded == 1
    calm = await session.get(MortalProfileRow, bearer.id)
    assert calm is not None and calm.stress < 40


async def test_an_obsessing_idea_turns_faster_and_weighs_on_its_holder(session: AsyncSession, world: CoreWorld) -> None:
    town, _ = await home(session, world, "Thinkwell")
    thinker = await mortal(session, "Orla", world, town.id)
    session.add(profile(thinker.id, stress=0))
    session.add(
        IdeaRow(
            holder_node_id=thinker.id,
            idea=IdeaKind.RATIONALISM,
            source=IdeaSource.PLAYER,
            progress=0,
            state=IdeaState.INCUBATING,
            strain=IdeaStrain.OBSESSION,
            started_epoch=1,
        )
    )
    await session.flush()
    ctx = await at(session, 3, ideas={"reject_pct": 0, "encounter_pct": 0, "obsession_stress": 10})
    await turn_over(ctx, thinker, KnowledgeMap({}))
    row = await session.scalar(select(IdeaRow).where(IdeaRow.holder_node_id == thinker.id))
    held = await session.get(MortalProfileRow, thinker.id)
    assert row is not None and row.progress > ctx.rules.ideas.incubation_rate and held is not None and held.stress == 10


async def test_mortals_and_gods_read_their_folkways_and_integrity_mends_dangling_ones(session: AsyncSession, world: CoreWorld) -> None:
    town, _ = await home(session, world, "Talemere")
    reader = await mortal(session, "Iso", world, town.id)
    session.add(profile(reader.id))
    session.add(NutritionScoreRow(holder_node_id=reader.id, score=40, deficiency=Nutrient.FAT, locked=[]))
    session.add(PurityRow(holder_node_id=reader.id, state=PurityState.IMPURE, source=ImpuritySource.WOUND, locked=[]))
    session.add(BiasWeightRow(holder_node_id=world.son.id, bias=DecisionBias.OVERCONFIDENCE, weight=90, last_shift=0, locked=[]))
    session.add(WitchHuntRow(settlement_entity_id=town.id, fervour=50, started_epoch=2, locked=[]))
    await session.flush()
    scope = await load_scope(session, tuned_rules())
    lines = await mortal_folkways_lines(scope, reader)
    assert any("nutrition" in line for line in lines) and any("impure" in line for line in lines) and any("witch hunt" in line for line in lines)
    assert any("overconfidence" in line for line in await son_folkways_lines(scope, world.son))
    town.status, town.end_epoch = EntityStatus.DESTROYED, 4
    await session.flush()
    assert await mend_folkways_links(session, 4) >= 1


async def test_a_ruling_council_leans_together_and_stores_against_hunger_keep_food_in_the_diet(session: AsyncSession, world: CoreWorld) -> None:
    town, folk = await home(session, world, "Twinseat")
    first = await mortal(session, "Ama", world, town.id)
    second = await mortal(session, "Bel", world, town.id)
    for ruler, weight in ((first, 100), (second, 0)):
        session.add(profile(ruler.id))
        session.add(BiasWeightRow(holder_node_id=ruler.id, bias=DecisionBias.RISK_SEEKING, weight=weight, last_shift=0, locked=[]))
    await bond(session, first.id, town.id, BondKind.RULES)
    session.add(OfficeRow(polity_entity_id=town.id, kind=OfficeKind.CHANCELLOR, holder_entity_id=second.id))
    session.add(FamineLoreRow(people_entity_id=folk.id, memory=80, famine_foods=True, storage=100, locked=[]))
    session.add(CommunityStockRow(community_entity_id=town.id, commodity=CommodityKind.GRAIN, quantity=50))
    await session.flush()
    ctx = await at(session, 3, biases={"council_pct": 50, "push_pct": 100}, nutrition={"stores_pct": 40})
    alone = await lean(ctx, first.id, BiasedDecision.RAID)
    together = await lean_community(ctx, town.id, BiasedDecision.RAID)
    assert alone > together > 1.0 - 0.01
    await keep_nutrition(ctx, NutritionTally())
    diet = await session.get(DietRow, town.id)
    assert diet is not None and diet.preserved == 40


async def test_purity_rules_fade_when_the_culture_stops_valuing_purity(session: AsyncSession, world: CoreWorld) -> None:
    _, folk = await home(session, world, "Lapsed Well", purity=-50)
    session.add(ImpuritySourceRow(people_entity_id=folk.id, source=ImpuritySource.FOOD, weight=1, lasts=1, locked=[]))
    session.add(ImpuritySourceRow(people_entity_id=folk.id, source=ImpuritySource.BIRTH, weight=80, lasts=1, locked=["weight"]))
    await session.flush()
    tally = PurityTally()
    await keep_purity(await at(session, 3, purity={"reform_pct": 50}), tally)
    left = {row.source for row in await session.scalars(select(ImpuritySourceRow).where(ImpuritySourceRow.people_entity_id == folk.id))}
    assert left == {ImpuritySource.BIRTH} and tally.reformed == 1


async def test_one_who_decides_without_a_read_character_leans_by_its_culture(session: AsyncSession, world: CoreWorld) -> None:
    town, _ = await home(session, world, "Plainseat", martial=80, tradition=80)
    ruler = await mortal(session, "Unread", world, town.id)
    session.add(profile(ruler.id))
    await bond(session, ruler.id, town.id, BondKind.RULES)
    await session.flush()
    tally = BiasTally()
    await keep_biases(await at(session, 3), tally)
    rows = list(await session.scalars(select(BiasWeightRow).where(BiasWeightRow.holder_node_id == ruler.id)))
    assert len(rows) == len(DecisionBias) and tally.derived >= len(DecisionBias)


async def test_a_hunt_started_by_hand_still_burns_out(session: AsyncSession, world: CoreWorld) -> None:
    town, _ = await home(session, world, "Embersby")
    hunt = await start_hunt(await at(session, 3), town.id, 20)
    assert hunt.locked == []
    await keep_witchcraft(await at(session, 4, witchcraft={"hunt_fade": 15, "hunt_accusations": 0}), WitchTally())
    await keep_witchcraft(await at(session, 5, witchcraft={"hunt_fade": 15, "hunt_accusations": 0}), WitchTally())
    assert hunt.fervour == 0 and hunt.ended_epoch == 5


async def test_a_life_outside_any_town_is_fed_as_its_people_is(session: AsyncSession, world: CoreWorld) -> None:
    town, folk = await home(session, world, "Hearthless")
    session.add(CommunityStockRow(community_entity_id=town.id, commodity=CommodityKind.GRAIN, quantity=50))
    wanderer = await mortal(session, "Kesh", world, world.regions[1].id)
    wanderer.affiliated_entity_id = folk.id
    session.add(profile(wanderer.id))
    await session.flush()
    await keep_nutrition(await at(session, 3), NutritionTally())
    fed = await session.get(NutritionScoreRow, wanderer.id)
    people = await session.get(NutritionScoreRow, folk.id)
    assert people is not None and fed is not None and fed.updated_epoch == 3 and fed.energy == people.energy
