from sqlalchemy import delete

from aerona.catalog.anatomy import ANATOMIES
from aerona.catalog.tissues import FULL_COUNTS, digit_keys, digits_phrase, intact_share
from aerona.core.random import RandomKey, SeededRandom
from aerona.db.tables.body import BodyRow
from aerona.db.tables.cosmos import AppliedFixupRow
from aerona.domain.enums.body import BodyPlan, Handedness, HarmCause, InjuryKind
from aerona.engine.body.book import ensure_body
from aerona.engine.body.capacities import BearerStats, BodyState, capacities
from aerona.engine.body.digits import DIGITS_FIXUP, backfill_digits, effective_counts, lose, restore
from aerona.engine.body.healing import mend
from aerona.engine.body.hits import Harm
from aerona.engine.lifecycle.wounds import apply_hits
from aerona.rules.registry import Rules
from tests.engine.society.factories import Realm, context, mortal

RULES = Rules()
HUMAN = ANATOMIES[BodyPlan.HUMANOID]
STATS = BearerStats(50, 50, 50, 50, 50)


def test_a_lost_thumb_weighs_more_than_a_little_finger_and_names_read_well() -> None:
    assert intact_share("fingers", ["left_hand.thumb"]) < intact_share("fingers", ["left_hand.little"])
    assert digits_phrase(["left_hand.index", "left_hand.middle"]) == "index and middle fingers of the left hand"
    assert digits_phrase(["right_hand.thumb"]) == "thumb of the right hand"
    assert len(digit_keys("fingers")) == FULL_COUNTS["fingers"] and len(digit_keys("toes")) == FULL_COUNTS["toes"]


def test_the_leading_hand_decides_whose_grip_a_lost_thumb_spoils() -> None:
    whole = capacities(RULES, STATS, BodyState(HUMAN, (), FULL_COUNTS, 0))
    lost = ("right_hand.thumb", "right_hand.index")
    righty = capacities(RULES, STATS, BodyState(HUMAN, (), FULL_COUNTS, 0, lost_digits=lost, handedness=Handedness.RIGHT))
    lefty = capacities(RULES, STATS, BodyState(HUMAN, (), FULL_COUNTS, 0, lost_digits=lost, handedness=Handedness.LEFT))
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
    assert body.fingers == FULL_COUNTS["fingers"] - len(row.digits)
    assert effective_counts(body)["fingers"] < FULL_COUNTS["fingers"]
    await mend(ctx, bearer, lasting=True)
    assert body.lost_digits == [] and body.fingers == FULL_COUNTS["fingers"]


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
