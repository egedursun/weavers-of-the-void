import math
import re
from dataclasses import replace

import pytest

from aerona.catalog.heraldry import CHARGE_NAMES, GLYPH_BOXES, GLYPHS, LIGHTNESS, VALUE_POOLS
from aerona.core.random import SeededRandom
from aerona.domain.enums.collective import (
    ArmsInk,
    ArmsRim,
    ChargeArrangement,
    HeraldicCharge,
    HeraldicDivision,
    PartitionLine,
    ShieldShape,
    SupporterPose,
    Tincture,
)
from aerona.domain.enums.mind import ValueAxis
from aerona.engine.collective.armory import Design, absolute, against, beneath, draw, glyph, region_path, slots
from aerona.engine.collective.heraldry import blazon_of, invent, signature
from aerona.services.books.armssvg import svg

PLAIN = Design(
    shape=ShieldShape.HEATER,
    field=Tincture.BLUE,
    division=HeraldicDivision.PLAIN,
    line=PartitionLine.STRAIGHT,
    second=None,
    charges=(),
    arrangement=ChargeArrangement.TWO_AND_ONE,
    rim=ArmsRim.LINE,
    rim_line=PartitionLine.STRAIGHT,
    rim_tincture=None,
    supporter=HeraldicCharge.NONE,
    pose=SupporterPose.CROSSED,
    supporter_tincture=None,
    crest=HeraldicCharge.NONE,
    crest_tincture=None,
)
NUMBER = re.compile(r"-?\d+(?:\.\d+)?")


def rolled(key: str, axes: list[ValueAxis]) -> dict[str, object]:
    return invent(SeededRandom.for_epoch(11, 1, key), None, axes)


def design_of(values: dict[str, object]) -> Design:
    return Design(
        shape=values["shape"],
        field=values["field"],
        division=values["division"],
        line=values["line"],
        second=values["second"],
        charges=(
            (values["charge"], values["charge_tincture"]),
            (values["charge_two"], values["charge_two_tincture"]),
            (values["charge_three"], values["charge_three_tincture"]),
        ),
        arrangement=values["arrangement"],
        rim=values["rim"],
        rim_line=values["rim_line"],
        rim_tincture=values["rim_tincture"],
        supporter=values["supporter"],
        pose=values["supporter_pose"],
        supporter_tincture=values["supporter_tincture"],
        crest=values["crest"],
        crest_tincture=values["crest_tincture"],
    )


@pytest.mark.parametrize("shape", list(ShieldShape))
def test_every_division_of_every_shape_draws_a_closed_region(shape: ShieldShape) -> None:
    for division in HeraldicDivision:
        design = replace(PLAIN, shape=shape, division=division, second=Tincture.GOLD)
        drawing = draw(design)
        assert drawing.outline.startswith("M") and drawing.outline.endswith("Z")
        assert len(NUMBER.findall(drawing.view_box)) == 4
        if division is not HeraldicDivision.PLAIN:
            assert region_path(design).count("Z") >= 1, division


def test_every_line_changes_the_edge_of_every_lined_division() -> None:
    for division in (HeraldicDivision.PER_PALE, HeraldicDivision.CROSS, HeraldicDivision.BORDURE, HeraldicDivision.FLAUNCHES):
        straight = region_path(replace(PLAIN, division=division))
        for line in PartitionLine:
            if line is not PartitionLine.STRAIGHT:
                assert region_path(replace(PLAIN, division=division, line=line)) != straight, (division, line)


def test_every_charge_has_its_own_drawing_and_name() -> None:
    drawn = {charge: glyph(charge) for charge in HeraldicCharge if charge is not HeraldicCharge.NONE}
    assert all(drawn.values())
    assert len(set(drawn.values())) == len(drawn)
    assert all(CHARGE_NAMES[charge][0] and CHARGE_NAMES[charge][1] for charge in drawn)
    assert all(not part.startswith("m") or absolute(part).startswith("M") for parts in GLYPHS.values() for part in parts)


def test_relative_moves_become_absolute_without_moving_the_line_after_them() -> None:
    assert absolute("m11 19-6-6") == "M11 19l-6-6"
    assert absolute("m5 21 2-2") == "M5 21l2-2"
    assert absolute("M9 3h6") == "M9 3h6"


def test_every_rim_pose_crest_and_fur_is_drawn() -> None:
    for rim in ArmsRim:
        for pose in SupporterPose:
            design = replace(
                PLAIN,
                field=Tincture.ERMINE,
                division=HeraldicDivision.PER_FESS,
                second=Tincture.VAIR,
                rim=rim,
                rim_line=PartitionLine.ENGRAILED,
                supporter=HeraldicCharge.SWORD,
                pose=pose,
                crest=HeraldicCharge.CROWN,
                charges=((HeraldicCharge.ROSE, None),),
            )
            drawing = draw(design)
            assert any(layer.clip is not None for layer in drawing.layers)
            assert sum(not layer.clipped and layer.transform is not None for layer in drawing.layers) >= 2
            assert {layer.ink for layer in drawing.layers} >= {ArmsInk.LINE, ArmsInk.SILVER, ArmsInk.BLACK, ArmsInk.BLUE}


