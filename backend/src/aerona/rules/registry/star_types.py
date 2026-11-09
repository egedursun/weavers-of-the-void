from dataclasses import dataclass

from aerona.rules.groups import RuleGroup
from aerona.rules.model import rule


@dataclass(frozen=True)
class StarTypeRules:
    brightness_heat_pct: int = rule(
        15, 0, 100, RuleGroup.SKY, "Temperature its worlds gain per point of brightness above the middle of its type's band (%; lose below)"
    )
    yellow_dwarf_brightness_min: int = rule(55, 0, 100, RuleGroup.SKY, "Yellow dwarf: lowest brightness when kindled")
    yellow_dwarf_brightness_max: int = rule(85, 0, 100, RuleGroup.SKY, "Yellow dwarf: highest brightness when kindled")
    yellow_dwarf_heat: int = rule(0, -50, 50, RuleGroup.SKY, "Yellow dwarf: temperature shift of the worlds it lights")
    yellow_dwarf_capacity: int = rule(100, 0, 1000, RuleGroup.SKY, "Yellow dwarf: life capacity of the worlds it lights (%)")
    yellow_dwarf_collapse_weight: int = rule(
        0, 0, 100, RuleGroup.SKY, "Yellow dwarf: weight of being the star that collapses in a spontaneous supernova or black sun (0 never)"
    )
    yellow_dwarf_flare_weight: int = rule(1, 0, 100, RuleGroup.SKY, "Yellow dwarf: weight of being the star that flares (0 never)")
    yellow_dwarf_mass: int = rule(100, 1, 100000, RuleGroup.SKY, "Yellow dwarf: mass of a star of this kind, in hundredths of a sun")
    blue_star_brightness_min: int = rule(85, 0, 100, RuleGroup.SKY, "Blue star: lowest brightness when kindled")
    blue_star_brightness_max: int = rule(100, 0, 100, RuleGroup.SKY, "Blue star: highest brightness when kindled")
    blue_star_heat: int = rule(14, -50, 50, RuleGroup.SKY, "Blue star: temperature shift of the worlds it lights")
    blue_star_capacity: int = rule(82, 0, 1000, RuleGroup.SKY, "Blue star: life capacity of the worlds it lights (%)")
    blue_star_collapse_weight: int = rule(
        3, 0, 100, RuleGroup.SKY, "Blue star: weight of being the star that collapses in a spontaneous supernova or black sun (0 never)"
    )
    blue_star_flare_weight: int = rule(2, 0, 100, RuleGroup.SKY, "Blue star: weight of being the star that flares (0 never)")
    blue_star_mass: int = rule(2000, 1, 100000, RuleGroup.SKY, "Blue star: mass of a star of this kind, in hundredths of a sun")
    blue_white_star_brightness_min: int = rule(75, 0, 100, RuleGroup.SKY, "Blue-white star: lowest brightness when kindled")
    blue_white_star_brightness_max: int = rule(95, 0, 100, RuleGroup.SKY, "Blue-white star: highest brightness when kindled")
    blue_white_star_heat: int = rule(9, -50, 50, RuleGroup.SKY, "Blue-white star: temperature shift of the worlds it lights")
    blue_white_star_capacity: int = rule(92, 0, 1000, RuleGroup.SKY, "Blue-white star: life capacity of the worlds it lights (%)")
    blue_white_star_collapse_weight: int = rule(
        1, 0, 100, RuleGroup.SKY, "Blue-white star: weight of being the star that collapses in a spontaneous supernova or black sun (0 never)"
    )
    blue_white_star_flare_weight: int = rule(1, 0, 100, RuleGroup.SKY, "Blue-white star: weight of being the star that flares (0 never)")
    blue_white_star_mass: int = rule(400, 1, 100000, RuleGroup.SKY, "Blue-white star: mass of a star of this kind, in hundredths of a sun")
    white_star_brightness_min: int = rule(65, 0, 100, RuleGroup.SKY, "White star: lowest brightness when kindled")
    white_star_brightness_max: int = rule(90, 0, 100, RuleGroup.SKY, "White star: highest brightness when kindled")
    white_star_heat: int = rule(5, -50, 50, RuleGroup.SKY, "White star: temperature shift of the worlds it lights")
    white_star_capacity: int = rule(97, 0, 1000, RuleGroup.SKY, "White star: life capacity of the worlds it lights (%)")
    white_star_collapse_weight: int = rule(
        0, 0, 100, RuleGroup.SKY, "White star: weight of being the star that collapses in a spontaneous supernova or black sun (0 never)"
    )
    white_star_flare_weight: int = rule(1, 0, 100, RuleGroup.SKY, "White star: weight of being the star that flares (0 never)")
    white_star_mass: int = rule(180, 1, 100000, RuleGroup.SKY, "White star: mass of a star of this kind, in hundredths of a sun")
    yellow_white_star_brightness_min: int = rule(60, 0, 100, RuleGroup.SKY, "Yellow-white star: lowest brightness when kindled")
    yellow_white_star_brightness_max: int = rule(88, 0, 100, RuleGroup.SKY, "Yellow-white star: highest brightness when kindled")
    yellow_white_star_heat: int = rule(2, -50, 50, RuleGroup.SKY, "Yellow-white star: temperature shift of the worlds it lights")
    yellow_white_star_capacity: int = rule(100, 0, 1000, RuleGroup.SKY, "Yellow-white star: life capacity of the worlds it lights (%)")
    yellow_white_star_collapse_weight: int = rule(
        0, 0, 100, RuleGroup.SKY, "Yellow-white star: weight of being the star that collapses in a spontaneous supernova or black sun (0 never)"
    )
    yellow_white_star_flare_weight: int = rule(1, 0, 100, RuleGroup.SKY, "Yellow-white star: weight of being the star that flares (0 never)")
    yellow_white_star_mass: int = rule(130, 1, 100000, RuleGroup.SKY, "Yellow-white star: mass of a star of this kind, in hundredths of a sun")
    orange_dwarf_brightness_min: int = rule(40, 0, 100, RuleGroup.SKY, "Orange dwarf: lowest brightness when kindled")
    orange_dwarf_brightness_max: int = rule(65, 0, 100, RuleGroup.SKY, "Orange dwarf: highest brightness when kindled")
    orange_dwarf_heat: int = rule(-4, -50, 50, RuleGroup.SKY, "Orange dwarf: temperature shift of the worlds it lights")
    orange_dwarf_capacity: int = rule(105, 0, 1000, RuleGroup.SKY, "Orange dwarf: life capacity of the worlds it lights (%)")
    orange_dwarf_collapse_weight: int = rule(
        0, 0, 100, RuleGroup.SKY, "Orange dwarf: weight of being the star that collapses in a spontaneous supernova or black sun (0 never)"
    )
    orange_dwarf_flare_weight: int = rule(1, 0, 100, RuleGroup.SKY, "Orange dwarf: weight of being the star that flares (0 never)")
    orange_dwarf_mass: int = rule(75, 1, 100000, RuleGroup.SKY, "Orange dwarf: mass of a star of this kind, in hundredths of a sun")
    red_dwarf_brightness_min: int = rule(15, 0, 100, RuleGroup.SKY, "Red dwarf: lowest brightness when kindled")
    red_dwarf_brightness_max: int = rule(40, 0, 100, RuleGroup.SKY, "Red dwarf: highest brightness when kindled")
    red_dwarf_heat: int = rule(-9, -50, 50, RuleGroup.SKY, "Red dwarf: temperature shift of the worlds it lights")
    red_dwarf_capacity: int = rule(88, 0, 1000, RuleGroup.SKY, "Red dwarf: life capacity of the worlds it lights (%)")
    red_dwarf_collapse_weight: int = rule(
        0, 0, 100, RuleGroup.SKY, "Red dwarf: weight of being the star that collapses in a spontaneous supernova or black sun (0 never)"
    )
    red_dwarf_flare_weight: int = rule(4, 0, 100, RuleGroup.SKY, "Red dwarf: weight of being the star that flares (0 never)")
    red_dwarf_mass: int = rule(30, 1, 100000, RuleGroup.SKY, "Red dwarf: mass of a star of this kind, in hundredths of a sun")
    brown_dwarf_brightness_min: int = rule(2, 0, 100, RuleGroup.SKY, "Brown dwarf: lowest brightness when kindled")
    brown_dwarf_brightness_max: int = rule(15, 0, 100, RuleGroup.SKY, "Brown dwarf: highest brightness when kindled")
    brown_dwarf_heat: int = rule(-18, -50, 50, RuleGroup.SKY, "Brown dwarf: temperature shift of the worlds it lights")
    brown_dwarf_capacity: int = rule(50, 0, 1000, RuleGroup.SKY, "Brown dwarf: life capacity of the worlds it lights (%)")
    brown_dwarf_collapse_weight: int = rule(
        0, 0, 100, RuleGroup.SKY, "Brown dwarf: weight of being the star that collapses in a spontaneous supernova or black sun (0 never)"
    )
    brown_dwarf_flare_weight: int = rule(1, 0, 100, RuleGroup.SKY, "Brown dwarf: weight of being the star that flares (0 never)")
    brown_dwarf_mass: int = rule(5, 1, 100000, RuleGroup.SKY, "Brown dwarf: mass of a star of this kind, in hundredths of a sun")
    yellow_giant_brightness_min: int = rule(65, 0, 100, RuleGroup.SKY, "Yellow giant: lowest brightness when kindled")
    yellow_giant_brightness_max: int = rule(90, 0, 100, RuleGroup.SKY, "Yellow giant: highest brightness when kindled")
    yellow_giant_heat: int = rule(6, -50, 50, RuleGroup.SKY, "Yellow giant: temperature shift of the worlds it lights")
    yellow_giant_capacity: int = rule(94, 0, 1000, RuleGroup.SKY, "Yellow giant: life capacity of the worlds it lights (%)")
    yellow_giant_collapse_weight: int = rule(
        0, 0, 100, RuleGroup.SKY, "Yellow giant: weight of being the star that collapses in a spontaneous supernova or black sun (0 never)"
    )
    yellow_giant_flare_weight: int = rule(1, 0, 100, RuleGroup.SKY, "Yellow giant: weight of being the star that flares (0 never)")
    yellow_giant_mass: int = rule(300, 1, 100000, RuleGroup.SKY, "Yellow giant: mass of a star of this kind, in hundredths of a sun")
    red_giant_brightness_min: int = rule(55, 0, 100, RuleGroup.SKY, "Red giant: lowest brightness when kindled")
    red_giant_brightness_max: int = rule(80, 0, 100, RuleGroup.SKY, "Red giant: highest brightness when kindled")
    red_giant_heat: int = rule(4, -50, 50, RuleGroup.SKY, "Red giant: temperature shift of the worlds it lights")
    red_giant_capacity: int = rule(90, 0, 1000, RuleGroup.SKY, "Red giant: life capacity of the worlds it lights (%)")
    red_giant_collapse_weight: int = rule(
        2, 0, 100, RuleGroup.SKY, "Red giant: weight of being the star that collapses in a spontaneous supernova or black sun (0 never)"
    )
    red_giant_flare_weight: int = rule(1, 0, 100, RuleGroup.SKY, "Red giant: weight of being the star that flares (0 never)")
    red_giant_mass: int = rule(120, 1, 100000, RuleGroup.SKY, "Red giant: mass of a star of this kind, in hundredths of a sun")
    blue_giant_brightness_min: int = rule(80, 0, 100, RuleGroup.SKY, "Blue giant: lowest brightness when kindled")
    blue_giant_brightness_max: int = rule(100, 0, 100, RuleGroup.SKY, "Blue giant: highest brightness when kindled")
    blue_giant_heat: int = rule(11, -50, 50, RuleGroup.SKY, "Blue giant: temperature shift of the worlds it lights")
    blue_giant_capacity: int = rule(88, 0, 1000, RuleGroup.SKY, "Blue giant: life capacity of the worlds it lights (%)")
    blue_giant_collapse_weight: int = rule(
        2, 0, 100, RuleGroup.SKY, "Blue giant: weight of being the star that collapses in a spontaneous supernova or black sun (0 never)"
    )
    blue_giant_flare_weight: int = rule(2, 0, 100, RuleGroup.SKY, "Blue giant: weight of being the star that flares (0 never)")
    blue_giant_mass: int = rule(1500, 1, 100000, RuleGroup.SKY, "Blue giant: mass of a star of this kind, in hundredths of a sun")
    red_supergiant_brightness_min: int = rule(60, 0, 100, RuleGroup.SKY, "Red supergiant: lowest brightness when kindled")
    red_supergiant_brightness_max: int = rule(85, 0, 100, RuleGroup.SKY, "Red supergiant: highest brightness when kindled")
    red_supergiant_heat: int = rule(6, -50, 50, RuleGroup.SKY, "Red supergiant: temperature shift of the worlds it lights")
    red_supergiant_capacity: int = rule(85, 0, 1000, RuleGroup.SKY, "Red supergiant: life capacity of the worlds it lights (%)")
    red_supergiant_collapse_weight: int = rule(
        4, 0, 100, RuleGroup.SKY, "Red supergiant: weight of being the star that collapses in a spontaneous supernova or black sun (0 never)"
    )
    red_supergiant_flare_weight: int = rule(2, 0, 100, RuleGroup.SKY, "Red supergiant: weight of being the star that flares (0 never)")
    red_supergiant_mass: int = rule(1500, 1, 100000, RuleGroup.SKY, "Red supergiant: mass of a star of this kind, in hundredths of a sun")
    blue_supergiant_brightness_min: int = rule(90, 0, 100, RuleGroup.SKY, "Blue supergiant: lowest brightness when kindled")
    blue_supergiant_brightness_max: int = rule(100, 0, 100, RuleGroup.SKY, "Blue supergiant: highest brightness when kindled")
    blue_supergiant_heat: int = rule(15, -50, 50, RuleGroup.SKY, "Blue supergiant: temperature shift of the worlds it lights")
    blue_supergiant_capacity: int = rule(80, 0, 1000, RuleGroup.SKY, "Blue supergiant: life capacity of the worlds it lights (%)")
    blue_supergiant_collapse_weight: int = rule(
        4, 0, 100, RuleGroup.SKY, "Blue supergiant: weight of being the star that collapses in a spontaneous supernova or black sun (0 never)"
    )
    blue_supergiant_flare_weight: int = rule(2, 0, 100, RuleGroup.SKY, "Blue supergiant: weight of being the star that flares (0 never)")
    blue_supergiant_mass: int = rule(2500, 1, 100000, RuleGroup.SKY, "Blue supergiant: mass of a star of this kind, in hundredths of a sun")
    hypergiant_brightness_min: int = rule(92, 0, 100, RuleGroup.SKY, "Hypergiant: lowest brightness when kindled")
    hypergiant_brightness_max: int = rule(100, 0, 100, RuleGroup.SKY, "Hypergiant: highest brightness when kindled")
    hypergiant_heat: int = rule(17, -50, 50, RuleGroup.SKY, "Hypergiant: temperature shift of the worlds it lights")
    hypergiant_capacity: int = rule(72, 0, 1000, RuleGroup.SKY, "Hypergiant: life capacity of the worlds it lights (%)")
    hypergiant_collapse_weight: int = rule(
        6, 0, 100, RuleGroup.SKY, "Hypergiant: weight of being the star that collapses in a spontaneous supernova or black sun (0 never)"
    )
    hypergiant_flare_weight: int = rule(3, 0, 100, RuleGroup.SKY, "Hypergiant: weight of being the star that flares (0 never)")
    hypergiant_mass: int = rule(6000, 1, 100000, RuleGroup.SKY, "Hypergiant: mass of a star of this kind, in hundredths of a sun")
    hypergiant_instability: int = rule(1, 0, 20, RuleGroup.SKY, "Hypergiant: epochs it cuts from each climate age of its worlds")
    wolf_rayet_brightness_min: int = rule(88, 0, 100, RuleGroup.SKY, "Wolf-Rayet star: lowest brightness when kindled")
    wolf_rayet_brightness_max: int = rule(100, 0, 100, RuleGroup.SKY, "Wolf-Rayet star: highest brightness when kindled")
    wolf_rayet_heat: int = rule(16, -50, 50, RuleGroup.SKY, "Wolf-Rayet star: temperature shift of the worlds it lights")
    wolf_rayet_capacity: int = rule(70, 0, 1000, RuleGroup.SKY, "Wolf-Rayet star: life capacity of the worlds it lights (%)")
    wolf_rayet_collapse_weight: int = rule(
        5, 0, 100, RuleGroup.SKY, "Wolf-Rayet star: weight of being the star that collapses in a spontaneous supernova or black sun (0 never)"
    )
    wolf_rayet_flare_weight: int = rule(3, 0, 100, RuleGroup.SKY, "Wolf-Rayet star: weight of being the star that flares (0 never)")
    wolf_rayet_mass: int = rule(2500, 1, 100000, RuleGroup.SKY, "Wolf-Rayet star: mass of a star of this kind, in hundredths of a sun")
    wolf_rayet_sail_danger: int = rule(5, 0, 100, RuleGroup.COSMOS_AND_TRAVEL, "Wolf-Rayet star: extra danger of a light-sail route bound to it")
    protostar_brightness_min: int = rule(20, 0, 100, RuleGroup.SKY, "Protostar: lowest brightness when kindled")
    protostar_brightness_max: int = rule(50, 0, 100, RuleGroup.SKY, "Protostar: highest brightness when kindled")
    protostar_heat: int = rule(-6, -50, 50, RuleGroup.SKY, "Protostar: temperature shift of the worlds it lights")
    protostar_capacity: int = rule(70, 0, 1000, RuleGroup.SKY, "Protostar: life capacity of the worlds it lights (%)")
    protostar_collapse_weight: int = rule(
        0, 0, 100, RuleGroup.SKY, "Protostar: weight of being the star that collapses in a spontaneous supernova or black sun (0 never)"
    )
    protostar_flare_weight: int = rule(4, 0, 100, RuleGroup.SKY, "Protostar: weight of being the star that flares (0 never)")
    protostar_mass: int = rule(100, 1, 100000, RuleGroup.SKY, "Protostar: mass of a star of this kind, in hundredths of a sun")
    protostar_sail_danger: int = rule(5, 0, 100, RuleGroup.COSMOS_AND_TRAVEL, "Protostar: extra danger of a light-sail route bound to it")
    protostar_instability: int = rule(2, 0, 20, RuleGroup.SKY, "Protostar: epochs it cuts from each climate age of its worlds")
    carbon_star_brightness_min: int = rule(40, 0, 100, RuleGroup.SKY, "Carbon star: lowest brightness when kindled")
    carbon_star_brightness_max: int = rule(65, 0, 100, RuleGroup.SKY, "Carbon star: highest brightness when kindled")
    carbon_star_heat: int = rule(2, -50, 50, RuleGroup.SKY, "Carbon star: temperature shift of the worlds it lights")
    carbon_star_capacity: int = rule(85, 0, 1000, RuleGroup.SKY, "Carbon star: life capacity of the worlds it lights (%)")
    carbon_star_collapse_weight: int = rule(
        1, 0, 100, RuleGroup.SKY, "Carbon star: weight of being the star that collapses in a spontaneous supernova or black sun (0 never)"
    )
    carbon_star_flare_weight: int = rule(1, 0, 100, RuleGroup.SKY, "Carbon star: weight of being the star that flares (0 never)")
    carbon_star_mass: int = rule(200, 1, 100000, RuleGroup.SKY, "Carbon star: mass of a star of this kind, in hundredths of a sun")
    white_dwarf_brightness_min: int = rule(20, 0, 100, RuleGroup.SKY, "White dwarf: lowest brightness when kindled")
    white_dwarf_brightness_max: int = rule(45, 0, 100, RuleGroup.SKY, "White dwarf: highest brightness when kindled")
    white_dwarf_heat: int = rule(-10, -50, 50, RuleGroup.SKY, "White dwarf: temperature shift of the worlds it lights")
    white_dwarf_capacity: int = rule(80, 0, 1000, RuleGroup.SKY, "White dwarf: life capacity of the worlds it lights (%)")
    white_dwarf_collapse_weight: int = rule(
        0, 0, 100, RuleGroup.SKY, "White dwarf: weight of being the star that collapses in a spontaneous supernova or black sun (0 never)"
    )
    white_dwarf_flare_weight: int = rule(0, 0, 100, RuleGroup.SKY, "White dwarf: weight of being the star that flares (0 never)")
    white_dwarf_mass: int = rule(60, 1, 100000, RuleGroup.SKY, "White dwarf: mass of a star of this kind, in hundredths of a sun")
    binary_brightness_min: int = rule(60, 0, 100, RuleGroup.SKY, "Binary star: lowest brightness when kindled")
    binary_brightness_max: int = rule(90, 0, 100, RuleGroup.SKY, "Binary star: highest brightness when kindled")
    binary_heat: int = rule(3, -50, 50, RuleGroup.SKY, "Binary star: temperature shift of the worlds it lights")
    binary_capacity: int = rule(95, 0, 1000, RuleGroup.SKY, "Binary star: life capacity of the worlds it lights (%)")
    binary_collapse_weight: int = rule(
        0, 0, 100, RuleGroup.SKY, "Binary star: weight of being the star that collapses in a spontaneous supernova or black sun (0 never)"
    )
    binary_flare_weight: int = rule(1, 0, 100, RuleGroup.SKY, "Binary star: weight of being the star that flares (0 never)")
    binary_mass: int = rule(150, 1, 100000, RuleGroup.SKY, "Binary star: mass of a star of this kind, in hundredths of a sun")
    binary_eclipse_weight: int = rule(2, 0, 50, RuleGroup.SKY, "Binary star: extra spontaneous eclipse weight from its companion suns")
    trinary_brightness_min: int = rule(60, 0, 100, RuleGroup.SKY, "Triple star: lowest brightness when kindled")
    trinary_brightness_max: int = rule(90, 0, 100, RuleGroup.SKY, "Triple star: highest brightness when kindled")
    trinary_heat: int = rule(4, -50, 50, RuleGroup.SKY, "Triple star: temperature shift of the worlds it lights")
    trinary_capacity: int = rule(90, 0, 1000, RuleGroup.SKY, "Triple star: life capacity of the worlds it lights (%)")
    trinary_collapse_weight: int = rule(
        0, 0, 100, RuleGroup.SKY, "Triple star: weight of being the star that collapses in a spontaneous supernova or black sun (0 never)"
    )
    trinary_flare_weight: int = rule(1, 0, 100, RuleGroup.SKY, "Triple star: weight of being the star that flares (0 never)")
    trinary_mass: int = rule(250, 1, 100000, RuleGroup.SKY, "Triple star: mass of a star of this kind, in hundredths of a sun")
    trinary_eclipse_weight: int = rule(3, 0, 50, RuleGroup.SKY, "Triple star: extra spontaneous eclipse weight from its companion suns")
    trinary_instability: int = rule(1, 0, 20, RuleGroup.SKY, "Triple star: epochs it cuts from each climate age of its worlds")
    variable_star_brightness_min: int = rule(40, 0, 100, RuleGroup.SKY, "Variable star: lowest brightness when kindled")
    variable_star_brightness_max: int = rule(90, 0, 100, RuleGroup.SKY, "Variable star: highest brightness when kindled")
    variable_star_heat: int = rule(0, -50, 50, RuleGroup.SKY, "Variable star: temperature shift of the worlds it lights")
    variable_star_capacity: int = rule(90, 0, 1000, RuleGroup.SKY, "Variable star: life capacity of the worlds it lights (%)")
    variable_star_collapse_weight: int = rule(
        2, 0, 100, RuleGroup.SKY, "Variable star: weight of being the star that collapses in a spontaneous supernova or black sun (0 never)"
    )
    variable_star_flare_weight: int = rule(2, 0, 100, RuleGroup.SKY, "Variable star: weight of being the star that flares (0 never)")
    variable_star_mass: int = rule(200, 1, 100000, RuleGroup.SKY, "Variable star: mass of a star of this kind, in hundredths of a sun")
    variable_star_instability: int = rule(3, 0, 20, RuleGroup.SKY, "Variable star: epochs it cuts from each climate age of its worlds")
    neutron_star_brightness_min: int = rule(5, 0, 100, RuleGroup.SKY, "Neutron star: lowest brightness when kindled")
    neutron_star_brightness_max: int = rule(20, 0, 100, RuleGroup.SKY, "Neutron star: highest brightness when kindled")
    neutron_star_heat: int = rule(-16, -50, 50, RuleGroup.SKY, "Neutron star: temperature shift of the worlds it lights")
    neutron_star_capacity: int = rule(50, 0, 1000, RuleGroup.SKY, "Neutron star: life capacity of the worlds it lights (%)")
    neutron_star_collapse_weight: int = rule(
        0, 0, 100, RuleGroup.SKY, "Neutron star: weight of being the star that collapses in a spontaneous supernova or black sun (0 never)"
    )
    neutron_star_flare_weight: int = rule(1, 0, 100, RuleGroup.SKY, "Neutron star: weight of being the star that flares (0 never)")
    neutron_star_mass: int = rule(140, 1, 100000, RuleGroup.SKY, "Neutron star: mass of a star of this kind, in hundredths of a sun")
    neutron_star_sail_danger: int = rule(8, 0, 100, RuleGroup.COSMOS_AND_TRAVEL, "Neutron star: extra danger of a light-sail route bound to it")
    pulsar_brightness_min: int = rule(10, 0, 100, RuleGroup.SKY, "Pulsar: lowest brightness when kindled")
    pulsar_brightness_max: int = rule(30, 0, 100, RuleGroup.SKY, "Pulsar: highest brightness when kindled")
    pulsar_heat: int = rule(-14, -50, 50, RuleGroup.SKY, "Pulsar: temperature shift of the worlds it lights")
    pulsar_capacity: int = rule(50, 0, 1000, RuleGroup.SKY, "Pulsar: life capacity of the worlds it lights (%)")
    pulsar_collapse_weight: int = rule(
        1, 0, 100, RuleGroup.SKY, "Pulsar: weight of being the star that collapses in a spontaneous supernova or black sun (0 never)"
    )
    pulsar_flare_weight: int = rule(2, 0, 100, RuleGroup.SKY, "Pulsar: weight of being the star that flares (0 never)")
    pulsar_mass: int = rule(140, 1, 100000, RuleGroup.SKY, "Pulsar: mass of a star of this kind, in hundredths of a sun")
    pulsar_sail_danger: int = rule(10, 0, 100, RuleGroup.COSMOS_AND_TRAVEL, "Pulsar: extra danger of a light-sail route bound to it")
    magnetar_brightness_min: int = rule(10, 0, 100, RuleGroup.SKY, "Magnetar: lowest brightness when kindled")
    magnetar_brightness_max: int = rule(30, 0, 100, RuleGroup.SKY, "Magnetar: highest brightness when kindled")
    magnetar_heat: int = rule(-14, -50, 50, RuleGroup.SKY, "Magnetar: temperature shift of the worlds it lights")
    magnetar_capacity: int = rule(40, 0, 1000, RuleGroup.SKY, "Magnetar: life capacity of the worlds it lights (%)")
    magnetar_collapse_weight: int = rule(
        0, 0, 100, RuleGroup.SKY, "Magnetar: weight of being the star that collapses in a spontaneous supernova or black sun (0 never)"
    )
    magnetar_flare_weight: int = rule(6, 0, 100, RuleGroup.SKY, "Magnetar: weight of being the star that flares (0 never)")
    magnetar_mass: int = rule(150, 1, 100000, RuleGroup.SKY, "Magnetar: mass of a star of this kind, in hundredths of a sun")
    magnetar_sanity_erosion: int = rule(1, 0, 100, RuleGroup.COSMIC_HORROR, "Magnetar: extra per-epoch sanity loss of those living under it")
    magnetar_sail_danger: int = rule(12, 0, 100, RuleGroup.COSMOS_AND_TRAVEL, "Magnetar: extra danger of a light-sail route bound to it")
    black_hole_brightness_min: int = rule(0, 0, 100, RuleGroup.SKY, "Black hole: lowest brightness when kindled")
    black_hole_brightness_max: int = rule(0, 0, 100, RuleGroup.SKY, "Black hole: highest brightness when kindled")
    black_hole_heat: int = rule(-25, -50, 50, RuleGroup.SKY, "Black hole: temperature shift of the worlds it lights")
    black_hole_capacity: int = rule(30, 0, 1000, RuleGroup.SKY, "Black hole: life capacity of the worlds it lights (%)")
    black_hole_collapse_weight: int = rule(
        0, 0, 100, RuleGroup.SKY, "Black hole: weight of being the star that collapses in a spontaneous supernova or black sun (0 never)"
    )
    black_hole_flare_weight: int = rule(0, 0, 100, RuleGroup.SKY, "Black hole: weight of being the star that flares (0 never)")
    black_hole_mass: int = rule(1000, 1, 100000, RuleGroup.SKY, "Black hole: mass of a star of this kind, in hundredths of a sun")
    black_hole_sail_danger: int = rule(15, 0, 100, RuleGroup.COSMOS_AND_TRAVEL, "Black hole: extra danger of a light-sail route bound to it")
    dead_star_brightness_min: int = rule(0, 0, 100, RuleGroup.SKY, "Dead star: lowest brightness when kindled")
    dead_star_brightness_max: int = rule(10, 0, 100, RuleGroup.SKY, "Dead star: highest brightness when kindled")
    dead_star_heat: int = rule(-22, -50, 50, RuleGroup.SKY, "Dead star: temperature shift of the worlds it lights")
    dead_star_capacity: int = rule(40, 0, 1000, RuleGroup.SKY, "Dead star: life capacity of the worlds it lights (%)")
    dead_star_collapse_weight: int = rule(
        0, 0, 100, RuleGroup.SKY, "Dead star: weight of being the star that collapses in a spontaneous supernova or black sun (0 never)"
    )
    dead_star_flare_weight: int = rule(0, 0, 100, RuleGroup.SKY, "Dead star: weight of being the star that flares (0 never)")
    dead_star_mass: int = rule(60, 1, 100000, RuleGroup.SKY, "Dead star: mass of a star of this kind, in hundredths of a sun")
    black_sun_brightness_min: int = rule(0, 0, 100, RuleGroup.SKY, "Black sun: lowest brightness when kindled")
    black_sun_brightness_max: int = rule(0, 0, 100, RuleGroup.SKY, "Black sun: highest brightness when kindled")
    black_sun_heat: int = rule(-24, -50, 50, RuleGroup.SKY, "Black sun: temperature shift of the worlds it lights")
    black_sun_capacity: int = rule(35, 0, 1000, RuleGroup.SKY, "Black sun: life capacity of the worlds it lights (%)")
    black_sun_collapse_weight: int = rule(
        0, 0, 100, RuleGroup.SKY, "Black sun: weight of being the star that collapses in a spontaneous supernova or black sun (0 never)"
    )
    black_sun_flare_weight: int = rule(0, 0, 100, RuleGroup.SKY, "Black sun: weight of being the star that flares (0 never)")
    black_sun_mass: int = rule(1000, 1, 100000, RuleGroup.SKY, "Black sun: mass of a star of this kind, in hundredths of a sun")
    black_sun_sanity_erosion: int = rule(1, 0, 100, RuleGroup.COSMIC_HORROR, "Black sun: extra per-epoch sanity loss of those living under it")
    broken_star_brightness_min: int = rule(30, 0, 100, RuleGroup.SKY, "Broken star: lowest brightness when kindled")
    broken_star_brightness_max: int = rule(60, 0, 100, RuleGroup.SKY, "Broken star: highest brightness when kindled")
    broken_star_heat: int = rule(-6, -50, 50, RuleGroup.SKY, "Broken star: temperature shift of the worlds it lights")
    broken_star_capacity: int = rule(70, 0, 1000, RuleGroup.SKY, "Broken star: life capacity of the worlds it lights (%)")
    broken_star_collapse_weight: int = rule(
        3, 0, 100, RuleGroup.SKY, "Broken star: weight of being the star that collapses in a spontaneous supernova or black sun (0 never)"
    )
    broken_star_flare_weight: int = rule(3, 0, 100, RuleGroup.SKY, "Broken star: weight of being the star that flares (0 never)")
    broken_star_mass: int = rule(100, 1, 100000, RuleGroup.SKY, "Broken star: mass of a star of this kind, in hundredths of a sun")
    star_remnant_brightness_min: int = rule(10, 0, 100, RuleGroup.SKY, "Star remnant: lowest brightness when kindled")
    star_remnant_brightness_max: int = rule(25, 0, 100, RuleGroup.SKY, "Star remnant: highest brightness when kindled")
    star_remnant_heat: int = rule(-15, -50, 50, RuleGroup.SKY, "Star remnant: temperature shift of the worlds it lights")
    star_remnant_capacity: int = rule(50, 0, 1000, RuleGroup.SKY, "Star remnant: life capacity of the worlds it lights (%)")
    star_remnant_collapse_weight: int = rule(
        0, 0, 100, RuleGroup.SKY, "Star remnant: weight of being the star that collapses in a spontaneous supernova or black sun (0 never)"
    )
    star_remnant_flare_weight: int = rule(0, 0, 100, RuleGroup.SKY, "Star remnant: weight of being the star that flares (0 never)")
    star_remnant_mass: int = rule(140, 1, 100000, RuleGroup.SKY, "Star remnant: mass of a star of this kind, in hundredths of a sun")
    star_remnant_sail_danger: int = rule(5, 0, 100, RuleGroup.COSMOS_AND_TRAVEL, "Star remnant: extra danger of a light-sail route bound to it")
    reborn_star_brightness_min: int = rule(70, 0, 100, RuleGroup.SKY, "Reborn star: lowest brightness when kindled")
    reborn_star_brightness_max: int = rule(85, 0, 100, RuleGroup.SKY, "Reborn star: highest brightness when kindled")
    reborn_star_heat: int = rule(2, -50, 50, RuleGroup.SKY, "Reborn star: temperature shift of the worlds it lights")
    reborn_star_capacity: int = rule(100, 0, 1000, RuleGroup.SKY, "Reborn star: life capacity of the worlds it lights (%)")
    reborn_star_collapse_weight: int = rule(
        0, 0, 100, RuleGroup.SKY, "Reborn star: weight of being the star that collapses in a spontaneous supernova or black sun (0 never)"
    )
    reborn_star_flare_weight: int = rule(1, 0, 100, RuleGroup.SKY, "Reborn star: weight of being the star that flares (0 never)")
    reborn_star_mass: int = rule(100, 1, 100000, RuleGroup.SKY, "Reborn star: mass of a star of this kind, in hundredths of a sun")
    chained_star_brightness_min: int = rule(30, 0, 100, RuleGroup.SKY, "Chained star: lowest brightness when kindled")
    chained_star_brightness_max: int = rule(55, 0, 100, RuleGroup.SKY, "Chained star: highest brightness when kindled")
    chained_star_heat: int = rule(-3, -50, 50, RuleGroup.SKY, "Chained star: temperature shift of the worlds it lights")
    chained_star_capacity: int = rule(90, 0, 1000, RuleGroup.SKY, "Chained star: life capacity of the worlds it lights (%)")
    chained_star_collapse_weight: int = rule(
        0, 0, 100, RuleGroup.SKY, "Chained star: weight of being the star that collapses in a spontaneous supernova or black sun (0 never)"
    )
    chained_star_flare_weight: int = rule(1, 0, 100, RuleGroup.SKY, "Chained star: weight of being the star that flares (0 never)")
    chained_star_mass: int = rule(100, 1, 100000, RuleGroup.SKY, "Chained star: mass of a star of this kind, in hundredths of a sun")
    chained_star_leak_repair: int = rule(1, 0, 50, RuleGroup.COSMIC_HORROR, "Chained star: leak it repairs in each of its worlds per epoch")
    watching_star_brightness_min: int = rule(40, 0, 100, RuleGroup.SKY, "Watching star: lowest brightness when kindled")
    watching_star_brightness_max: int = rule(70, 0, 100, RuleGroup.SKY, "Watching star: highest brightness when kindled")
    watching_star_heat: int = rule(0, -50, 50, RuleGroup.SKY, "Watching star: temperature shift of the worlds it lights")
    watching_star_capacity: int = rule(95, 0, 1000, RuleGroup.SKY, "Watching star: life capacity of the worlds it lights (%)")
    watching_star_collapse_weight: int = rule(
        0, 0, 100, RuleGroup.SKY, "Watching star: weight of being the star that collapses in a spontaneous supernova or black sun (0 never)"
    )
    watching_star_flare_weight: int = rule(1, 0, 100, RuleGroup.SKY, "Watching star: weight of being the star that flares (0 never)")
    watching_star_mass: int = rule(100, 1, 100000, RuleGroup.SKY, "Watching star: mass of a star of this kind, in hundredths of a sun")
    watching_star_leak: int = rule(1, 0, 50, RuleGroup.COSMIC_HORROR, "Watching star: leak it draws into each of its worlds per epoch")
    watching_star_sanity_erosion: int = rule(2, 0, 100, RuleGroup.COSMIC_HORROR, "Watching star: extra per-epoch sanity loss of those living under it")
