import pathlib
import re

from aerona.catalog.collective import FORMATIVE_SHIFTS
from aerona.catalog.genetics import APTITUDE_LOCI, LOCI, TEMPERAMENT_LOCI
from aerona.catalog.life.kin import AVENGING, KIN_ROLES, RAISE_ORDER
from aerona.db.tables.genetics import GenomeRow
from aerona.domain.enums.collective import FormativeKind
from aerona.domain.enums.genetics import Locus
from aerona.domain.enums.kin import KinRole
from aerona.engine.genetics.life import aptitude_pace, twinning_chance
from aerona.rules.registry import Rules

RULES = Rules()
ENUMS = pathlib.Path(__file__).resolve().parents[3] / "src" / "aerona" / "domain" / "enums"


def test_no_enum_value_names_a_line_by_sex() -> None:
    sexed = re.compile(r'"(?:matri|patri)(?:lineal|local|archal)[a-z_]*"')
    found = [path.name for path in ENUMS.glob("*.py") if sexed.search(path.read_text())]
    assert found == []


def test_twinning_runs_in_lines_that_carry_it() -> None:
    carrier = GenomeRow(genes={Locus.TWINNING.value: ["twinning", "twinning"]})
    plain = GenomeRow(genes={Locus.TWINNING.value: ["common", "common"]})
    assert twinning_chance(RULES, 2.0, [carrier, plain]) == 2.0 + RULES.genetics.twinning_pct
    assert twinning_chance(RULES, 2.0, [plain, None]) == 2.0
    assert Locus.TWINNING in LOCI


def test_aptitude_speeds_upbringing_and_temperament_loci_are_known() -> None:
    keen = {locus.value: ["high", "high"] for locus in APTITUDE_LOCI}
    dull = {locus.value: ["low", "low"] for locus in APTITUDE_LOCI}
    assert min(aptitude_pace(RULES, keen).values()) > 1 > max(aptitude_pace(RULES, dull).values())
    assert len(TEMPERAMENT_LOCI) == 5


def test_foster_kin_has_duties_and_a_long_season_marks_a_generation() -> None:
    assert len(KIN_ROLES) == 18 and KinRole.FOSTER_KIN in AVENGING and RAISE_ORDER[-1] is KinRole.FOSTER_KIN
    assert FORMATIVE_SHIFTS[FormativeKind.LONG_SEASON]
