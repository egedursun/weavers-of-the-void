from sqlalchemy import select

from aerona.catalog.arcana import DURATIONS, RANGES, RECHARGES, RITE_CONDITIONS, TARGETS
from aerona.db.tables.arcana import RiteGrammarRow
from aerona.db.tables.celestial import SkyEventRow
from aerona.db.tables.crafts import SympatheticLinkRow
from aerona.db.tables.culture import CastingRow, ItemEnchantmentRow
from aerona.db.tables.interconnect import IncidentRow
from aerona.domain.enums.arcana import RechargeRule, RiteCondition, RiteEnd, SpellDuration, SpellForm, SpellRange, SpellTarget, SpellTechnique
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.crafts import LinkToken
from aerona.domain.enums.culture import RiteEffectKind
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.world import SkyEventKind
from aerona.domain.models.entity_stats import ItemStats, RiteStats
from aerona.engine.arcana.endings import EndingTally, end_rites
from aerona.engine.arcana.grammar import cost_factor, link_factor, power_suffices, reaches
from aerona.engine.arcana.items import recharge
from aerona.engine.crafts.linking import true_named
from aerona.engine.lore.rites import aims_of
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.stats import stat_or
from tests.engine.society.factories import Realm, context, link, make, mortal, tuned


def grammar(rite_id: int, **values: object) -> RiteGrammarRow:
    row = RiteGrammarRow(rite_entity_id=rite_id, technique=SpellTechnique.CONTROL, form=SpellForm.MIND, difficulty=4, locked=[])
    for key, value in values.items():
        setattr(row, key, value)
    return row


def test_every_new_grammar_value_has_its_catalogue_entry() -> None:
    assert RANGES[SpellRange.LINKED].through_link and RANGES[SpellRange.COSMOS].beyond_world
    assert DURATIONS[SpellDuration.SUSTAINED].sustained and DURATIONS[SpellDuration.UNTIL_CONDITION].conditional
    assert TARGETS[SpellTarget.ITEM].item and TARGETS[SpellTarget.LINE].line and TARGETS[SpellTarget.WORLD].world
    assert RITE_CONDITIONS[RiteCondition.TIME].needs_epoch and RITE_CONDITIONS[RiteCondition.DEED].by_anyone
    rules = tuned(arcana={"sky_event_fill": 3, "bodily_offering_fill": 4})
    assert RECHARGES[RechargeRule.SKY_EVENT].fill(rules) == 3 and RECHARGES[RechargeRule.BODILY_OFFERING].fill(rules) == 4


async def test_a_linked_rite_reaches_only_through_its_link_and_a_cosmic_rite_costs_more(realm: Realm) -> None:
    rules = tuned(arcana={"linked_strength_pct": 50, "cosmos_cost_pct": 300})
    caster, target = await mortal(realm, "Ossa"), await mortal(realm, "Vey", location_id=realm.far_region.id)
    atlas = await RegionAtlas.load(realm.session)
    through = grammar(1, range=SpellRange.LINKED)
    assert not reaches(atlas, through, caster, target, linked=0)
    assert reaches(atlas, through, caster, target, linked=80)
    assert link_factor(rules, through, 80) == 0.4
    beyond = grammar(1, range=SpellRange.COSMOS)
    assert reaches(atlas, beyond, caster, target, joined=False)
    assert cost_factor(rules, beyond) == 3 * cost_factor(rules, grammar(1, range=SpellRange.WORLD))


async def test_a_world_rite_needs_the_greatest_power_and_a_line_rite_reaches_the_children(realm: Realm) -> None:
    rules = tuned(arcana={"world_rite_power": 9, "line_reach": 4})
    assert not power_suffices(rules, grammar(1, target=SpellTarget.WORLD), 5)
    assert power_suffices(rules, grammar(1, target=SpellTarget.WORLD), 9)
    parent, child, grandchild = await mortal(realm, "Ama"), await mortal(realm, "Bel"), await mortal(realm, "Cor")
    await link(realm.session, parent.id, child.id, BondKind.PARENT_OF)
    await link(realm.session, child.id, grandchild.id, BondKind.PARENT_OF)
    aims = await aims_of(context(realm.session, rules), grammar(1, target=SpellTarget.LINE), parent)
    assert [aim.id for aim in aims if aim is not None] == [parent.id, child.id, grandchild.id]
    assert await aims_of(context(realm.session, rules), grammar(1, target=SpellTarget.ONE), parent) == [parent]


