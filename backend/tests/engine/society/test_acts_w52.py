from sqlalchemy import select

from aerona.catalog.diets import DIETS
from aerona.catalog.ethics import ACT_LABELS
from aerona.catalog.mind import ACT_READINGS
from aerona.catalog.renown import ACT_RENOWN, AXES, GLORIOUS
from aerona.db.tables.interconnect import IncidentRow
from aerona.db.tables.mind import CultureEthicRow
from aerona.domain.enums.ecology import Diet
from aerona.domain.enums.mind import ActKind, EthicalStance
from aerona.domain.enums.renown import ReputationAxis
from aerona.engine.mind.ethics import write_stance
from aerona.engine.mind.hooks import committed
from tests.engine.society.factories import Realm, context, mortal, people

NEW_ACTS = (ActKind.LYING, ActKind.DRUNKENNESS, ActKind.TOMB_ROBBING, ActKind.USING_CHARMS, ActKind.FEEDING_ON_HOSTS, ActKind.KILLING_SACRED_ANIMAL)


def test_every_act_is_labelled_read_by_values_and_renowned() -> None:
    assert len(ActKind) == 59
    for act in NEW_ACTS:
        assert ACT_LABELS[act] and ACT_READINGS[act] and act in ACT_RENOWN
    assert {ReputationAxis.MERCY, ReputationAxis.JUSTICE} <= GLORIOUS and len(AXES) == 11
    assert {diet for diet, spec in DIETS.items() if spec.feeds_on_hosts} == {Diet.PARASITE, Diet.SANGUIVORE}


async def test_a_new_act_is_judged_by_the_doers_own_culture(realm: Realm) -> None:
    folk = await people(realm, "Kin")
    liar = await mortal(realm, "Liar")
    ctx = context(realm.session)
    await write_stance(realm.session, folk.id, ActKind.LYING, EthicalStance.SHAMEFUL, ctx.epoch)
    await realm.session.flush()
    held = await realm.session.scalar(select(CultureEthicRow).where(CultureEthicRow.holder_entity_id == folk.id, CultureEthicRow.act == ActKind.LYING))
    assert held is not None and held.stance is EthicalStance.SHAMEFUL
    assert await committed(ctx, liar.id, ActKind.LYING, seen=False) == 0
    assert "ethics.act_judged" not in set(await realm.session.scalars(select(IncidentRow.kind)))
