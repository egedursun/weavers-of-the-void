from sqlalchemy import select

from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.intrigue import HookRow, SchemeRow, SecretRow
from aerona.db.tables.lore import MessageRow
from aerona.db.tables.mortal import MarriageRow
from aerona.db.tables.polity import OfficeRow
from aerona.db.tables.relations import RelationshipRow
from aerona.domain.enums.intrigue import IntrigueSecret, PlotKind
from aerona.domain.enums.polity import OfficeKind
from aerona.engine.intrigue.schemes import STRIKES
from tests.engine.cosmos.factories import make_world
from tests.engine.environment.test_environment import surveyed
from tests.engine.society.factories import Realm, context, mortal
from tests.engine.statecraft.crowns import crown


async def strike(realm: Realm, kind: PlotKind, owner: EntityRow, target: EntityRow) -> str:
    scheme = SchemeRow(owner_node_id=owner.id, kind=kind, target_node_id=target.id, agents=[], power=50, started_epoch=1)
    realm.session.add(scheme)
    await realm.session.flush()
    return await STRIKES[kind](context(realm.session), scheme, owner, target)


async def test_a_forged_letter_goes_only_to_a_realm_of_the_targets_world(realm: Realm) -> None:
    owner = await mortal(realm, "Forger")
    polity, _ = await crown(realm, "Velmar")
    ruler = await mortal(realm, "Queen Otta")
    realm.session.add(OfficeRow(polity_entity_id=polity.id, kind=OfficeKind.RULER, holder_entity_id=ruler.id, powers=[], locked=[]))
    elsewhere, _ = await crown(realm, "Far Throne")
    other_world = await make_world(realm.session, "Far Shore")
    elsewhere.world_id = other_world.id
    await realm.session.flush()
    assert await strike(realm, PlotKind.FORGE_LETTER, owner, ruler) == "there was no one to deceive"
    neighbour, _ = await crown(realm, "Reed Throne")
    assert await strike(realm, PlotKind.FORGE_LETTER, owner, ruler) == "a forged declaration went out in the name of Queen Otta"
    letter = await realm.session.scalar(select(MessageRow).where(MessageRow.forged.is_(True)))
    assert letter is not None and letter.sender_node_id == polity.id and letter.recipient_node_id == neighbour.id


async def test_a_hook_and_a_sway_give_the_plotter_a_hold_and_a_friend(realm: Realm) -> None:
    owner, target = await mortal(realm, "Plotter"), await mortal(realm, "Mark")
    assert await strike(realm, PlotKind.FABRICATE_HOOK, owner, target) == "Plotter gained a hold over Mark"
    assert await realm.session.scalar(select(HookRow).where(HookRow.holder_node_id == owner.id, HookRow.target_node_id == target.id)) is not None
    assert await strike(realm, PlotKind.SWAY, owner, target) == "Mark warmed to Plotter"
    view = await realm.session.scalar(select(RelationshipRow).where(RelationshipRow.holder_node_id == target.id, RelationshipRow.subject_node_id == owner.id))
    assert view is not None and view.friendship > 0


async def test_lovers_elope_into_a_marriage(realm: Realm) -> None:
    owner, target = await mortal(realm, "Lover"), await mortal(realm, "Beloved")
    assert await strike(realm, PlotKind.ELOPE, owner, target) == "Lover and Beloved eloped"
    assert await realm.session.scalar(select(MarriageRow).where(MarriageRow.first_id.in_([owner.id, target.id]))) is not None


async def test_sabotage_scars_the_land_in_secret(realm: Realm) -> None:
    ground = await surveyed(realm)
    owner = await mortal(realm, "Saboteur")
    before = sum(ground.scars.values())
    text = await strike(realm, PlotKind.ECOSABOTAGE, owner, realm.region)
    assert text.startswith(f"the land of {realm.region.name} was ") and "night" not in text
    refreshed = await realm.session.get(RegionEnvironmentRow, realm.region.id)
    assert refreshed is not None and sum(refreshed.scars.values()) > before
    assert await realm.session.scalar(select(SecretRow).where(SecretRow.holder_node_id == owner.id, SecretRow.kind == IntrigueSecret.ECOSABOTAGE))
    adrift = await mortal(realm, "Adrift")
    adrift.location_id = None
    assert await strike(realm, PlotKind.ECOSABOTAGE, owner, adrift) == "there was no land of Adrift to blight"