async def test_a_sustained_working_ends_with_its_caster_and_a_timed_one_at_its_epoch(realm: Realm) -> None:
    session = realm.session
    caster, target = await mortal(realm, "Ossa"), await mortal(realm, "Vey")
    held_rite = await make(session, "Holding Word", EntityType.RITE, RiteStats(power=1, castings=0), world_id=realm.world.id)
    timed_rite = await make(session, "Season Bond", EntityType.RITE, RiteStats(power=1, castings=0), world_id=realm.world.id)
    session.add(grammar(held_rite.id, duration=SpellDuration.SUSTAINED))
    session.add(grammar(timed_rite.id, duration=SpellDuration.UNTIL_CONDITION, condition=RiteCondition.TIME, condition_epoch=4))
    sustained = CastingRow(rite_entity_id=held_rite.id, caster_entity_id=caster.id, target_entity_id=target.id, epoch=2, succeeded=True, effect="")
    timed = CastingRow(rite_entity_id=timed_rite.id, caster_entity_id=caster.id, target_entity_id=target.id, epoch=2, succeeded=True, effect="")
    session.add_all([sustained, timed])
    await session.flush()
    tally = EndingTally()
    await end_rites(context(session, epoch=3), tally)
    assert tally.ended == 0
    caster.status, caster.end_epoch = EntityStatus.DEAD, 3
    await end_rites(context(session, epoch=4), tally)
    assert sustained.end is RiteEnd.CASTER_GONE and timed.end is RiteEnd.CONDITION_MET and tally.ended == 2
    told = await session.scalar(select(IncidentRow).where(IncidentRow.kind == "rite.ended").limit(1))
    assert told is not None


async def test_a_sky_bound_item_fills_at_a_sign_and_a_blood_fed_one_takes_its_holder_hp(realm: Realm) -> None:
    session = realm.session
    rules = tuned(arcana={"sky_event_fill": 2, "bodily_offering_fill": 3, "bodily_offering_harm": 10})
    holder = await mortal(realm, "Keeper")
    item = await make(session, "Star Cup", EntityType.ITEM, ItemStats(), world_id=realm.world.id, location_id=realm.region.id)
    await link(session, holder.id, item.id, BondKind.OWNS)
    sky = ItemEnchantmentRow(item_entity_id=item.id, effect=RiteEffectKind.WARD, strength=10, charges=0, capacity=5, recharge=RechargeRule.SKY_EVENT)
    blood = ItemEnchantmentRow(item_entity_id=item.id, effect=RiteEffectKind.HEAL, strength=10, charges=0, capacity=5, recharge=RechargeRule.BODILY_OFFERING)
    session.add_all([sky, blood])
    await session.flush()
    atlas = await RegionAtlas.load(session)
    ctx = context(session, rules, epoch=4)
    assert await recharge(ctx, atlas, sky, item) == 0
    session.add(SkyEventRow(kind=SkyEventKind.ECLIPSE, epoch=4, world_id=realm.world.id))
    await session.flush()
    assert await recharge(ctx, atlas, sky, item) == 2
    assert await recharge(ctx, atlas, blood, item) == 3 and stat_or(holder, "hp", 0) == 90


async def test_a_true_name_link_strengthens_a_commanding_rite(realm: Realm) -> None:
    session = realm.session
    caster, target = await mortal(realm, "Ossa"), await mortal(realm, "Vey")
    session.add(SympatheticLinkRow(holder_node_id=caster.id, target_node_id=target.id, token=LinkToken.TRUE_NAME, strength=100, obtained_epoch=1, locked=[]))
    await session.flush()
    assert await true_named(session, caster.id, target.id)
    assert not await true_named(session, target.id, caster.id)
