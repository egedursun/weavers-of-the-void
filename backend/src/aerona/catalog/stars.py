from dataclasses import dataclass

from aerona.domain.enums.world import StarType

S = StarType


@dataclass(frozen=True)
class StarTypeSpec:
    star_type: StarType
    label: str
    description: str
    remnant: StarType = StarType.STAR_REMNANT


STAR_TYPES: dict[StarType, StarTypeSpec] = {
    spec.star_type: spec
    for spec in (
        StarTypeSpec(S.YELLOW_DWARF, "Yellow dwarf", "A steady yellow sun of middling size, the kind most life is born under."),
        StarTypeSpec(
            S.BLUE_STAR,
            "Blue star",
            "A huge, young blue-hot sun (O class) that burns fiercely and dies early, scorching its near worlds with hard light.",
            S.NEUTRON_STAR,
        ),
        StarTypeSpec(S.BLUE_WHITE_STAR, "Blue-white star", "A hot blue-white sun (B class), bright and short-lived.", S.NEUTRON_STAR),
        StarTypeSpec(S.WHITE_STAR, "White star", "A white sun (A class), hotter and brighter than a yellow dwarf."),
        StarTypeSpec(S.YELLOW_WHITE_STAR, "Yellow-white star", "A yellow-white sun (F class), a little warmer than a yellow dwarf."),
        StarTypeSpec(S.ORANGE_DWARF, "Orange dwarf", "A calm orange sun (K class) that burns long and gently; its worlds keep steady climates."),
        StarTypeSpec(S.RED_DWARF, "Red dwarf", "A small, dim red ember (M class) that lives almost for ever but flares often."),
        StarTypeSpec(S.BROWN_DWARF, "Brown dwarf", "A failed star, too small to burn true: a faint, warm dusk in the sky."),
        StarTypeSpec(S.YELLOW_GIANT, "Yellow giant", "A swollen yellow sun past its prime, wide and bright."),
        StarTypeSpec(S.RED_GIANT, "Red giant", "An old sun bloated to enormous size, red and cooling, its inner worlds in its reach.", S.WHITE_DWARF),
        StarTypeSpec(S.BLUE_GIANT, "Blue giant", "A great blue sun, blinding and unstable.", S.NEUTRON_STAR),
        StarTypeSpec(
            S.RED_SUPERGIANT,
            "Red supergiant",
            "A vast dying red sun, so large it would swallow whole orbits; it will end in a supernova.",
            S.NEUTRON_STAR,
        ),
        StarTypeSpec(S.BLUE_SUPERGIANT, "Blue supergiant", "One of the brightest suns there is, burning through its life in a blaze.", S.BLACK_HOLE),
        StarTypeSpec(S.HYPERGIANT, "Hypergiant", "A monstrous sun shedding its own body in storms; it trembles on the edge of collapse.", S.BLACK_HOLE),
        StarTypeSpec(S.WOLF_RAYET, "Wolf-Rayet star", "A stripped, searing sun blowing ferocious winds into the void; its death is near.", S.BLACK_HOLE),
        StarTypeSpec(S.PROTOSTAR, "Protostar", "A sun still being born inside its cocoon of dust, flickering and unsteady."),
        StarTypeSpec(S.CARBON_STAR, "Carbon star", "A deep-red old sun wrapped in soot, its light thick and smoky.", S.WHITE_DWARF),
        StarTypeSpec(S.WHITE_DWARF, "White dwarf", "The small, hot ashen core of a dead sun, cooling slowly."),
        StarTypeSpec(S.BINARY, "Binary star", "Two suns circling each other; double shadows and frequent eclipses."),
        StarTypeSpec(S.TRINARY, "Triple star", "Three suns in a tangled dance; eclipses are common and the seasons restless."),
        StarTypeSpec(S.VARIABLE_STAR, "Variable star", "A sun that swells and dims in long breaths, dragging its worlds' climates with it.", S.NEUTRON_STAR),
        StarTypeSpec(S.NEUTRON_STAR, "Neutron star", "The crushed core of an exploded sun: tiny, dim and deadly with radiation."),
        StarTypeSpec(S.PULSAR, "Pulsar", "A spinning dead core that sweeps the void with beams of radiation like a lighthouse."),
        StarTypeSpec(S.MAGNETAR, "Magnetar", "A dead core with a monstrous magnetic field; its starquakes tear at minds and ships."),
        StarTypeSpec(S.BLACK_HOLE, "Black hole", "A collapsed sun whose pull nothing escapes, ringed by a burning disc of what it devours."),
        StarTypeSpec(S.DEAD_STAR, "Dead star", "A sun that has gone out: a cold cinder in the dark."),
        StarTypeSpec(S.BLACK_SUN, "Black sun", "A sun that gives no light but swallows it; the things outside love it."),
        StarTypeSpec(S.BROKEN_STAR, "Broken star", "A sun cracked open, bleeding light through its wounds."),
        StarTypeSpec(S.STAR_REMNANT, "Star remnant", "The glowing shell and ember left behind by an exploded sun."),
        StarTypeSpec(S.REBORN_STAR, "Reborn star", "A sun that died and was kindled again; its light is young."),
        StarTypeSpec(S.CHAINED_STAR, "Chained star", "A sun bound in ancient chains of sigils; whatever is imprisoned in it holds the outside at bay."),
        StarTypeSpec(S.WATCHING_STAR, "Watching star", "A sun with an eye: it looks back at those who look at it."),
    )
}

STAR_TYPE_LABELS: dict[StarType, str] = {star_type: spec.label for star_type, spec in STAR_TYPES.items()}
