import importlib.util
import re
from pathlib import Path

from aerona.catalog.beast_tempers import HELD_TEMPERS
from aerona.catalog.life_traits import PACKAGE_KIND_TRAITS, having
from aerona.db.tables.collective import CrowdMoodRow
from aerona.db.tables.demography import CohortRow
from aerona.db.tables.disease import DiseaseProfileRow
from aerona.db.tables.evolution import WorldCycleRow
from aerona.domain.enums.ecology import AnimalRole
from aerona.domain.enums.life_traits import PackageKindTrait
from aerona.engine.ecology.pets import HUNTING_USES
from aerona.engine.environment.dangers import HELD_BEASTS
from aerona.engine.intrigue.sources import CURSED_PACKAGES

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / "backend" / "src" / "aerona"
HOOK = ROOT / ".githooks" / "pre-commit"
KEPT_OUT = ("alembic", "renames.py", "__pycache__")


def code() -> dict[Path, str]:
    return {path: path.read_text(encoding="utf-8") for path in SOURCE.rglob("*.py") if not any(part in str(path) for part in KEPT_OUT)}


def holders(pattern: str) -> list[str]:
    found = re.compile(pattern)
    return sorted(str(path.relative_to(SOURCE)) for path, text in code().items() if found.search(text))


def enum_values(name: str) -> set[str]:
    values: set[str] = set()
    for path in (SOURCE / "domain" / "enums").rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        if match := re.search(rf"^class {name}\(StrEnum\):\n((?:    .+\n)+)", text, flags=re.MULTILINE):
            values |= set(re.findall(r'= "(\w+)"', match.group(1)))
    return values


def test_the_guards_of_the_defects_run_in_the_gate() -> None:
    hook = HOOK.read_text(encoding="utf-8")
    guards = (
        "check_season_positions",
        "check_literal_enum_sets",
        "check_calendar_slots",
        "check_movement_modes",
        "check_canned_lines",
        "check_cycle_fields",
        "check_spec_duplicates",
        "check_prompt_bias",
    )
    assert [guard for guard in guards if guard not in hook] == []
    found = importlib.util.spec_from_file_location("check_literal_enum_sets", ROOT / "scripts" / "check_literal_enum_sets.py")
    assert found is not None and found.loader is not None
    families = importlib.util.module_from_spec(found)
    found.loader.exec_module(families)
    assert {family.name for family in families.FAMILIES} == {"weather", "terrain", "movement", "deep", "catch", "species", "body", "life", "goods"}


def test_d1_to_d4_seasons_weather_and_slots_live_in_one_place() -> None:
    assert holders(r"\bWEATHER_EFFECTS\b") == []
    assert holders(r"def slot_fits\b") == []
    assert holders(r"\bSEASON_SHAPES\b") == []


def test_d10_to_d12_modes_dangers_and_cycles_are_typed() -> None:
    assert holders(r"\bROAD_MODES\b|\bGROUND_MODES\b") == []
    assert holders(r"Strange lights|Strange phenomena") == []
    assert not {"carbon", "water", "nutrients", "carbon_in", "water_in"} & {column.name for column in WorldCycleRow.__table__.columns}


def test_d13_catch_families_come_from_the_catalogue() -> None:
    assert holders(r"\bFISH_GEAR\b|\bLAND_GEAR\b|\bMARKET_RANKS\b") == []


def test_d14_a_hunting_animal_is_read_from_the_hunting_role() -> None:
    assert {AnimalRole.HUNTING} == HUNTING_USES


def test_d15_held_beasts_are_one_catalogue() -> None:
    assert HELD_BEASTS == HELD_TEMPERS


def test_d16_to_d19_merged_taxonomies_and_two_climate_axes() -> None:
    assert not enum_values("LoreKind") and not enum_values("TeachingKind") and not enum_values("DiseaseVector")
    assert "dragonbone" not in enum_values("YieldProduct") | enum_values("MaterialKind")
    columns = {column.name for column in DiseaseProfileRow.__table__.columns}
    assert {"affinity_warmth", "affinity_moisture", "primary_route"} <= columns and "vector" not in columns


def test_d20_d21_reactions_and_families_are_read_from_catalogues() -> None:
    assert holders(r"\bGLORIOUS_DEATHS\b|\bSHAMEFUL_DEATHS\b") == []
    assert having(PACKAGE_KIND_TRAITS, PackageKindTrait.HIDDEN_BY_BEARER) == CURSED_PACKAGES


def test_d22_to_d26_no_sexed_cohorts_lines_martial_grades_fixed_feelings_or_mixed_goals() -> None:
    assert "sex" not in {column.name for column in CohortRow.__table__.columns}
    assert holders(r"\bwomen_study\b|\bwarriors_ready\b") == []
    assert "matrilineal" not in enum_values("SuccessionRule")
    assert "warriors" not in enum_values("AgeGrade")
    assert not {"anger", "anxiety", "fervour"} & {column.name for column in CrowdMoodRow.__table__.columns}
    assert "adopt_ways" not in enum_values("RevivalGoal") and "adopt" in enum_values("RevivalWay")


def test_d27_to_d29_goods_routes_and_union_payments() -> None:
    assert "caravan" not in enum_values("TradeMode") and not enum_values("RouteEnvironment")
    assert "dowry" not in enum_values("RegistryKind")


def test_d40_cultivation_keeps_the_held_methods() -> None:
    assert not {"grafting", "partnering"} & enum_values("CultivationMethod")


def test_the_closing_audit_renames_hold() -> None:
    renamed = {
        "FossilSource": ("dead_god", "god"),
        "DivinationKind": ("asking_the_dead", "spirit_consultation"),
        "DuelEnd": ("first_blood", "first_wound"),
        "RechargeRule": ("blood", "bodily_offering"),
        "TerrainTrait": ("uncanny_matter", "non_mineral_ground"),
        "CultivationMethod": ("grafting", "hybridising"),
    }
    assert [name for name, (old, new) in renamed.items() if old in enum_values(name) or new not in enum_values(name)] == []
    assert not {"saps", "batteries"} & enum_values("SiegeWork")
    assert not {"aptitude", "temperament", "sense_acuity", "breath_capacity", "pain_tolerance"} & enum_values("Locus")
