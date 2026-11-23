import re
from pathlib import Path

from aerona.catalog.reproduction import ROLE_WEIGHTS, SEX_KINDS, SEX_SYSTEMS, kind_of_sex, sex_rule_fit, sex_shares
from aerona.core.random import RandomKey, SeededRandom
from aerona.db.tables.mortal import MarriageRow
from aerona.domain.enums import demography
from aerona.domain.enums.collective import RoleEligibility
from aerona.domain.enums.cycles import ReproductiveSystem
from aerona.domain.enums.demography import SexKind
from aerona.domain.enums.entity import EntityStatus
from aerona.domain.enums.mortal import MarriageEnd
from aerona.domain.enums.polity import SexRule
from aerona.engine.collective.demography import bereaved_among
from aerona.engine.cycles.breeding import born_sex
from aerona.engine.mortal.life import window_end_pct
from aerona.rules.registry import Rules
from tests.engine.society.factories import Realm, mortal, settlement

RULES = Rules()
SOURCE = Path(__file__).resolve().parents[3] / "src" / "aerona"
FIXED = re.compile(r"\b(?:female|male|women|men|widows)\b", re.IGNORECASE)


def test_no_module_names_a_fixed_sex_and_the_old_enum_is_gone() -> None:
    assert not hasattr(demography, "Sex")
    offenders = []
    for path in SOURCE.rglob("*.py"):
        relative = path.relative_to(SOURCE).as_posix()
        if relative.startswith("db/alembic/") or "__pycache__" in relative:
            continue
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if FIXED.search(line) and "re.compile(" not in line:
                offenders.append(f"{relative}:{number}")
    assert offenders == []
    assert not any(FIXED.search(value) for value in (*(item.value for item in RoleEligibility), *(item.value for item in SexRule)))


def test_births_follow_the_biology_and_every_sex_kind_has_its_role() -> None:
    assert set(SEX_KINDS) == set(SexKind)
    assert SEX_SYSTEMS[ReproductiveSystem.ASEXUAL].bearing == {SexKind.NONE}
    assert SEX_SYSTEMS[ReproductiveSystem.AMBISEXUAL].bearing == {SexKind.BOTH}
    assert SEX_SYSTEMS[ReproductiveSystem.TWO_SEX].bearing == {SexKind.BEARER}
    rng = SeededRandom(RandomKey(1, 0, "born"))
    assert born_sex(RULES, ReproductiveSystem.ASEXUAL, rng) is SexKind.NONE
    assert born_sex(RULES, ReproductiveSystem.AMBISEXUAL, rng) is SexKind.BOTH
    assert born_sex(RULES, ReproductiveSystem.TWO_SEX, rng) in {SexKind.BEARER, SexKind.BEGETTER}
    assert sex_shares(SEX_SYSTEMS[ReproductiveSystem.ASEXUAL], RULES.cohorts.bearer_pct) == {SexKind.NONE: 1.0}
    assert window_end_pct(RULES, SexKind.NEITHER) == 0 < window_end_pct(RULES, SexKind.NONE)


def test_roles_bind_by_reproductive_role_and_never_bar_a_people_without_sexes() -> None:
    assert ROLE_WEIGHTS[RoleEligibility.BEARERS_ONLY][SexKind.BOTH] == ROLE_WEIGHTS[RoleEligibility.ANY][SexKind.BOTH]
    assert ROLE_WEIGHTS[RoleEligibility.BEARERS_ONLY][SexKind.BEGETTER] < ROLE_WEIGHTS[RoleEligibility.BEARERS_PREFERRED][SexKind.BEGETTER]
    assert ROLE_WEIGHTS[RoleEligibility.BEGETTERS_ONLY][SexKind.NONE] == ROLE_WEIGHTS[RoleEligibility.ANY][SexKind.NONE]
    assert sex_rule_fit(SexRule.BEGETTERS_ONLY, SexKind.BEARER) is None
    assert sex_rule_fit(SexRule.BEARER_PREFERENCE, SexKind.BEGETTER) == 0.5
    assert kind_of_sex("unknown") is SexKind.NONE and kind_of_sex("bearer") is SexKind.BEARER


async def test_bereaved_partners_are_counted_from_unions_ended_by_death(realm: Realm) -> None:
    town = await settlement(realm, "Weir", population=2000)
    living = await mortal(realm, "Ala", location_id=town.id)
    dead = await mortal(realm, "Bem", location_id=town.id)
    remarried = await mortal(realm, "Cor", location_id=town.id)
    again = await mortal(realm, "Dun", location_id=town.id)
    dead.status, dead.end_epoch = EntityStatus.DEAD, 2
    realm.session.add_all(
        [
            MarriageRow(first_id=living.id, second_id=dead.id, start_epoch=1, end_epoch=2, cause_end=MarriageEnd.DEATH),
            MarriageRow(first_id=remarried.id, second_id=dead.id, start_epoch=1, end_epoch=2, cause_end=MarriageEnd.DEATH),
            MarriageRow(first_id=remarried.id, second_id=again.id, start_epoch=2),
        ]
    )
    await realm.session.flush()
    assert await bereaved_among(realm.session, town.id) == 1
