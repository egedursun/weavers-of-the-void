from sqlalchemy import delete

from aerona.catalog.anatomy import ANATOMIES
from aerona.catalog.tissues import DIGIT_LIMBS, digit_keys, digits_phrase, intact_share
from aerona.core.random import RandomKey, SeededRandom
from aerona.db.tables.body import BodyRow
from aerona.db.tables.cosmos import AppliedFixupRow
from aerona.domain.enums.body import BodyPlan, Handedness, HarmCause, InjuryKind
from aerona.domain.enums.entity import EntityType
from aerona.domain.models.entity_stats import SpeciesStats
from aerona.engine.body.book import ensure_body, ensure_species_body
from aerona.engine.body.capacities import BearerStats, BodyState, capacities
from aerona.engine.body.digits import DIGITS_FIXUP, backfill_digits, effective_counts, lose, replan, restore
from aerona.engine.body.healing import mend
from aerona.engine.body.hits import Harm
from aerona.engine.lifecycle.wounds import apply_hits
from aerona.rules.registry import Rules
from tests.engine.society.factories import Realm, context, make, mortal

RULES = Rules()
HUMAN = ANATOMIES[BodyPlan.HUMANOID]
FULL = HUMAN.full_counts
STATS = BearerStats(50, 50, 50, 50, 50)


def test_a_lost_thumb_weighs_more_than_a_little_finger_and_names_read_well() -> None:
    assert intact_share("fingers", ["left_hand.thumb"]) < intact_share("fingers", ["left_hand.little"])
    assert digits_phrase(["left_hand.index", "left_hand.middle"]) == "index and middle fingers of the left hand"
    assert digits_phrase(["right_hand.thumb"]) == "thumb of the right hand"
    assert len(digit_keys("fingers")) == FULL["fingers"] and len(digit_keys("toes")) == FULL["toes"]


def test_the_leading_hand_decides_whose_grip_a_lost_thumb_spoils() -> None:
    whole = capacities(RULES, STATS, BodyState(HUMAN, (), FULL, 0))
    lost = ("right_hand.thumb", "right_hand.index")
    righty = capacities(RULES, STATS, BodyState(HUMAN, (), FULL, 0, lost_digits=lost, handedness=Handedness.RIGHT))
    lefty = capacities(RULES, STATS, BodyState(HUMAN, (), FULL, 0, lost_digits=lost, handedness=Handedness.LEFT))
    assert righty["melee"] < whole["melee"]
    assert lefty["melee"] == whole["melee"]


async def test_a_severing_blow_takes_named_digits_and_lasting_healing_returns_them(realm: Realm) -> None:
    ctx = context(realm.session)
    bearer = await mortal(realm, "Hesk")
    body = await ensure_body(realm.session, RULES, bearer, ctx.epoch)
    wounding = await apply_hits(ctx, bearer, Harm(30, HarmCause.PLAYER, "struck", part="fingers", kind=InjuryKind.SEVERED, severity=1), lethal=False)
    row = wounding.injuries[0]
    assert len(row.digits) == RULES.anatomy.fingers_per_severity
    assert set(row.digits) <= set(body.lost_digits)
    assert body.fingers == FULL["fingers"] - len(row.digits)
    assert effective_counts(body)["fingers"] < FULL["fingers"]
    await mend(ctx, bearer, lasting=True)
    assert body.lost_digits == [] and body.fingers == FULL["fingers"]


async def test_old_counts_become_named_digits_once(realm: Realm) -> None:
    bearer = await mortal(realm, "Orla")
    body = await ensure_body(realm.session, RULES, bearer, 1)
    body.fingers, body.toes, body.lost_digits = 7, 9, []
    await realm.session.execute(delete(AppliedFixupRow).where(AppliedFixupRow.key == DIGITS_FIXUP))
    assert await backfill_digits(realm.session, RULES) >= 1
    assert sum(1 for key in body.lost_digits if "_hand." in key) == 3
    assert sum(1 for key in body.lost_digits if "_foot." in key) == 1
    assert await backfill_digits(realm.session, RULES) == 0
    taken = lose(body, "fingers", 20, SeededRandom(RandomKey(1, 0, "all")))
    assert body.fingers == 0 and len(taken) == 7
    restore(body, "fingers", taken[:2])
    assert body.fingers == 2
    assert isinstance(await realm.session.get(BodyRow, bearer.id), BodyRow)


def test_every_plan_names_as_many_digits_as_it_counts() -> None:
    for anatomy in ANATOMIES.values():
        for part in DIGIT_LIMBS:
            assert anatomy.full_count(part) in (0, len(digit_keys(part))), (anatomy.plan, part)
    assert FULL == {"fingers": 10, "toes": 10, "teeth": 32}
    assert ANATOMIES[BodyPlan.AVIAN].full_counts == {"fingers": 0, "toes": 0, "teeth": 0}


async def test_a_non_humanoid_being_takes_its_plans_digits_and_teeth(realm: Realm) -> None:
    hound = await make(realm.session, "Grey Hound Kin", EntityType.SPECIES, SpeciesStats(), world_id=realm.world.id)
    body = await ensure_species_body(realm.session, hound, BodyPlan.QUADRUPED)
    assert (body.fingers, body.toes, body.teeth) == (0, 0, ANATOMIES[BodyPlan.QUADRUPED].full_count("teeth"))
    assert body.teeth != FULL["teeth"] and effective_counts(body)["fingers"] == 0
    bearer = await mortal(realm, "Vey")
    kin = await ensure_body(realm.session, RULES, bearer, 1)
    lose(kin, "fingers", 2, SeededRandom(RandomKey(bearer.id, 0, "test")))
    kin.teeth -= 3
    replan(kin, BodyPlan.AVIAN)
    assert (kin.fingers, kin.toes, kin.teeth) == (0, 0, 0)
    replan(kin, BodyPlan.QUADRUPED)
    assert kin.teeth == ANATOMIES[BodyPlan.QUADRUPED].full_count("teeth")
    replan(kin, BodyPlan.HUMANOID)
    assert (kin.fingers, kin.toes, kin.teeth) == (FULL["fingers"] - 2, FULL["toes"], FULL["teeth"])
