from dataclasses import replace

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.afflictions import AfflictionRow
from aerona.db.tables.arcana import LabTextRow, LawUpkeepRow, RiteGrammarRow, VisStockRow, WarpingRow
from aerona.db.tables.culture import ItemEnchantmentRow, ItemProfileRow, LegendProfileRow, RiteProfileRow
from aerona.db.tables.discovery import TheoryProfileRow
from aerona.db.tables.dominion import MagicSiteRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.foreign_gods import ForeignGodRow
from aerona.db.tables.mind import SkillRow
from aerona.domain.enums.affliction import PackageKind, Transmission
from aerona.domain.enums.arcana import LawSource, RechargeRule, SpellDuration, SpellForm, SpellRange, SpellTarget, SpellTechnique
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.culture import ItemClass, LegendArchetype, MagicSchool, RiteEffectKind
from aerona.domain.enums.discovery import TheoryDomain
from aerona.domain.enums.domain import Domain
from aerona.domain.enums.dominion import MagicSiteKind
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.foreign_god import ForeignGodStatus
from aerona.domain.enums.mind import SkillKind, SkillSource
from aerona.domain.enums.society import NaturalLaw
from aerona.domain.models.entity_stats import FactionStats, ItemStats, LegendStats, TheoryStats
from aerona.engine.arcana import control
from aerona.engine.arcana.casting import myth_factor, paradigm_factor, shape_casting
from aerona.engine.arcana.enchantments import keep_law, lay_enchantment
from aerona.engine.arcana.grammar import Shape, cost_factor, difficulty_of, ensure_grammar, write_grammar
from aerona.engine.arcana.items import ChargeTally, recharge_all, use_charge
from aerona.engine.arcana.labs import StudyTally, study, write_lab_text
from aerona.engine.arcana.longevity import LongevityTally, begin_longevity, tend_longevity
from aerona.engine.arcana.resistance import dispel_force
from aerona.engine.arcana.vis import VisTally, flow_vis, vis_of
from aerona.engine.arcana.warping import WarpTally, expose, warp_world
from aerona.engine.body.afflictions import afflict
from aerona.engine.context import TickContext
from aerona.engine.lore.items import profile_of
from aerona.engine.lore.rites import devise
from aerona.engine.primitives.manual import manual_context
from aerona.engine.primitives.stats import stat, stat_or
from aerona.rules.registry import Rules
from tests.engine.core.factories import CoreWorld, bond, entity, mortal, settlement


async def rite_of(
    ctx: TickContext, session: AsyncSession, world: CoreWorld, school: MagicSchool = MagicSchool.ELEMENTAL_FIRE
) -> tuple[EntityRow, EntityRow, RiteProfileRow]:
    mage = await mortal(session, "Ysel", world, world.regions[0].id)
    rite, profile = await devise(ctx, school, mage)
    await session.flush()
    return mage, rite, profile


async def test_every_rite_takes_the_grammar_of_its_school(ctx: TickContext, session: AsyncSession, world: CoreWorld) -> None:
    _, rite, profile = await rite_of(ctx, session, world)
    grammar = await ensure_grammar(session, ctx.rules, profile)
    assert (grammar.technique, grammar.form) == (SpellTechnique.DESTROY, SpellForm.FIRE)
    near = difficulty_of(ctx.rules, Shape(SpellTechnique.DESTROY, SpellForm.FIRE), profile.power)
    far = difficulty_of(ctx.rules, Shape(SpellTechnique.DESTROY, SpellForm.FIRE, SpellRange.WORLD, SpellDuration.PERMANENT, SpellTarget.REGION), profile.power)
    assert far > near
    wide = await write_grammar(
        session, ctx.rules, profile, Shape(SpellTechnique.DESTROY, SpellForm.FIRE, SpellRange.WORLD, SpellDuration.PERMANENT), paradigm_id=None, myth_id=None
    )
    assert cost_factor(ctx.rules, wide) > 1
    assert (await session.get(RiteGrammarRow, rite.id)) is wide


