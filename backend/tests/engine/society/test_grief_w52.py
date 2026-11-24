from sqlalchemy import select

from aerona.catalog.grief import GRIEF_STAGES, OPEN_GRIEF_STAGES
from aerona.db.tables.interconnect import IncidentRow
from aerona.db.tables.mind import GriefRow, MemoryRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.mind import GriefStage, MemoryKind
from aerona.engine.mind.grief import GriefTally, advance
from tests.engine.society.factories import Realm, context, link, mortal, tuned


def test_six_stages_in_order_with_anger_after_shock_and_yearning_before_acceptance() -> None:
    assert len(GRIEF_STAGES) == 7
    assert OPEN_GRIEF_STAGES == (GriefStage.SHOCK, GriefStage.ANGER, GriefStage.BARGAINING, GriefStage.MOURNING, GriefStage.YEARNING)
    assert GRIEF_STAGES[GriefStage.ANGER].angry and GRIEF_STAGES[GriefStage.YEARNING].yearning


async def test_the_anger_of_grief_turns_on_the_killer(realm: Realm) -> None:
    mourner, dead, killer = await mortal(realm, "Spouse"), await mortal(realm, "Lost"), await mortal(realm, "Slayer")
    await link(realm.session, killer.id, dead.id, BondKind.KILLED)
    realm.session.add(
        GriefRow(mourner_node_id=mourner.id, deceased_node_id=dead.id, stage=GriefStage.SHOCK, strength=90, started_epoch=1, stage_epoch=1, length_epochs=2)
    )
    await realm.session.flush()
    rules = tuned(grief={"anger_vengeance_pct": 100})
    await advance(context(realm.session, rules, epoch=3), mourner, GriefTally())
    row = await realm.session.scalar(select(GriefRow).where(GriefRow.mourner_node_id == mourner.id))
    assert row is not None and row.stage is GriefStage.ANGER
    grudge = await realm.session.scalar(
        select(MemoryRow).where(MemoryRow.holder_node_id == mourner.id, MemoryRow.subject_node_id == killer.id, MemoryRow.kind == MemoryKind.KILLED_KIN)
    )
    assert grudge is not None
    assert "mind.grief_stage" in set(await realm.session.scalars(select(IncidentRow.kind)))
