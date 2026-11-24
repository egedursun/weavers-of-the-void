from collections.abc import Mapping
from dataclasses import dataclass

from aerona.core.total import total
from aerona.domain.enums.body import BodyPlan
from aerona.domain.enums.environment import MovementMode, TerrainTrait
from aerona.domain.enums.world_view import SettleMode

P = BodyPlan
T = TerrainTrait


@dataclass(frozen=True)
class SettleSpec:
    label: str
    grounded: bool
    needs: MovementMode | None = None
    terrains: frozenset[TerrainTrait] = frozenset()
    shuns: frozenset[TerrainTrait] = frozenset()
    natural: frozenset[BodyPlan] = frozenset()
    forest: bool = False


SETTLE_MODES: Mapping[SettleMode, SettleSpec] = total(
    SettleMode,
    {
        SettleMode.GROUND: SettleSpec("On the ground", grounded=True),
        SettleMode.FLOATING: SettleSpec("Floating", grounded=False),
        SettleMode.STILT: SettleSpec("On stilts", grounded=True, terrains=frozenset({T.WET, T.WATERY, T.COASTAL})),
        SettleMode.OASIS: SettleSpec("At oases", grounded=True, terrains=frozenset({T.ARID})),
        SettleMode.VENT: SettleSpec("Around warm vents", grounded=True),
        SettleMode.HABITAT: SettleSpec("In sealed habitats", grounded=True),
        SettleMode.BAND: SettleSpec("In a habitable band", grounded=True),
        SettleMode.DECK: SettleSpec("On decks", grounded=False),
        SettleMode.BURROW: SettleSpec(
            "In burrows", grounded=True, needs=MovementMode.BURROWING, shuns=frozenset({T.WATERY}), natural=frozenset({P.INSECTOID, P.AMORPHOUS})
        ),
        SettleMode.SUBMERGED: SettleSpec(
            "Beneath the water",
            grounded=False,
            needs=MovementMode.SUBMERGED,
            terrains=frozenset({T.WATERY, T.COASTAL, T.WET}),
            natural=frozenset({P.AQUATIC, P.TENTACLED, P.RADIAL, P.COLONIAL}),
        ),
        SettleMode.CANOPY: SettleSpec(
            "In the canopy", grounded=True, needs=MovementMode.CLIMBING, terrains=frozenset({T.WOODED}), natural=frozenset({P.ARBOREAL}), forest=True
        ),
        SettleMode.CLIFF: SettleSpec("On cliffs", grounded=True, terrains=frozenset({T.HIGH, T.ROUGH, T.COASTAL})),
        SettleMode.DRIFT: SettleSpec("On drift", grounded=False, terrains=frozenset({T.WATERY})),
    },
)
PREFERRED = (SettleMode.SUBMERGED, SettleMode.BURROW, SettleMode.CANOPY)
