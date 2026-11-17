from sqlalchemy import select

from aerona.db.repositories.cosmos import CosmosRepository, CreatorDraft
from aerona.db.tables.cosmos import CreatorRow
from aerona.db.tables.creator_bonds import CovenantRow
from aerona.db.tables.divine import WorldAttentionRow
from aerona.db.tables.divine_powers import DivinePowerRow
from aerona.db.tables.pantheon import PantheonStructureRow, PantheonTieRow
from aerona.domain.enums.creator import CovenantState
from aerona.domain.enums.divine import DivineObject, DivineVerb
from aerona.domain.enums.domain import Domain
from aerona.engine.divine.creator_bonds import keep_creator_bonds
from aerona.engine.divine.grammar import keep_powers
from aerona.engine.divine.pantheon import keep_pantheons
from tests.engine.divine.pantheon import foreign, god, worship
from tests.engine.society.factories import Realm, context, people, settlement


async def creator_of(realm: Realm) -> CreatorRow:
    found = await realm.session.scalar(select(CreatorRow).limit(1))
    if found is not None:
        return found
    return await CosmosRepository(realm.session).create_creator(
        CreatorDraft(name="Aeron", essence=500, mood_contentment=50, mood_anger=20, mood_interest=60, mood_loneliness=30)
    )


async def test_worship_spread_over_communities_grants_a_god_a_power_of_its_first_domain(realm: Realm) -> None:
    son = await god(realm, "Ondra", Domain.SEA, Domain.STORM)
    for name in ("Brightwater", "Lowmere"):
        await worship(realm, await settlement(realm, name), son.id)
    ctx = context(realm.session)
    await keep_powers(ctx)
    power = await realm.session.scalar(select(DivinePowerRow).where(DivinePowerRow.holder_node_id == son.id))
    assert power is not None
    assert power.domains == [Domain.SEA.value] and power.verb is DivineVerb.INSPIRE and power.object is DivineObject.VALUE
    assert power.strength == ctx.rules.divine_grammar.grant_strength
    await keep_powers(ctx)
    assert len(list(await realm.session.scalars(select(DivinePowerRow).where(DivinePowerRow.holder_node_id == son.id)))) == 1


async def test_a_god_with_too_few_faithful_is_granted_nothing(realm: Realm) -> None:
    son = await god(realm, "Varr", Domain.LIES, Domain.SHADOW)
    await worship(realm, await settlement(realm, "Lonehold"), son.id)
    await keep_powers(context(realm.session))
    assert await realm.session.scalar(select(DivinePowerRow).where(DivinePowerRow.holder_node_id == son.id)) is None


async def test_the_creator_returning_to_a_neglected_world_warns_and_offers_a_covenant(realm: Realm) -> None:
    await creator_of(realm)
    folk = await people(realm, "Tarn")
    ctx = context(realm.session)
    absence = ctx.rules.creator_bonds.absence_epochs
    realm.session.add(WorldAttentionRow(world_id=realm.world.id, attention=90, watched=True, far_epochs=absence, locked=[]))
    await realm.session.flush()
    await keep_creator_bonds(ctx)
    covenant = await realm.session.scalar(select(CovenantRow).where(CovenantRow.people_entity_id == folk.id))
    assert covenant is not None and covenant.state in {CovenantState.OFFERED, CovenantState.SEALED}
    attention = await realm.session.get(WorldAttentionRow, realm.world.id)
    assert attention is not None and attention.far_epochs == 0


async def test_a_world_still_far_from_the_eye_is_offered_nothing(realm: Realm) -> None:
    await creator_of(realm)
    folk = await people(realm, "Tarn")
    ctx = context(realm.session)
    realm.session.add(WorldAttentionRow(world_id=realm.world.id, attention=1, watched=False, far_epochs=ctx.rules.creator_bonds.absence_epochs, locked=[]))
    await realm.session.flush()
    await keep_creator_bonds(ctx)
    assert await realm.session.scalar(select(CovenantRow).where(CovenantRow.people_entity_id == folk.id)) is None


async def test_two_foreign_gods_of_a_world_form_a_pantheon_with_ties(realm: Realm) -> None:
    first = await foreign(realm.session, realm, "Ussamar", Domain.WAR, power=70)
    second = await foreign(realm.session, realm, "Ilthe", Domain.HARVEST, power=40)
    await keep_pantheons(context(realm.session))
    structure = await realm.session.get(PantheonStructureRow, realm.world.id)
    assert structure is not None and structure.head_node_id == first.id
    assert await realm.session.get(PantheonTieRow, (first.id, second.id)) is not None