@pytest.mark.parametrize("arrangement", list(ChargeArrangement))
def test_charges_are_laid_out_inside_the_shield_for_every_count(arrangement: ChargeArrangement) -> None:
    for shape in ShieldShape:
        for count in (1, 2, 3):
            spots = slots(replace(PLAIN, shape=shape, arrangement=arrangement), count)
            assert len(spots) == count
            assert all(4 <= x <= 116 and 4 <= y <= 128 and 8 <= size <= 56 for x, y, size in spots)
            assert len({(round(x), round(y)) for x, y, _ in spots}) == count


def test_the_same_holder_always_rolls_the_same_arms_and_others_differ() -> None:
    axes = [ValueAxis.MARTIAL, ValueAxis.HONOUR]
    assert rolled("arms.7.0", axes) == rolled("arms.7.0", axes)
    seen = {signature(rolled(f"arms.{holder}.0", axes)) for holder in range(500)}
    assert len(seen) == 500


def test_the_first_charge_comes_from_the_strongest_value() -> None:
    for holder in range(200):
        values = rolled(f"arms.{holder}.0", [ValueAxis.WEALTH, ValueAxis.LAW])
        if values["charge"] is not HeraldicCharge.NONE:
            assert values["charge"] in VALUE_POOLS[ValueAxis.WEALTH]


def test_charges_stand_out_from_what_lies_beneath_them() -> None:
    for holder in range(300):
        design = design_of(rolled(f"arms.{holder}.0", []))
        shown = [(charge, tincture) for charge, tincture in design.charges if charge is not HeraldicCharge.NONE]
        for (_, tincture), (x, y, size) in zip(shown, slots(design, len(shown)), strict=True):
            under = beneath(design, x, y, size)
            assert tincture in against(under) or not any(against({below}) for below in under) or len(under) > 1


def test_the_blazon_names_every_part_of_the_arms() -> None:
    design = replace(
        PLAIN,
        shape=ShieldShape.KITE,
        division=HeraldicDivision.BEND,
        line=PartitionLine.ENGRAILED,
        second=Tincture.GOLD,
        charges=((HeraldicCharge.ROSE, Tincture.RED), (HeraldicCharge.ROSE, Tincture.RED), (HeraldicCharge.ROSE, Tincture.RED)),
        arrangement=ChargeArrangement.IN_BEND,
        rim=ArmsRim.BEADED,
        rim_tincture=Tincture.SILVER,
        supporter=HeraldicCharge.COLUMN,
        pose=SupporterPose.FLANKING,
        supporter_tincture=Tincture.GOLD,
        crest=HeraldicCharge.CROWN,
        crest_tincture=Tincture.GOLD,
    )
    assert blazon_of(design) == (
        "Azure, a bend engrailed or, three roses gules in bend, within a beaded rim argent; "
        "supported by two columns or; for a crest, a crown or; borne on a kite shield"
    )


def test_the_book_draws_the_same_layers_as_the_app() -> None:
    design = design_of(rolled("arms.3.0", [ValueAxis.NATURE]))
    markup = str(svg(draw(design), "Arms of Ashby", "arms3"))
    assert markup.count("<path") == len(draw(design).layers) + markup.count("<clipPath")
    assert "None" not in markup and 'clip-path="url(#arms3-o)"' in markup


def test_ornaments_outside_the_shield_show_on_light_and_dark_pages() -> None:
    for holder in range(300):
        values = rolled(f"arms.{holder}.0", [])
        for key in ("supporter_tincture", "crest_tincture"):
            tincture = values[key]
            assert tincture is None or LIGHTNESS[tincture] >= 0.5, (holder, key, tincture)


def matrix_of(transform: str) -> tuple[float, float, float, float, float, float]:
    a, b, c, d, e, f = 1.0, 0.0, 0.0, 1.0, 0.0, 0.0
    for name, args in re.findall(r"(\w+)\(([^)]*)\)", transform):
        values = [float(value) for value in args.split()]
        if name == "translate":
            m = (1.0, 0.0, 0.0, 1.0, values[0], values[1])
        elif name == "scale":
            m = (values[0], 0.0, 0.0, values[-1], 0.0, 0.0)
        else:
            turn = math.radians(values[0])
            m = (math.cos(turn), math.sin(turn), -math.sin(turn), math.cos(turn), 0.0, 0.0)
        a, b, c, d, e, f = (
            a * m[0] + c * m[1],
            b * m[0] + d * m[1],
            a * m[2] + c * m[3],
            b * m[2] + d * m[3],
            a * m[4] + c * m[5] + e,
            b * m[4] + d * m[5] + f,
        )
    return a, b, c, d, e, f


