import math
from collections.abc import Callable
from io import BytesIO

from PIL import Image, ImageDraw

from aerona.cartography.model import BorderKind, KnownState, MapWindow, WorldMap
from aerona.constants.books import (
    EXTENT_PADDING,
    FOG_ALPHA,
    HACHURE_ALPHA,
    HACHURE_BASE,
    HACHURE_GAIN,
    HACHURE_MIN,
    HACHURE_WIDTH,
    SEAM_WIDTH,
    TERRAIN_FORMAT,
    TERRAIN_QUALITY,
    TERRAIN_SUPERSAMPLE,
    WAVE_ALPHAS,
    WAVE_WIDTHS,
)

LIGHT = (255, 255, 255)
DARK = (0, 0, 0)
FULL = 255

Point = tuple[float, float]


def _rgb(colour: str) -> tuple[int, int, int]:
    digits = colour.lstrip("#")
    if len(digits) == 3:
        digits = "".join(character * 2 for character in digits)
    return int(digits[0:2], 16), int(digits[2:4], 16), int(digits[4:6], 16)


def _cell_colour(world_map: WorldMap, index: int) -> str:
    cells = world_map.cells
    palette = world_map.palette
    if cells.known[index] == KnownState.UNKNOWN:
        return palette.unknown_water if cells.water[index] else palette.unknown_land
    if cells.water[index] and cells.coastal[index]:
        return palette.coastal_water
    biome = cells.biome[index]
    if 0 <= biome < len(palette.terrain_colours):
        return palette.terrain_colours[biome]
    return palette.terrain_colours[-1] if palette.terrain_colours else palette.background


def _overlay(base: Image.Image, colour: tuple[int, int, int], mask: Image.Image) -> None:
    base.paste(colour, (0, 0), mask)


def book_frame(world_map: WorldMap) -> MapWindow:
    window = world_map.window
    extent = world_map.extent
    if extent.known_cells <= 0 or extent.width <= 0 or extent.height <= 0:
        return window
    padding = max(extent.width, extent.height) * EXTENT_PADDING
    left = max(window.x, extent.x - padding)
    top = max(window.y, extent.y - padding)
    right = min(window.x + window.width, extent.x + extent.width + padding)
    bottom = min(window.y + window.height, extent.y + extent.height + padding)
    return MapWindow(x=left, y=top, width=max(1.0, right - left), height=max(1.0, bottom - top))


