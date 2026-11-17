from dataclasses import replace

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.repositories.foreign_gods import ForeignGodDraft, ForeignGodRepository
from aerona.db.repositories.sons import SonRepository
from aerona.db.tables.bonds import BondRow
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.domain import Domain
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.son import SonDeathCause, SonStatus
from aerona.domain.models.stats import StatBlock
from aerona.engine.gods.devotion import SchemeKind, resurrection_state, sibling_scheme
from aerona.engine.gods.god_death import god_death
from aerona.engine.phases.god_death import death_engine
from aerona.rules.registry import Rules
from tests.engine.gods.factories import GodsWorld, bond, chronicle_keys, make_context, make_entity, make_son


def _tuned(rules: Rules, **changes: int) -> Rules:
    return replace(rules, death=replace(rules.death, **changes))


async def _foreign_god(session: AsyncSession, world: GodsWorld) -> None:
    await ForeignGodRepository(session).create(
        ForeignGodDraft(name="Ur", world_id=world.world.id, domain_primary=Domain.SEA, power=50, stats=StatBlock.uniform(50), created_epoch=1)
    )


async def test_bargain_hands_the_faithful_community_to_the_foreign_god(session: AsyncSession, world: GodsWorld, rules: Rules) -> None:
    await _foreign_god(session, world)
    son = await make_son(session, "Velkar", world.world.id)
    friend = await make_son(session, "Iolen", world.world.id, essence=500)
    people = await make_entity(session, "Faithful", EntityType.PEOPLE, world_id=world.world.id, location_id=world.region.id)
    await bond(session, people.id, son.id, BondKind.WORSHIPS)
    ctx = make_context(session, rules, 3)
    await god_death(ctx, son, "fell", SonDeathCause.OTHER)
    result = await sibling_scheme(ctx, friend, son, SchemeKind.BARGAIN)
    assert result.contribution == rules.death.sibling_bargain_devotion
    assert friend.essence == 500 - rules.death.sibling_bargain_cost
    bonds = list(await session.scalars(select(BondRow).where(BondRow.source_node_id == people.id, BondRow.kind == BondKind.WORSHIPS)))
    by_target = {item.target_node_id: item.state for item in bonds}
    assert by_target[son.id] is not BondState.ACTIVE
    assert BondState.ACTIVE in {state for target, state in by_target.items() if target != son.id}
    assert "gods.death.scheme" in await chronicle_keys(session)


async def test_close_sibling_schemes_on_their_own(session: AsyncSession, world: GodsWorld, rules: Rules) -> None:
    tuned = _tuned(rules, auto_intrigue_chance=100, auto_intrigue_min_relation=10, sibling_descent_success=100, rite_chance=0, sacrifice_chance=0)
    dead = await make_son(session, "Velkar", world.world.id)
    friend = await make_son(session, "Iolen", world.world.id, essence=500)
    await SonRepository(session).change_relation(friend.id, dead.id, 50)
    await god_death(make_context(session, tuned, 3), dead, "fell", SonDeathCause.OTHER)
    essence = friend.essence
    first = await resurrection_state(session, tuned, dead, 3)
    assert first is not None
    await death_engine(make_context(session, tuned, 4, "death_engine"))
    assert friend.essence == essence - tuned.death.sibling_descent_cost
    state = await resurrection_state(session, tuned, dead, 4)
    assert state is not None and state.devotion - first.devotion >= tuned.death.sibling_descent_devotion
    assert "gods.death.scheme" in await chronicle_keys(session)


async def test_unaffordable_scheme_is_skipped(session: AsyncSession, world: GodsWorld, rules: Rules) -> None:
    tuned = _tuned(rules, auto_intrigue_chance=100, auto_intrigue_min_relation=10)
    dead = await make_son(session, "Velkar", world.world.id)
    friend = await make_son(session, "Iolen", world.world.id, essence=1)
    await SonRepository(session).change_relation(friend.id, dead.id, 50)
    await god_death(make_context(session, tuned, 3), dead, "fell", SonDeathCause.OTHER)
    await death_engine(make_context(session, tuned, 4, "death_engine"))
    assert friend.essence == 1
    assert "gods.death.scheme" not in await chronicle_keys(session)


async def test_hostile_sibling_scatters_the_bones_on_their_own(session: AsyncSession, world: GodsWorld, rules: Rules) -> None:
    tuned = _tuned(
        rules, auto_hinder_chance=100, auto_hinder_relation=30, auto_intrigue_chance=0, hinder_return_devotion_loss=10, rite_chance=0, sacrifice_chance=0
    )
    dead = await make_son(session, "Velkar", world.world.id)
    rival = await make_son(session, "Iolen", world.world.id, essence=500)
    friend = await make_son(session, "Brann", world.world.id, essence=500)
    await SonRepository(session).change_relation(rival.id, dead.id, -50)
    ctx = make_context(session, tuned, 3)
    await god_death(ctx, dead, "fell", SonDeathCause.OTHER)
    await sibling_scheme(ctx, friend, dead, SchemeKind.RITE)
    before = (await resurrection_state(session, tuned, dead, 3)).devotion
    await death_engine(make_context(session, tuned, 4, "death_engine"))
    after = await resurrection_state(session, tuned, dead, 4)
    assert after is not None and after.devotion == before - tuned.death.hinder_return_devotion_loss
    assert rival.essence == 500 - tuned.death.hinder_return_cost
    assert "gods.death.return_hindered" in await chronicle_keys(session)
    assert rival.status is SonStatus.ACTIVE
