import re
from pathlib import Path

from aerona.catalog.canonical import RETIRED
from aerona.catalog.dominion import ALIGNMENT_LOOKS
from aerona.catalog.peoples import STYLE_AXES, VALUE_STYLE, Style
from aerona.db.tables.demography import PeopleCultureRow
from aerona.db.tables.structures import StructureProfileRow
from aerona.domain.enums import demography
from aerona.domain.enums.culture import ArtMode
from aerona.domain.enums.dominion import PerceivedAlignment
from aerona.domain.enums.mind import ValueAxis
from aerona.domain.enums.structure import StructureKind
from aerona.engine.cycles.legacy import keep_style, style_key
from aerona.engine.demography.peoples import style_columns
from aerona.engine.dominion.worship import lean_style
from aerona.engine.lore.style import style_fit
from aerona.engine.structures.construction import style_splendour
from aerona.engine.structures.profiles import kept_style, style_snapshot
from aerona.rules.registry import Rules

RULES = Rules()
VERSIONS = Path(__file__).resolve().parents[2] / "src" / "aerona" / "db" / "alembic" / "versions"
FAMILY_LEAD = {
    "austere": ValueAxis.MARTIAL,
    "ornate": ValueAxis.WEALTH,
    "geometric": ValueAxis.KNOWLEDGE,
    "natural": ValueAxis.NATURE,
    "macabre": ValueAxis.DEATH,
    "celestial": ValueAxis.PIETY,
}
MAPPED = re.compile(
    r"UPDATE people_culture SET ornament = (\d+), geometry = (\d+), colour = (\d+), scale = (\d+), symmetry = (\d+) WHERE .*?aesthetic = '(\w+)'"
)


def test_the_aesthetic_family_is_retired_for_good() -> None:
    assert not hasattr(demography, "Aesthetic")
    assert "Aesthetic" in RETIRED["aesthetics"]
    assert "aesthetic" not in PeopleCultureRow.__table__.columns
    assert "aesthetic" not in StructureProfileRow.__table__.columns


def test_every_old_family_maps_to_the_axes_its_leading_value_now_gives() -> None:
    (migration,) = VERSIONS.glob("*_w48_ways_of_life.py")
    mapped = {name: Style(*(int(value) for value in axes)) for *axes, name in MAPPED.findall(migration.read_text(encoding="utf-8"))}
    assert set(mapped) == set(FAMILY_LEAD)
    assert all(mapped[name] == VALUE_STYLE[lead] for name, lead in FAMILY_LEAD.items())


def test_a_people_s_leading_value_sets_its_base_style() -> None:
    assert style_columns({ValueAxis.WEALTH: 30}) == {
        axis: getattr(VALUE_STYLE[ValueAxis.WEALTH], axis) + (7 if axis == "ornament" else 0) for axis in STYLE_AXES
    }


def test_art_fit_keeps_its_behaviour_on_the_axes() -> None:
    assert style_fit(RULES, VALUE_STYLE[ValueAxis.WEALTH], ArtMode.FLAT_IMAGE) == RULES.customs.aesthetic_fit_pct / 100
    assert style_fit(RULES, VALUE_STYLE[ValueAxis.NATURE], ArtMode.MOVEMENT) == RULES.customs.aesthetic_fit_pct / 100
    assert style_fit(RULES, VALUE_STYLE[ValueAxis.MARTIAL], ArtMode.FLAT_IMAGE) == RULES.customs.aesthetic_clash_pct / 100
    assert style_fit(RULES, None, ArtMode.FLAT_IMAGE) == 1.0


def test_a_work_built_in_its_onlookers_style_gains_splendour_and_a_foreign_one_loses_it() -> None:
    table = RULES.construction
    rich, plain = VALUE_STYLE[ValueAxis.WEALTH], VALUE_STYLE[ValueAxis.MARTIAL]
    assert style_splendour(RULES, rich, rich) == table.aesthetic_fit
    assert style_splendour(RULES, rich, plain) == -table.aesthetic_clash
    assert style_splendour(RULES, None, rich) == 0


def profile(locked: list[str] | None = None, **values: object) -> StructureProfileRow:
    return StructureProfileRow(structure_entity_id=1, kind=StructureKind.TEMPLE, locked=locked or [], **values)


def test_a_work_keeps_the_style_of_its_builders() -> None:
    rich = VALUE_STYLE[ValueAxis.WEALTH]
    work = profile(**style_snapshot(rich))
    assert kept_style(work) == rich
    assert kept_style(profile(**style_snapshot(None))) is None


def test_a_temple_leans_toward_the_look_its_people_give_its_god_and_holds_what_is_held() -> None:
    look = ALIGNMENT_LOOKS[PerceivedAlignment.MALEVOLENT]
    work = profile(**style_snapshot(VALUE_STYLE[ValueAxis.WEALTH]), locked=["style_scale"])
    lean_style(work, look, 50)
    assert work.style_ornament == 75
    assert work.style_scale == VALUE_STYLE[ValueAxis.WEALTH].scale
    bare = profile(**style_snapshot(None))
    lean_style(bare, look, 50)
    assert kept_style(bare) == look


def test_a_kept_style_carries_every_axis_and_honours_holds() -> None:
    source = PeopleCultureRow(people_entity_id=1, ornament=90, geometry=50, colour=80, scale=60, symmetry=60, locked=[])
    heir = PeopleCultureRow(people_entity_id=2, ornament=10, geometry=10, colour=10, scale=10, symmetry=10, locked=["colour"])
    keep_style(heir, style_key(source))
    assert (heir.ornament, heir.geometry, heir.colour, heir.scale, heir.symmetry) == (90, 50, 10, 60, 60)