def moved(transform: str, x: float, y: float) -> tuple[float, float]:
    a, b, c, d, e, f = matrix_of(transform)
    return (round(a * x + c * y + e, 1), round(b * x + d * y + f, 1))


@pytest.mark.parametrize("pose", [SupporterPose.CROSSED, SupporterPose.FLANKING, SupporterPose.CORNERS])
def test_paired_supporters_mirror_each_other_across_the_shield(pose: SupporterPose) -> None:
    for supporter in (HeraldicCharge.SWORD, HeraldicCharge.KEY, HeraldicCharge.TORCH, HeraldicCharge.BIRD, HeraldicCharge.LAUREL):
        drawing = draw(replace(PLAIN, supporter=supporter, pose=pose, supporter_tincture=Tincture.GOLD))
        copies = [layer.transform for layer in drawing.layers if not layer.clipped and layer.ink is ArmsInk.LINE and layer.transform]
        x0, y0, x1, y1 = GLYPH_BOXES[supporter]
        corners = [(x0, y0), (x1, y0), (x0, y1), (x1, y1), ((x0 + x1) / 2, y0)]
        shapes = {tuple(sorted(moved(transform, x, y) for x, y in corners)) for transform in copies if transform}
        mirrored = {tuple(sorted((round(120 - x, 1), y) for x, y in shape)) for shape in shapes}
        assert shapes == mirrored, (pose, supporter)


def test_every_charge_sits_on_the_centre_of_its_slot() -> None:
    for charge in (HeraldicCharge.KEY, HeraldicCharge.LAUREL, HeraldicCharge.HELPING_HAND, HeraldicCharge.WING):
        design = replace(PLAIN, charges=((charge, Tincture.GOLD),))
        ((x, y, _),) = slots(design, 1)
        transform = next(layer.transform for layer in draw(design).layers if layer.transform)
        x0, y0, x1, y1 = GLYPH_BOXES[charge]
        assert moved(transform, (x0 + x1) / 2, (y0 + y1) / 2) == (round(x, 1), round(y, 1))


MIRRORED_DIVISIONS = [
    division
    for division in HeraldicDivision
    if division
    not in {
        HeraldicDivision.PLAIN,
        HeraldicDivision.PER_PALE,
        HeraldicDivision.PER_BEND,
        HeraldicDivision.PER_BEND_SINISTER,
        HeraldicDivision.QUARTERLY,
        HeraldicDivision.GYRONNY,
        HeraldicDivision.PALY,
        HeraldicDivision.BENDY,
        HeraldicDivision.BENDY_SINISTER,
        HeraldicDivision.CHEQUY,
        HeraldicDivision.BEND,
        HeraldicDivision.BEND_SINISTER,
        HeraldicDivision.CANTON,
    }
]


def points_of(d: str) -> list[tuple[float, float]]:
    rings = re.findall(r"M(-?[\d.]+) (-?[\d.]+)a([\d.]+)", d)
    if rings:
        return [(float(x) + float(r), float(y)) for x, y, r in rings]
    numbers = [float(value) for value in re.findall(r"-?\d+(?:\.\d+)?", d)]
    return list(zip(numbers[::2], numbers[1::2], strict=False))


def is_mirrored(d: str) -> bool:
    points = points_of(d)
    grid = {(round(x * 10), round(y * 10)) for x, y in points}
    near = [(dx, dy) for dx in (-2, -1, 0, 1, 2) for dy in (-2, -1, 0, 1, 2)]
    return all(any((round((120 - x) * 10) + dx, round(y * 10) + dy) in grid for dx, dy in near) for x, y in points)


@pytest.mark.parametrize("shape", list(ShieldShape))
def test_every_balanced_division_and_edge_is_a_mirror_image_on_every_line(shape: ShieldShape) -> None:
    for line in PartitionLine:
        for division in MIRRORED_DIVISIONS:
            assert is_mirrored(region_path(replace(PLAIN, shape=shape, division=division, line=line))), (shape, division, line)
        outline = draw(replace(PLAIN, shape=shape, rim_line=line)).outline
        assert is_mirrored(outline), (shape, line)
        xs = [x for x, _ in points_of(outline)]
        assert max(xs) - min(xs) > 80, (shape, line)


@pytest.mark.parametrize("shape", list(ShieldShape))
def test_every_rim_is_a_mirror_image(shape: ShieldShape) -> None:
    for rim in ArmsRim:
        for layer in draw(replace(PLAIN, shape=shape, rim=rim)).layers:
            if layer.transform is None and layer.clip is None:
                assert is_mirrored(layer.d), (shape, rim)