class Canvas:
    def __init__(self, world_map: WorldMap, width: int) -> None:
        self.world_map = world_map
        self.window = book_frame(world_map)
        self.scale = width * TERRAIN_SUPERSAMPLE / max(self.window.width, 1.0)
        self.size = (max(1, math.ceil(self.window.width * self.scale)), max(1, math.ceil(self.window.height * self.scale)))
        self.seam = max(1, round(SEAM_WIDTH * self.scale))
        self.base = Image.new("RGB", self.size, _rgb(world_map.palette.background))

    def place(self, x: float, y: float) -> Point:
        return (x - self.window.x) * self.scale, (y - self.window.y) * self.scale

    def polygon(self, index: int) -> list[Point]:
        cells = self.world_map.cells
        start, end = cells.polygon_offsets[index], cells.polygon_offsets[index + 1]
        coordinates = cells.polygon_coordinates[start:end]
        return [self.place(coordinates[position], coordinates[position + 1]) for position in range(0, len(coordinates) - 1, 2)]

    def mask(self) -> tuple[Image.Image, ImageDraw.ImageDraw]:
        image = Image.new("L", self.size, 0)
        return image, ImageDraw.Draw(image)

    def water(self) -> list[int]:
        cells = self.world_map.cells
        draw = ImageDraw.Draw(self.base)
        land: list[int] = []
        for index in range(len(cells.x)):
            points = self.polygon(index)
            if len(points) < 3:
                continue
            if cells.known[index] != KnownState.UNKNOWN and not cells.water[index]:
                land.append(index)
                continue
            colour = _rgb(_cell_colour(self.world_map, index))
            draw.polygon(points, fill=colour, outline=colour, width=self.seam)
        return land

    def waves(self) -> None:
        coast = _segments(self.world_map, BorderKind.COAST, self.place)
        wave = _rgb(self.world_map.palette.water_label)
        for line_width, alpha in zip(WAVE_WIDTHS, WAVE_ALPHAS, strict=True):
            mask, draw = self.mask()
            _stroke(draw, coast, max(1, round(line_width * self.scale)), round(FULL * alpha))
            _overlay(self.base, wave, mask)

    def land(self, land: list[int]) -> None:
        cells = self.world_map.cells
        draw = ImageDraw.Draw(self.base)
        light, light_draw = self.mask()
        dark, dark_draw = self.mask()
        for index in land:
            points = self.polygon(index)
            colour = _rgb(_cell_colour(self.world_map, index))
            draw.polygon(points, fill=colour, outline=colour, width=self.seam)
            shade = cells.shade[index] if index < len(cells.shade) else 0.0
            if shade:
                target = light_draw if shade > 0 else dark_draw
                target.polygon(points, fill=min(FULL, round(abs(shade) * FULL)))
        _overlay(self.base, LIGHT, light)
        _overlay(self.base, DARK, dark)

    def fog(self) -> None:
        cells = self.world_map.cells
        fog, draw = self.mask()
        value = round(FULL * FOG_ALPHA)
        for index in range(len(cells.x)):
            if cells.known[index] == KnownState.FOG:
                points = self.polygon(index)
                if len(points) >= 3:
                    draw.polygon(points, fill=value, outline=value, width=self.seam)
        _overlay(self.base, _rgb(self.world_map.palette.background), fog)

    def hachures(self, land: list[int]) -> None:
        cells = self.world_map.cells
        hachure, draw = self.mask()
        width = max(1, round(HACHURE_WIDTH * self.scale))
        for index in land:
            elevation = cells.elevation[index]
            if elevation < HACHURE_MIN:
                continue
            height = HACHURE_BASE + HACHURE_GAIN * elevation
            x, y = cells.x[index], cells.y[index]
            points = [self.place(x - height * 0.7, y + height * 0.4), self.place(x, y - height * 0.6), self.place(x + height * 0.7, y + height * 0.4)]
            draw.line(points, fill=round(FULL * HACHURE_ALPHA), width=width, joint="curve")
        _overlay(self.base, DARK, hachure)

    def encode(self) -> bytes:
        final = self.base.resize((max(1, self.size[0] // TERRAIN_SUPERSAMPLE), max(1, self.size[1] // TERRAIN_SUPERSAMPLE)), Image.Resampling.LANCZOS)
        output = BytesIO()
        final.save(output, format=TERRAIN_FORMAT, quality=TERRAIN_QUALITY, optimize=True)
        return output.getvalue()


def render_terrain(world_map: WorldMap, width: int) -> bytes:
    canvas = Canvas(world_map, width)
    land = canvas.water()
    canvas.waves()
    canvas.land(land)
    canvas.fog()
    canvas.hachures(land)
    return canvas.encode()


def _segments(world_map: WorldMap, kind: BorderKind, place: Callable[[float, float], Point]) -> list[tuple[Point, Point]]:
    coordinates = world_map.borders.coordinates
    found: list[tuple[Point, Point]] = []
    for index, border in enumerate(world_map.borders.kinds):
        if border is not kind:
            continue
        offset = index * 4
        found.append((place(coordinates[offset], coordinates[offset + 1]), place(coordinates[offset + 2], coordinates[offset + 3])))
    return found


def _stroke(draw: ImageDraw.ImageDraw, segments: list[tuple[Point, Point]], width: int, value: int) -> None:
    radius = width / 2
    for start, end in segments:
        draw.line([start, end], fill=value, width=width)
        for x, y in (start, end):
            draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=value)
