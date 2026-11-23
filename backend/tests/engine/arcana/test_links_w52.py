from aerona.catalog.life.crafts import KNOWN_NAME_TOKENS, TOKEN_STRENGTH
from aerona.db.tables.crafts import SympatheticLinkRow
from aerona.db.tables.intrigue import TrueNameRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.crafts import LinkToken
from aerona.domain.enums.entity import EntityType
from aerona.domain.models.entity_stats import ItemStats
from aerona.engine.crafts.sympathy import tokens_within_reach
from aerona.services.integrity.w52_agent_a import link_by_name, unknown_true_names
from tests.engine.society.factories import Realm, context, link, make, mortal, tuned


def test_every_token_has_a_strength_rule_and_a_true_name_is_the_strongest() -> None:
    rules = tuned(links={"true_name_strength": 100, "possession_strength": 25})
    assert TOKEN_STRENGTH[LinkToken.TRUE_NAME](rules) == 100 and TOKEN_STRENGTH[LinkToken.POSSESSION](rules) == 25
    assert max(TOKEN_STRENGTH, key=lambda token: TOKEN_STRENGTH[token](rules)) is LinkToken.TRUE_NAME
    assert {LinkToken.TRUE_NAME} == KNOWN_NAME_TOKENS


async def test_a_kept_thing_gives_a_link_within_reach(realm: Realm) -> None:
    caster, target = await mortal(realm, "Ossa"), await mortal(realm, "Vey")
    ctx = context(realm.session)
    assert LinkToken.POSSESSION not in await tokens_within_reach(ctx, caster.id, target.id)
    cloak = await make(realm.session, "Grey Cloak", EntityType.ITEM, ItemStats(), world_id=realm.world.id, location_id=realm.region.id)
    await link(realm.session, target.id, cloak.id, BondKind.OWNS)
    assert LinkToken.POSSESSION in await tokens_within_reach(ctx, caster.id, target.id)


async def test_a_true_name_link_held_by_one_who_does_not_know_the_name_falls_back_to_a_name(realm: Realm) -> None:
    session = realm.session
    caster, target = await mortal(realm, "Ossa"), await mortal(realm, "Vey")
    row = SympatheticLinkRow(holder_node_id=caster.id, target_node_id=target.id, token=LinkToken.TRUE_NAME, strength=100, obtained_epoch=1, locked=[])
    session.add(row)
    session.add(TrueNameRow(bearer_node_id=target.id, name="Ithren", known_by=[], since_epoch=1, locked=[]))
    await session.flush()
    assert await unknown_true_names(session) == [row.id]
    await link_by_name(session, row.id)
    assert row.token is LinkToken.NAME and await unknown_true_names(session) == []
