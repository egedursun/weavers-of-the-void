import re
from pathlib import Path

from aerona.catalog.terrain import TACTIC_TERRAIN, TERRAIN, terrain_has, terrains
from aerona.domain.enums.environment import MovementMode, TerrainKind, TerrainTrait
from aerona.domain.enums.military import Tactic
from aerona.rules.registry import Rules

SOURCE = Path(__file__).resolve().parents[2] / "src" / "aerona"
CATALOGUE = SOURCE / "catalog" / "terrain.py"


def readers_of(trait: TerrainTrait) -> list[Path]:
    pattern = re.compile(rf"TerrainTrait\.{trait.name}\b")
    return [path for path in SOURCE.rglob("*.py") if path != CATALOGUE and pattern.search(path.read_text(encoding="utf-8"))]


def test_every_terrain_kind_has_traits_and_a_passage() -> None:
    rules = Rules()
    for kind, spec in TERRAIN.items():
        assert spec.traits, kind
        assert set(spec.passage(rules)) == set(MovementMode)
        assert spec.width > 0


def test_every_trait_has_a_reader() -> None:
    assert [trait for trait in TerrainTrait if not readers_of(trait)] == []


def test_trait_queries_keep_the_old_memberships() -> None:
    assert terrains(TerrainTrait.AMBUSH_COVER) == {
        TerrainKind.FOREST,
        TerrainKind.JUNGLE,
        TerrainKind.MARSH,
        TerrainKind.CANYON,
        TerrainKind.RUIN_FIELD,
        TerrainKind.MANGROVE,
        TerrainKind.SCRUBLAND,
        TerrainKind.TAIGA,
    }
    assert terrains(TerrainTrait.ROUGH) == {
        TerrainKind.HILLS,
        TerrainKind.MOUNTAINS,
        TerrainKind.HIGH_PASS,
        TerrainKind.CANYON,
        TerrainKind.BADLANDS,
        TerrainKind.KARST,
        TerrainKind.REGOLITH_PLAIN,
    }
    assert terrains(every=(TerrainTrait.HIGH, TerrainTrait.COLD)) == {TerrainKind.MOUNTAINS, TerrainKind.HIGH_PASS}
    assert terrains(TerrainTrait.COLD, without=(TerrainTrait.OPEN,)) == {TerrainKind.MOUNTAINS, TerrainKind.HIGH_PASS, TerrainKind.ICE_SHEET, TerrainKind.TAIGA}
    assert terrain_has(TerrainKind.MARSH, TerrainTrait.WET) and not terrain_has(None, TerrainTrait.WET)
    assert TACTIC_TERRAIN[Tactic.RIVER_DEFENCE] == {TerrainKind.RIVER_VALLEY, TerrainKind.FLOODPLAIN}
    assert Tactic.HOLD_LINE not in TACTIC_TERRAIN