async def test_a_lab_text_teaches_the_mages_near_it(session: AsyncSession, world: CoreWorld, rules: Rules) -> None:
    ctx = await manual_context(session, "lab", rules=replace(rules, spell_grammar=replace(rules.spell_grammar, lab_learn_pct=100)))
    author, rite, _ = await rite_of(ctx, session, world)
    text = await write_lab_text(ctx, rite, author)
    assert text is not None
    reader = await mortal(session, "Ovan", world, world.regions[0].id)
    session.add(SkillRow(holder_node_id=reader.id, skill=SkillKind.SPELLCRAFT, level=30, peak=30, last_used_epoch=1, source=SkillSource.PRACTICE))
    text.fidelity = 100
    await session.flush()
    await study(ctx, StudyTally())
    learned = await session.scalar(select(SkillRow).where(SkillRow.holder_node_id == reader.id, SkillRow.subject_node_id == rite.id))
    assert learned is not None
    assert (await session.scalar(select(LabTextRow).where(LabTextRow.rite_entity_id == rite.id))) is not None


async def test_sources_give_vis_and_a_rite_burns_it_for_strength(ctx: TickContext, session: AsyncSession, world: CoreWorld) -> None:
    mage, _, profile = await rite_of(ctx, session, world)
    session.add(
        MagicSiteRow(
            place_entity_id=world.regions[0].id,
            kind=MagicSiteKind.SOURCE,
            school=MagicSchool.ELEMENTAL_FIRE,
            strength=100,
            found_epoch=0,
            holder_node_id=mage.id,
            locked=[],
        )
    )
    await session.flush()
    await flow_vis(ctx, VisTally())
    assert await vis_of(ctx, mage.id, SpellForm.FIRE) >= ctx.rules.vis.site_yield
    shaped = await shape_casting(ctx, mage, None, profile, effects=[RiteEffectKind.DAMAGE], mastery=0, caster_god=None, warded=1.0)
    assert shaped.strength > 1
    assert any("vis" in line for line in shaped.notes)


async def test_a_community_sells_its_surplus_vis_to_a_neighbour(ctx: TickContext, session: AsyncSession, world: CoreWorld) -> None:
    seller = await settlement(session, "Arkwell", world, world.regions[0])
    await settlement(session, "Brin", world, world.regions[0], wealth=90)
    start = ctx.rules.vis.surplus + 5
    session.add(VisStockRow(holder_node_id=seller.id, form=SpellForm.WATER, amount=start, locked=[]))
    await session.flush()
    tally = VisTally()
    await flow_vis(ctx, tally)
    assert tally.traded > 0
    assert await vis_of(ctx, seller.id, SpellForm.WATER) == start - tally.traded
    bought = await session.scalars(select(VisStockRow).where(VisStockRow.form == SpellForm.WATER, VisStockRow.holder_node_id != seller.id))
    assert sum(row.amount for row in bought) == tally.traded


async def test_a_hostile_rite_that_cannot_pierce_resistance_is_resisted(ctx: TickContext, session: AsyncSession, world: CoreWorld) -> None:
    mage, _, profile = await rite_of(ctx, session, world)
    target = await mortal(session, "Tarn", world, world.regions[0].id)
    shaped = await shape_casting(ctx, mage, target, profile, effects=[RiteEffectKind.DAMAGE], mastery=0, caster_god=None, warded=10.0)
    assert shaped.resisted


async def test_a_paradigm_closer_to_the_truth_makes_rites_more_reliable(ctx: TickContext, session: AsyncSession, world: CoreWorld) -> None:
    _, _, profile = await rite_of(ctx, session, world)
    grammar = await ensure_grammar(session, ctx.rules, profile)
    false = await entity(session, "Wrong Lore", EntityType.THEORY, TheoryStats(), world_id=world.world.id)
    true = await entity(session, "Right Lore", EntityType.THEORY, TheoryStats(), world_id=world.world.id)
    session.add_all(
        [
            TheoryProfileRow(theory_entity_id=false.id, domain=TheoryDomain.MAGIC, correctness=0, locked=[]),
            TheoryProfileRow(theory_entity_id=true.id, domain=TheoryDomain.MAGIC, correctness=100, locked=[]),
        ]
    )
    await session.flush()
    grammar.paradigm_entity_id = false.id
    low = await paradigm_factor(ctx, grammar)
    grammar.paradigm_entity_id = true.id
    high = await paradigm_factor(ctx, grammar)
    assert low < high


