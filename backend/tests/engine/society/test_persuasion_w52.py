from aerona.catalog.relations import APPEALS, INTERACTIONS, NOTABLE_INTERACTIONS, TUNING
from aerona.db.tables.relations import RelationshipRow
from aerona.domain.enums.relations import AppealKind, InteractionKind, PersuasionAim, RelationType
from aerona.engine.relations.interactions import apologise, load_scene
from aerona.engine.relations.persuasion import already_won, bond_pull, persuade
from aerona.rules.registry import Rules
from tests.engine.society.factories import Realm, context, mortal, tuned

RULES = Rules()


def held_bond(holder: int, subject: int, friendship: int, kinds: list[str] | None = None) -> RelationshipRow:
    return RelationshipRow(
        holder_node_id=holder,
        subject_node_id=subject,
        friendship=friendship,
        romance=0,
        familiarity=40,
        rivalry=10,
        kinds=kinds or [],
        since_epoch=1,
        last_epoch=1,
        locked=[],
    )


def test_every_interaction_and_appeal_has_its_spec_and_tuning() -> None:
    assert set(INTERACTIONS) == set(TUNING) == set(InteractionKind)
    assert len(InteractionKind) == 24 and len(APPEALS) == len(AppealKind) == 7 and len(PersuasionAim) == 7
    assert {InteractionKind.APOLOGISE, InteractionKind.SHARE_MEAL, InteractionKind.ASK_COUNSEL} <= NOTABLE_INTERACTIONS
    assert all(0 <= tuning.weight(RULES) <= 100 and 0 <= tuning.effect(RULES) <= 100 for tuning in TUNING.values())


async def test_an_apology_softens_the_grievance(realm: Realm) -> None:
    sorry, hurt = await mortal(realm, "Sorry"), await mortal(realm, "Hurt")
    grudge = held_bond(hurt.id, sorry.id, -40)
    realm.session.add(grudge)
    await realm.session.flush()
    scene = await load_scene(context(realm.session), realm.region.id, [sorry, hurt])
    await apologise(scene, sorry.id, hurt.id)
    assert grudge.friendship > -40


async def test_a_bond_appeal_fails_without_a_bond_and_carries_with_one(realm: Realm) -> None:
    speaker, stranger, kin = await mortal(realm, "Speaker"), await mortal(realm, "Stranger"), await mortal(realm, "Kin")
    realm.session.add(held_bond(kin.id, speaker.id, 50, [RelationType.SWORN_KIN.value]))
    await realm.session.flush()
    assert await bond_pull(realm.session, speaker.id, stranger.id) < 0
    assert await bond_pull(realm.session, speaker.id, kin.id) > 0


async def test_a_won_surrender_is_remembered_for_the_siege(realm: Realm) -> None:
    envoy, ruler = await mortal(realm, "Envoy"), await mortal(realm, "Ruler")
    easy = tuned(persuasion={"threshold": 0, "jitter": 0})
    argument = await persuade(context(realm.session, easy), envoy.id, ruler.id, AppealKind.FEELING, PersuasionAim.SURRENDER, subject_id=realm.region.id)
    assert argument.success
    won = await already_won(realm.session, PersuasionAim.SURRENDER, target_id=None, subject_id=realm.region.id, since=0)
    assert won is not None and won.appeal is AppealKind.FEELING
