from aerona.catalog.peoples import IMAGE_MODES, MODE_STYLE, STYLE_AXES, STYLE_MIDPOINT, STYLE_VALUES, Style
from aerona.constants.units import PERCENT
from aerona.db.tables.demography import PeopleCultureRow
from aerona.domain.enums.culture import ArtMode
from aerona.rules.registry import Rules


def style_of(culture: PeopleCultureRow | None) -> Style | None:
    if culture is None:
        return None
    return Style(culture.ornament, culture.geometry, culture.colour, culture.scale, culture.symmetry)


def axis_of(style: Style, axis: str) -> int:
    return int(getattr(style, axis))


def affinity(style: Style, mode: ArtMode) -> float:
    weights = MODE_STYLE[mode]
    return sum((axis_of(style, axis) - STYLE_MIDPOINT) / STYLE_MIDPOINT * axis_of(weights, axis) for axis in STYLE_AXES) / PERCENT


def favoured_modes(style: Style, count: int) -> list[ArtMode]:
    ranked = sorted(ArtMode, key=lambda mode: (-affinity(style, mode), mode.value))
    return [mode for mode in ranked[:count] if affinity(style, mode) > 0]


def image_mode(style: Style | None) -> ArtMode:
    if style is None:
        return ArtMode.SOLID_IMAGE
    return max(IMAGE_MODES, key=lambda mode: (affinity(style, mode), mode.value))


def style_fit(rules: Rules, style: Style | None, medium: ArtMode) -> float:
    if style is None:
        return 1.0
    leaning = affinity(style, medium)
    threshold = rules.customs.style_fit_at / PERCENT
    if leaning >= threshold:
        return rules.customs.aesthetic_fit_pct / PERCENT
    if leaning <= -threshold:
        return rules.customs.aesthetic_clash_pct / PERCENT
    return 1.0


def style_message(rules: Rules, style: Style | None, medium: ArtMode, message: dict[str, int]) -> dict[str, int]:
    if style is None or affinity(style, medium) < rules.customs.style_fit_at / PERCENT:
        return dict(message)
    strongest = max(STYLE_AXES, key=lambda axis: (abs(axis_of(style, axis) - STYLE_MIDPOINT), axis))
    axis = STYLE_VALUES[strongest].value
    sign = 1 if axis_of(style, strongest) >= STYLE_MIDPOINT else -1
    return {**message, axis: message.get(axis, 0) + sign * rules.customs.aesthetic_message}
