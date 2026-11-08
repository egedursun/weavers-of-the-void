from sqlalchemy import select

from aerona.db.tables.polity import OfficeRow
from aerona.db.tables.relations import PersuasionRow
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.polity import OfficeKind
from aerona.domain.enums.relations import PersuasionAim
from aerona.domain.models.entity_stats import PolityStats, TreatyStats
from aerona.engine.relations.persuasion import COUNCIL_VOICES, Argument, council_lift, envoy_sways, lift
from tests.engine.society.factories import Realm, context, make, mortal, tuned

CERTAIN = tuned(persuasion={"threshold": 0, "jitter": 0, "envoy_pct": 100, "council_pct": 100})
HOPELESS = tuned(persuasion={"threshold": 200, "jitter": 0, "envoy_pct": 100})


async def seat(realm: Realm, polity_id: int, kind: OfficeKind, name: str) -> int:
    holder = await mortal(realm, name)
    realm.session.add(OfficeRow(polity_entity_id=polity_id, kind=kind, holder_entity_id=holder.id, powers=[], locked=[]))
    await realm.session.flush()
    return holder.id


async def test_a_ruler_without_a_council_gets_no_lift(realm: Realm) -> None:
    polity = await make(realm.session, "Quiet Crown", EntityType.POLITY, PolityStats(), world_id=realm.world.id)
    ruler = await seat(realm, polity.id, OfficeKind.RULER, "Lone")
    assert await council_lift(context(realm.session, CERTAIN), ruler, polity.id) == 1.0


async def test_the_council_lift_is_the_mean_of_its_voices_and_never_counts_the_speaker(realm: Realm) -> None:
    ctx = context(realm.session, CERTAIN)
    polity = await make(realm.session, "Loud Crown", EntityType.POLITY, PolityStats(), world_id=realm.world.id)
    ruler = await seat(realm, polity.id, OfficeKind.RULER, "Speaker")
    councillors = [await seat(realm, polity.id, OfficeKind.CHANCELLOR, f"Councillor {index}") for index in range(COUNCIL_VOICES + 1)]
    swayed = await council_lift(ctx, ruler, polity.id)
    rows = list(await realm.session.scalars(select(PersuasionRow).where(PersuasionRow.speaker_node_id == ruler).order_by(PersuasionRow.id)))
    assert len(rows) == COUNCIL_VOICES
    assert all(row.aim is PersuasionAim.VOTE and row.subject_node_id == polity.id and row.target_node_id in councillors for row in rows)
    assert ruler not in {row.target_node_id for row in rows}
    expected = sum(1 + ctx.rules.persuasion.council_pct / 100 * (row.score - 50) / 100 for row in rows) / len(rows)
    assert abs(swayed - expected) < 1e-9


async def test_lift_rises_with_the_argument_score(realm: Realm) -> None:
    assert lift(100, Argument(100, True, None)) > lift(100, Argument(50, True, None)) == 1.0 > lift(100, Argument(0, False, None))


async def test_a_realm_without_an_envoy_sways_nobody(realm: Realm) -> None:
    proposer = await make(realm.session, "Mute Crown", EntityType.POLITY, PolityStats(), world_id=realm.world.id)
    other = await make(realm.session, "Deaf Crown", EntityType.POLITY, PolityStats(), world_id=realm.world.id)
    treaty = await make(realm.session, "Pact Unspoken", EntityType.TREATY, TreatyStats(), world_id=realm.world.id)
    assert not await envoy_sways(context(realm.session, CERTAIN), proposer.id, [other.id], treaty.id)


async def test_an_ambassador_argues_with_each_ruler_and_wins_the_treaty(realm: Realm) -> None:
    ctx = context(realm.session, CERTAIN)
    proposer = await make(realm.session, "Bright Crown", EntityType.POLITY, PolityStats(), world_id=realm.world.id)
    other = await make(realm.session, "Far Crown", EntityType.POLITY, PolityStats(), world_id=realm.world.id)
    rulerless = await make(realm.session, "Free Folk", EntityType.POLITY, PolityStats(), world_id=realm.world.id)
    treaty = await make(realm.session, "Pact of Light", EntityType.TREATY, TreatyStats(), world_id=realm.world.id)
    envoy = await seat(realm, proposer.id, OfficeKind.AMBASSADOR, "Envoy")
    listener = await seat(realm, other.id, OfficeKind.RULER, "Listener")
    assert await envoy_sways(ctx, proposer.id, [other.id, rulerless.id], treaty.id)
    targets = set(await realm.session.scalars(select(PersuasionRow.target_node_id).where(PersuasionRow.speaker_node_id == envoy)))
    assert targets == {listener, rulerless.id}
    aims = set(await realm.session.scalars(select(PersuasionRow.aim).where(PersuasionRow.speaker_node_id == envoy)))
    assert aims == {PersuasionAim.TREATY}


async def test_one_unconvinced_ruler_sinks_the_envoy(realm: Realm) -> None:
    ctx = context(realm.session, HOPELESS)
    proposer = await make(realm.session, "Dim Crown", EntityType.POLITY, PolityStats(), world_id=realm.world.id)
    other = await make(realm.session, "Cold Crown", EntityType.POLITY, PolityStats(), world_id=realm.world.id)
    treaty = await make(realm.session, "Pact of Cold", EntityType.TREATY, TreatyStats(), world_id=realm.world.id)
    await seat(realm, proposer.id, OfficeKind.CHANCELLOR, "Chancellor")
    await seat(realm, other.id, OfficeKind.RULER, "Stubborn")
    assert not await envoy_sways(ctx, proposer.id, [other.id], treaty.id)
