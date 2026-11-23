from sqlalchemy import select

from aerona.catalog.kinds.harm import HARM_CAUSES, HARM_DEATHS
from aerona.db.tables.interconnect import IncidentRow
from aerona.domain.enums.body import HarmCause
from aerona.domain.enums.mortal import DeathCause
from aerona.engine.body.hits import Harm
from aerona.engine.lifecycle.wounds import apply_hits
from tests.engine.society.factories import Realm, context, mortal


def test_the_three_new_causes_lead_to_their_deaths() -> None:
    assert set(HARM_CAUSES) == set(HarmCause) and {HarmCause.CHILDBIRTH, HarmCause.CRIME, HarmCause.SPORT} <= set(HarmCause)
    assert HARM_DEATHS[HarmCause.CHILDBIRTH] is DeathCause.CHILDBIRTH
    assert HARM_DEATHS[HarmCause.CRIME] is DeathCause.MURDER
    assert all(HARM_CAUSES[cause].noted for cause in (HarmCause.CHILDBIRTH, HarmCause.CRIME, HarmCause.SPORT))


async def test_harm_by_a_new_cause_is_told_with_its_cause(realm: Realm) -> None:
    victim = await mortal(realm, "Ivo")
    await apply_hits(context(realm.session), victim, Harm(30, HarmCause.CRIME, "stabbed in an alley"), lethal=False)
    await realm.session.flush()
    assert "body.harmed" in set(await realm.session.scalars(select(IncidentRow.kind)))
