from aerona.catalog.identity import IDENTITY_LAYERS, NEW_LAYERS
from aerona.db.tables.belonging import HeldIdentityRow
from aerona.domain.enums.belonging import IdentityLayer, SalienceDriver
from aerona.engine.belonging.effects import shared_weight
from aerona.engine.belonging.identities import keep_holder
from aerona.engine.primitives.distance import RegionAtlas
from aerona.rules.registry import Rules
from tests.engine.society.factories import Realm, context, mortal, settlement

RULES = Rules()


def test_twelve_layers_each_with_its_own_base_weight() -> None:
    assert len(IDENTITY_LAYERS) == len(IdentityLayer) == 14
    assert set(NEW_LAYERS) == {IdentityLayer.LANGUAGE, IdentityLayer.KIND, IdentityLayer.CAUSE}
    assert all(spec.base(RULES) == 30 for layer, spec in IDENTITY_LAYERS.items() if layer not in {IdentityLayer.GIFT, IdentityLayer.CALLING})
    assert (IDENTITY_LAYERS[IdentityLayer.GIFT].base(RULES), IDENTITY_LAYERS[IdentityLayer.CALLING].base(RULES)) == (15, 20)


async def test_a_claimed_strength_outlives_the_epoch_and_weighs_in_trust(realm: Realm) -> None:
    town = await settlement(realm, "Brindle")
    first, second = await mortal(realm, "Ama", location_id=town.id), await mortal(realm, "Teodor", location_id=town.id)
    ctx = context(realm.session)
    claimed = HeldIdentityRow(holder_entity_id=first.id, layer=IdentityLayer.LOCALITY, strength=90, salience=60, locked=[])
    realm.session.add(claimed)
    await realm.session.flush()
    targets = {layer: (60, SalienceDriver.BASELINE) for layer in IdentityLayer}
    atlas = await RegionAtlas.load(realm.session)
    await keep_holder(ctx, atlas, first, targets, 100)
    await keep_holder(ctx, atlas, second, targets, 100)
    await realm.session.flush()
    assert claimed.strength == 90 and claimed.value_node_id == town.id
    mine = {IdentityLayer.LOCALITY: claimed}
    theirs = {IdentityLayer.LOCALITY: await realm.session.get(HeldIdentityRow, (second.id, IdentityLayer.LOCALITY))}
    loose = HeldIdentityRow(holder_entity_id=first.id, layer=IdentityLayer.LOCALITY, value_node_id=town.id, strength=10, salience=60, locked=[])
    assert shared_weight(mine, theirs) > shared_weight({IdentityLayer.LOCALITY: loose}, theirs)