async def test_a_believed_myth_strengthens_its_rite(ctx: TickContext, session: AsyncSession, world: CoreWorld) -> None:
    mage, _, profile = await rite_of(ctx, session, world)
    grammar = await ensure_grammar(session, ctx.rules, profile)
    legend = await entity(session, "The First Fire", EntityType.LEGEND, LegendStats(), world_id=world.world.id)
    session.add(LegendProfileRow(legend_entity_id=legend.id, archetype=LegendArchetype.CREATION, credence=100, distortion=0, locked=[]))
    await session.flush()
    grammar.myth_entity_id = legend.id
    factor, corrupted = await myth_factor(ctx, mage, grammar)
    assert factor > 1
    assert not corrupted


async def test_a_dispel_lifts_a_rite_curse_and_unmakes_a_rival_enchantment(ctx: TickContext, session: AsyncSession, world: CoreWorld) -> None:
    mage, _, _ = await rite_of(ctx, session, world)
    victim = await mortal(session, "Hale", world, world.regions[0].id)
    await afflict(ctx, victim, PackageKind.HUNGER_CURSE, Transmission.CURSE)
    law = await lay_enchantment(
        ctx, world.son.id, name="The Still Air", effect=NaturalLaw.BOUNTY, world_id=world.world.id, region_id=None, strength=40, vis_form=None
    )
    upkeep = await session.get(LawUpkeepRow, law.law_entity_id)
    assert upkeep is not None
    upkeep.dispel_resistance = 1
    await session.flush()
    text = await dispel_force(ctx, mage, victim, 10)
    assert "hunger" in text
    law_entity = await session.get(EntityRow, law.law_entity_id)
    assert law_entity is not None
    assert law_entity.status is EntityStatus.DESTROYED


async def test_long_exposure_warps_a_mortal_through_its_stages(ctx: TickContext, session: AsyncSession, world: CoreWorld) -> None:
    mage = await mortal(session, "Ivo", world, world.regions[0].id)
    await expose(ctx, mage.id, ctx.rules.warping.unmoored_at)
    await warp_world(ctx, WarpTally())
    row = await session.get(WarpingRow, mage.id)
    assert row is not None
    assert row.stage == 3
    warped = await session.scalar(select(AfflictionRow).where(AfflictionRow.bearer_node_id == mage.id, AfflictionRow.package == PackageKind.WARPING))
    assert warped is not None
    assert warped.stage == 3


async def test_an_enchanted_item_spends_its_charges_cracks_when_overused_and_recharges_from_vis(
    ctx: TickContext, session: AsyncSession, world: CoreWorld
) -> None:
    owner = await mortal(session, "Kel", world, world.regions[0].id)
    item = await entity(session, "Bright Ring", EntityType.ITEM, ItemStats(), world_id=world.world.id, location_id=owner.location_id)
    await profile_of(ctx, item, ItemClass.RING)
    await bond(session, owner.id, item.id, BondKind.OWNS)
    spell = ItemEnchantmentRow(item_entity_id=item.id, effect=RiteEffectKind.WARD, strength=30, charges=1, capacity=2, recharge=RechargeRule.VIS)
    session.add(spell)
    await session.flush()
    assert await use_charge(ctx, item, spell, owner)
    assert not await use_charge(ctx, item, spell, owner)
    profile = await session.get(ItemProfileRow, item.id)
    assert profile is not None
    assert profile.condition < 100
    session.add(VisStockRow(holder_node_id=owner.id, form=SpellForm.SPIRIT, amount=5, locked=[]))
    await session.flush()
    await recharge_all(ctx, ChargeTally())
    assert spell.charges == 1


async def test_longevity_adds_years_while_paid_and_takes_them_back_when_it_lapses(ctx: TickContext, session: AsyncSession, world: CoreWorld) -> None:
    elder = await mortal(session, "Orla", world, world.regions[0].id, lifespan=70)
    row = await begin_longevity(ctx, elder, SpellForm.BODY)
    assert row is not None
    session.add(VisStockRow(holder_node_id=elder.id, form=SpellForm.BODY, amount=1, locked=[]))
    await session.flush()
    await tend_longevity(ctx, LongevityTally())
    assert stat(elder, "lifespan") == 70 + ctx.rules.longevity.years
    assert row.dependence > 0
    await tend_longevity(ctx, LongevityTally())
    assert stat_or(elder, "lifespan", 0) < 70 + ctx.rules.longevity.years


