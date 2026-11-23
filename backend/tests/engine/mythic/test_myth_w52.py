from sqlalchemy import select

from aerona.catalog.mythic import ARCHETYPE_TRIALS, GEAS_LAYERS, LINE_LAYERS
from aerona.db.tables.afflictions import AfflictionRow
from aerona.db.tables.interconnect import IncidentRow
from aerona.db.tables.mythic import GeasRow, HeroquestRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.mind import ActKind, SkillKind, SkillSource, ValueAxis, ValueHolder
from aerona.domain.enums.mythic import GeasLayer, GeasMode, GeasState, QuestTrial
from aerona.engine.mind.book import set_skill, write_values
from aerona.engine.mythic.geasa import doom, inherit_geasa, lay_geas
from aerona.engine.mythic.heroquests import trial_of, trial_value
from tests.engine.society.factories import Realm, context, link, mortal, people, settlement, tuned


def test_cunning_and_endurance_are_trials_of_the_myths() -> None:
    trials = {trial for row in ARCHETYPE_TRIALS.values() for trial in row}
    assert {QuestTrial.CUNNING, QuestTrial.ENDURANCE} <= trials
    assert GEAS_LAYERS[GeasLayer.SELF].sworn and not GEAS_LAYERS[GeasLayer.SELF].dooms
    assert {GeasLayer.KIN} == LINE_LAYERS


async def test_a_trial_of_cunning_reads_wit_and_trickery_and_a_god_may_set_the_trial(realm: Realm) -> None:
    session = realm.session
    quester = await mortal(realm, "Ossa", intellect=80)
    await set_skill(session, quester.id, SkillKind.DECEPTION, 40, epoch=1, source=SkillSource.TEACHING)
    row = HeroquestRow(quester_entity_id=quester.id, steps=3, step=0, fidelity=100, deviated=False, interference=0, start_epoch=1, locked=[])
    session.add(row)
    await session.flush()
    ctx = context(session)
    assert await trial_value(ctx, row, quester, QuestTrial.CUNNING, 0) == 60
    assert await trial_value(ctx, row, quester, QuestTrial.ENDURANCE, 0) == 50
    row.trial = QuestTrial.ENDURANCE
    assert await trial_of(ctx, row) is QuestTrial.ENDURANCE


async def test_a_kin_geas_passes_down_a_line_that_holds_its_kin_and_is_told(realm: Realm) -> None:
    session = realm.session
    folk = await people(realm, "Kinfolk")
    town = await settlement(realm, "Hearth")
    await link(session, town.id, folk.id, BondKind.DESCENDS_FROM)
    await write_values(session, ValueHolder.CULTURE, folk.id, {ValueAxis.KINSHIP: 60})
    parent = await mortal(realm, "Ama", location_id=town.id)
    child = await mortal(realm, "Bel", location_id=town.id)
    ctx = context(session, tuned(geasa={"kin_pass_pct": 100, "kin_kinship": 20}))
    await lay_geas(ctx, parent, layer_node_id=parent.id, layer=GeasLayer.KIN, mode=GeasMode.TABOO, act=ActKind.COWARDICE)
    assert await inherit_geasa(ctx, child, (parent, parent)) == 1
    passed = await session.scalar(select(GeasRow).where(GeasRow.bearer_entity_id == child.id))
    assert passed is not None and passed.layer is GeasLayer.KIN and passed.layer_node_id == parent.id
    told = await session.scalar(select(IncidentRow).where(IncidentRow.kind == "geas.laid").limit(1))
    assert told is not None


async def test_a_sworn_geas_broken_shames_its_bearer_without_a_god_s_doom(realm: Realm) -> None:
    session = realm.session
    bearer = await mortal(realm, "Vow")
    ctx = context(session)
    row = await lay_geas(ctx, bearer, layer_node_id=bearer.id, layer=GeasLayer.SELF, mode=GeasMode.TABOO, act=ActKind.OATHBREAKING)
    await doom(ctx, row, bearer, "it broke its word")
    assert row.state is GeasState.BROKEN
    doomed = await session.scalar(select(AfflictionRow.id).where(AfflictionRow.bearer_node_id == bearer.id))
    assert doomed is None
