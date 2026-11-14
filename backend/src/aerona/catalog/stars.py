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
        StarTypeSpec(S.YELLOW_DWARF, "Yellow dwarf", "A steady yellow star of middling size (G class) with long, stable output."),
        StarTypeSpec(
            S.BLUE_STAR,
            "Blue star",
            "A huge, young, very hot blue star (O class) that burns fast and ends early; its near worlds take strong radiation.",
            S.NEUTRON_STAR,
        ),
        StarTypeSpec(S.BLUE_WHITE_STAR, "Blue-white star", "A hot blue-white star (B class), bright and short-lived.", S.NEUTRON_STAR),
        StarTypeSpec(S.WHITE_STAR, "White star", "A white star (A class), hotter and brighter than a yellow dwarf."),
        StarTypeSpec(S.YELLOW_WHITE_STAR, "Yellow-white star", "A yellow-white star (F class), a little warmer than a yellow dwarf."),
        StarTypeSpec(S.ORANGE_DWARF, "Orange dwarf", "An orange star (K class) with long, stable output; its worlds keep steady climates."),
        StarTypeSpec(S.RED_DWARF, "Red dwarf", "A small, dim red star (M class) that lives almost for ever but flares often."),
        StarTypeSpec(S.BROWN_DWARF, "Brown dwarf", "A body between a planet and a star, too small to sustain fusion; it gives faint warmth and little light."),
        StarTypeSpec(S.YELLOW_GIANT, "Yellow giant", "A large yellow star late in its life, wide and bright."),
        StarTypeSpec(S.RED_GIANT, "Red giant", "An old star expanded to enormous size, red and cooling; its inner worlds lie within its reach.", S.WHITE_DWARF),
        StarTypeSpec(S.BLUE_GIANT, "Blue giant", "A large blue star, very bright and unstable.", S.NEUTRON_STAR),
        StarTypeSpec(
            S.RED_SUPERGIANT,
            "Red supergiant",
            "A vast red star near its end, wider than whole orbits; it will end in a supernova.",
            S.NEUTRON_STAR,
        ),
        StarTypeSpec(S.BLUE_SUPERGIANT, "Blue supergiant", "One of the brightest kinds of star, using up its fuel quickly.", S.BLACK_HOLE),
        StarTypeSpec(S.HYPERGIANT, "Hypergiant", "An extremely massive star losing mass in strong outbursts; it is close to collapse.", S.BLACK_HOLE),
        StarTypeSpec(S.WOLF_RAYET, "Wolf-Rayet star", "A very hot star that has lost its outer layers and drives strong winds; its end is near.", S.BLACK_HOLE),
        StarTypeSpec(S.PROTOSTAR, "Protostar", "A star still forming inside a cloud of gas and dust, with unsteady output."),
        StarTypeSpec(S.CARBON_STAR, "Carbon star", "An old deep-red star rich in carbon, wrapped in dust that dims its light.", S.WHITE_DWARF),
        StarTypeSpec(S.WHITE_DWARF, "White dwarf", "The small, hot core left by a star that has ended, cooling slowly."),
        StarTypeSpec(S.BINARY, "Binary star", "Two stars orbiting each other; their worlds see two lights and frequent eclipses."),
        StarTypeSpec(S.TRINARY, "Triple star", "Three stars in shared orbits; eclipses are common and seasons vary."),
        StarTypeSpec(S.VARIABLE_STAR, "Variable star", "A star whose brightness rises and falls in long cycles, moving its worlds' climates.", S.NEUTRON_STAR),
        StarTypeSpec(S.NEUTRON_STAR, "Neutron star", "The collapsed core of an exploded star: tiny, dim and strongly radioactive."),
        StarTypeSpec(S.PULSAR, "Pulsar", "A rapidly spinning collapsed core that sends out regular pulses of radiation."),
        StarTypeSpec(S.MAGNETAR, "Magnetar", "A collapsed core with an extremely strong magnetic field; its quakes disrupt minds and ships nearby."),
        StarTypeSpec(S.BLACK_HOLE, "Black hole", "A collapsed star whose pull nothing escapes, ringed by a hot disc of infalling matter."),
        StarTypeSpec(S.DEAD_STAR, "Dead star", "A star that no longer shines: a cold remnant."),
        StarTypeSpec(S.BLACK_SUN, "Black sun", "A star that gives no light and absorbs the light around it."),
        StarTypeSpec(S.BROKEN_STAR, "Broken star", "A star split open and unstable, shedding light unevenly."),
        StarTypeSpec(S.STAR_REMNANT, "Star remnant", "The glowing shell of gas and the core left behind by an exploded star."),
        StarTypeSpec(S.REBORN_STAR, "Reborn star", "A star that ended and began again; its output is that of a young star."),
        StarTypeSpec(S.CHAINED_STAR, "Chained star", "A star held by a binding that keeps what is inside it contained."),
        StarTypeSpec(S.WATCHING_STAR, "Watching star", "A star that perceives those who observe it."),
    )
}

STAR_TYPE_LABELS: dict[StarType, str] = {star_type: spec.label for star_type, spec in STAR_TYPES.items()}
