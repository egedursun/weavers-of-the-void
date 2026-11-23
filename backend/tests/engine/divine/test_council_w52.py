from sqlalchemy import select

from aerona.db.tables.divine import CouncilRulingRow, DivineWoundRow
from aerona.db.tables.faith import SpiritProfileRow
from aerona.db.tables.interconnect import IncidentRow
from aerona.db.tables.mythic import ServitorRow
from aerona.domain.enums.divine import CouncilMotion, PenanceDeed, SonPunishment, WoundCause
from aerona.domain.enums.domain import Domain
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.mythic import ServitorOrigin, ServitorRole
from aerona.domain.models.entity_stats import SpiritStats
from aerona.engine.divine import control
from aerona.engine.divine.rulings import enforce_rulings
from aerona.engine.mythic.servitors import ServitorTally, fall, make_servitor, raise_offspring
from aerona.engine.recording.record import record
from tests.engine.divine.pantheon import god
from tests.engine.society.factories import Realm, context, make, mortal, tuned


async def test_a_penance_is_kept_by_its_deed_and_a_missed_one_brings_chains(realm: Realm) -> None:
    keeper = await god(realm, "Ondra", Domain.SEA, Domain.STORM)
    shirker = await god(realm, "Vorn", Domain.WAR, Domain.STONE)
    ctx = context(realm.session, tuned(council={"penance_epochs": 2}), epoch=3)
    kept, lines = await control.decree(
        ctx, CouncilMotion.PUNISH_SON, target_id=keeper.id, punishment=SonPunishment.PENANCE, penance_deed=PenanceDeed.RAISE_HERO
    )
    missed, _ = await control.decree(ctx, CouncilMotion.PUNISH_SON, target_id=shirker.id, punishment=SonPunishment.PENANCE, penance_deed=PenanceDeed.UNDO_CURSE)
    assert kept.penance_deed is PenanceDeed.RAISE_HERO and kept.until_epoch == 5 and "raise a hero" in lines[0]
    quester = await mortal(realm, "Tal")
    await record(
        ctx,
        "heroism.victory",
        roles={IncidentRole.ACTOR: quester.id, IncidentRole.OPPONENT: shirker.id, IncidentRole.PATRON: keeper.id},
        facts={"danger": 50, "charisma_gain": 2},
    )
    fame = keeper.fame
    assert await enforce_rulings(ctx) >= 1
    assert not kept.active and keeper.fame > fame and missed.active and not shirker.chained
    late = context(realm.session, tuned(council={"penance_epochs": 2}), epoch=5)
    await enforce_rulings(late)
    assert shirker.chained and missed.punishment is SonPunishment.CHAIN
    assert await realm.session.scalar(select(IncidentRow).where(IncidentRow.kind == "council.penance_failed")) is not None


async def test_an_essence_fine_moves_essence_to_the_other_gods(realm: Realm) -> None:
    fined = await god(realm, "Ondra", Domain.SEA, Domain.STORM)
    other = await god(realm, "Vorn", Domain.WAR, Domain.STONE)
    fined.essence, other.essence = 100, 10
    await realm.session.flush()
    ctx = context(realm.session, tuned(council={"essence_fine_share_pct": 20}))
    ruling, lines = await control.decree(ctx, CouncilMotion.PUNISH_SON, target_id=fined.id, punishment=SonPunishment.ESSENCE_FINE)
    assert fined.essence == 80 and other.essence == 30 and "20 essence" in lines[0]
    assert isinstance(ruling, CouncilRulingRow)
    assert await realm.session.scalar(select(IncidentRow).where(IncidentRow.kind == "council.penalty")) is not None


async def test_a_servitor_that_falls_comes_over_defected_and_wounds_its_old_god(realm: Realm) -> None:
    old = await god(realm, "Ondra", Domain.SEA, Domain.STORM)
    await god(realm, "Mira", Domain.SEA, Domain.MOON)
    ctx = context(realm.session, tuned(servitors={"fall_pct": 100, "defected_loyalty": 40}, divine_wounds={"betrayal_pct": 100}))
    row = await make_servitor(ctx, old.id, name="Gull", role=ServitorRole.MESSENGER, post_id=None, world_id=realm.world.id)
    row.loyalty = 0
    await fall(ctx, row, ServitorTally())
    assert row.origin is ServitorOrigin.DEFECTED and row.former_god_node_id == old.id and row.loyalty == 40 and row.god_node_id != old.id
    wound = await realm.session.scalar(select(DivineWoundRow).where(DivineWoundRow.god_node_id == old.id))
    assert wound is not None and wound.cause is WoundCause.BETRAYAL
    joined = await realm.session.scalar(select(IncidentRow).where(IncidentRow.kind == "servitor.joined"))
    assert joined is not None


async def test_the_soul_of_a_gods_child_rises_born_into_its_service(realm: Realm) -> None:
    parent = await god(realm, "Ondra", Domain.SEA, Domain.STORM)
    child = await mortal(realm, "Tide-born")
    child.creator_son_id, child.status, child.end_epoch = parent.id, EntityStatus.DEAD, 2
    soul = await make(realm.session, "Shade of Tide-born", EntityType.SPIRIT, SpiritStats(strength=40), world_id=realm.world.id)
    realm.session.add(SpiritProfileRow(spirit_entity_id=soul.id, origin_mortal_id=child.id, locked=[]))
    await realm.session.flush()
    ctx = context(realm.session, tuned(servitors={"born_rise_pct": 100}))
    tally = ServitorTally()
    await raise_offspring(ctx, tally)
    row = await realm.session.get(ServitorRow, soul.id)
    assert row is not None and row.origin is ServitorOrigin.BORN and row.god_node_id == parent.id and tally.raised == 1