async def test_a_global_enchantment_lapses_when_its_upkeep_goes_unpaid(ctx: TickContext, session: AsyncSession, world: CoreWorld) -> None:
    law = await lay_enchantment(
        ctx, world.son.id, name="Long Calm", effect=NaturalLaw.BOUNTY, world_id=world.world.id, region_id=None, strength=60, vis_form=None
    )
    world.son.essence = 0
    for _ in range(ctx.rules.global_enchantments.lapse_after):
        assert await keep_law(ctx, law) is False
    entity_row = await session.get(EntityRow, law.law_entity_id)
    assert entity_row is not None
    assert entity_row.status is EntityStatus.DESTROYED
    upkeep = await session.get(LawUpkeepRow, law.law_entity_id)
    assert upkeep is not None
    assert upkeep.source is LawSource.ENCHANTMENT


async def test_the_god_can_reset_grammar_and_set_vis(ctx: TickContext, session: AsyncSession, world: CoreWorld) -> None:
    _, rite, _ = await rite_of(ctx, session, world)
    edited = await control.edit_grammar(ctx, rite.id, {"range": "world"}, [])
    assert edited.range is SpellRange.WORLD
    assert "range" in edited.locked
    reset = await control.delete_grammar(ctx, rite.id)
    assert reset.range is SpellRange.SIGHT
    held_vis = await control.set_vis(ctx, world.son.id, SpellForm.LIGHT, 9, hold=True)
    assert held_vis.amount == 9
    assert "amount" in held_vis.locked


async def foreign_caster(session: AsyncSession, world: CoreWorld) -> ForeignGodRow:
    row = ForeignGodRow(
        name="Outlander",
        domain_primary=Domain.SEA,
        world_id=world.world.id,
        power=60,
        status=ForeignGodStatus.AWAKE,
        strength=50,
        endurance=50,
        agility=50,
        wisdom=50,
        cunning=50,
        will=50,
        creativity=50,
        charisma=50,
        might=50,
        sanity=80,
        created_epoch=1,
    )
    session.add(row)
    await session.flush()
    return row


async def test_every_kind_of_caster_pays_to_keep_its_enchantment(ctx: TickContext, session: AsyncSession, world: CoreWorld) -> None:
    outsider = await foreign_caster(session, world)
    mage = await mortal(session, "Wren", world, world.regions[0].id)
    order = await entity(session, "The Order", EntityType.FACTION, FactionStats(), world_id=world.world.id, location_id=world.regions[0].id)
    member = await mortal(session, "Yara", world, world.regions[0].id)
    await bond(session, member.id, order.id, BondKind.MEMBER_OF)
    for holder in (mage.id, member.id):
        session.add(VisStockRow(holder_node_id=holder, form=SpellForm.AIR, amount=10, locked=[]))
    await session.flush()
    before = {"son": world.son.essence, "creator": world.creator.essence, "foreign": outsider.power}
    laws = {
        caster: await lay_enchantment(
            ctx, caster, name=f"Calm {index}", effect=NaturalLaw.BOUNTY, world_id=world.world.id, region_id=None, strength=60, vis_form=None
        )
        for index, caster in enumerate((world.son.id, world.creator.id, outsider.id, mage.id, order.id))
    }
    for law in laws.values():
        assert await keep_law(ctx, law) is True
    assert world.son.essence < before["son"]
    assert world.creator.essence < before["creator"]
    assert outsider.power < before["foreign"]
    assert await vis_of(ctx, mage.id, SpellForm.AIR) < 10
    assert await vis_of(ctx, member.id, SpellForm.AIR) < 10
    broke = await mortal(session, "Zeb", world, world.regions[0].id)
    unpaid = await lay_enchantment(
        ctx, broke.id, name="Calm unpaid", effect=NaturalLaw.BOUNTY, world_id=world.world.id, region_id=None, strength=60, vis_form=None
    )
    assert await keep_law(ctx, unpaid) is False
