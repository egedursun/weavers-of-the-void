from dataclasses import dataclass

from sqlalchemy import select

from aerona.catalog.place_terrain import height_of, kind_spec
from aerona.db.fixups import fixup_due
from aerona.db.tables.cosmos import AppliedFixupRow
from aerona.db.tables.environment import PlaceEnvironmentRow
from aerona.db.tables.place import PlaceProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.environment import PlaceCover, TerrainKind, WaterSource
from aerona.domain.enums.place import PlaceHeight, PlaceKind
from aerona.engine.context import TickContext
from aerona.engine.environment.book import EnvironmentBook
from aerona.engine.environment.places import KindClues, apply_kind, sacred_base, typed_kind
from aerona.engine.primitives.queries import canon

KIND_FIXUP = "places.kind_backfill"
K = PlaceKind


@dataclass(frozen=True)
class OldProfile:
    terrain: TerrainKind | None
    cover: PlaceCover
    water: WaterSource
    height: PlaceHeight
    chokepoint: bool = False


T, C, W, H = TerrainKind, PlaceCover, WaterSource, PlaceHeight
OLD_DEFAULT = OldProfile(None, C.LIGHT, W.NONE, H.FLAT)
OLD_PROFILES: dict[str, OldProfile] = {
    "forest": OldProfile(T.FOREST, C.HEAVY, W.SPRING, H.FLAT),
    "misty grove": OldProfile(T.FOREST, C.HEAVY, W.SPRING, H.FLAT),
    "lake": OldProfile(None, C.OPEN, W.LAKE, H.FLAT),
    "valley": OldProfile(T.RIVER_VALLEY, C.LIGHT, W.RIVER, H.FLAT),
    "river": OldProfile(T.RIVER_VALLEY, C.OPEN, W.RIVER, H.FLAT, True),
    "cave": OldProfile(T.UNDERGROUND, C.HEAVY, W.SPRING, H.LOW, True),
    "marsh": OldProfile(T.MARSH, C.LIGHT, W.LAKE, H.FLAT),
    "pass": OldProfile(T.HIGH_PASS, C.LIGHT, W.NONE, H.HIGH, True),
    "chasm": OldProfile(T.CANYON, C.LIGHT, W.NONE, H.HIGH, True),
    "well": OldProfile(None, C.OPEN, W.WELL, H.FLAT),
    "stone circle": OldProfile(None, C.OPEN, W.NONE, H.LOW),
    "hill": OldProfile(T.HILLS, C.LIGHT, W.NONE, H.HIGH),
    "upland": OldProfile(T.HILLS, C.LIGHT, W.SPRING, H.HIGH),
    "plain": OldProfile(T.PLAIN, C.OPEN, W.NONE, H.FLAT),
    "cove": OldProfile(T.COAST, C.LIGHT, W.SEA, H.LOW),
    "island": OldProfile(T.ISLAND, C.LIGHT, W.SEA, H.LOW),
    "reef": OldProfile(T.COAST, C.OPEN, W.SEA, H.FLAT, True),
    "oasis": OldProfile(T.DESERT, C.LIGHT, W.SPRING, H.FLAT),
    "dune": OldProfile(T.DESERT, C.LIGHT, W.NONE, H.LOW),
    "glacier": OldProfile(T.ICE_SHEET, C.OPEN, W.NONE, H.LOW),
    "hot spring": OldProfile(None, C.OPEN, W.SPRING, H.FLAT),
    "lava lake": OldProfile(T.VOLCANIC, C.OPEN, W.NONE, H.FLAT),
    "ash plain": OldProfile(T.VOLCANIC, C.OPEN, W.NONE, H.FLAT),
}
SUBTYPE_KINDS: dict[str, PlaceKind] = {
    "mountain": K.MOUNTAIN,
    "hill": K.MOUNTAIN,
    "upland": K.MOUNTAIN,
    "peak": K.PEAK,
    "summit": K.PEAK,
    "pass": K.PASS,
    "forest": K.FOREST,
    "wood": K.FOREST,
    "woods": K.FOREST,
    "canopy": K.FOREST,
    "jungle": K.FOREST,
    "grove": K.GROVE,
    "river": K.RIVER,
    "stream": K.RIVER,
    "ford": K.FORD,
    "lake": K.LAKE,
    "pool": K.LAKE,
    "spring": K.SPRING,
    "cave": K.CAVE,
    "grotto": K.CAVE,
    "cavern": K.CAVERN_SYSTEM,
    "caverns": K.CAVERN_SYSTEM,
    "ruin": K.RUIN,
    "ruins": K.RUIN,
    "island": K.ISLAND,
    "isle": K.ISLAND,
    "swamp": K.SWAMP,
    "marsh": K.SWAMP,
    "bog": K.SWAMP,
    "well": K.WELL,
    "valley": K.VALLEY,
    "plain": K.VALLEY,
    "cliff": K.CLIFF,
    "chasm": K.CLIFF,
    "canyon": K.CANYON,
    "gorge": K.CANYON,
    "trench": K.CLIFF,
    "volcano": K.VOLCANO,
    "vent": K.VOLCANO,
    "crater": K.CRATER,
    "dune": K.DUNES,
    "dunes": K.DUNES,
    "reef": K.REEF,
    "glacier": K.GLACIER,
    "oasis": K.OASIS,
    "geyser": K.GEYSER,
    "anomaly": K.ANOMALY,
    "wreck": K.WRECK_SITE,
    "shipwreck": K.WRECK_SITE,
    "debris": K.DEBRIS_FIELD,
    "megastructure": K.MEGASTRUCTURE_RUIN,
    "battlefield": K.BATTLEFIELD,
    "tomb": K.BURIAL_GROUND,
    "barrow": K.BURIAL_GROUND,
    "graveyard": K.BURIAL_GROUND,
    "necropolis": K.BURIAL_GROUND,
    "lair": K.LAIR,
    "den": K.LAIR,
    "hoard": K.LAIR,
    "nexus": K.NEXUS,
    "shrine": K.SHRINE_SITE,
    "altar": K.SHRINE_SITE,
    "circle": K.SHRINE_SITE,
    "mine": K.MINE_SITE,
    "quarry": K.MINE_SITE,
    "harbour": K.HARBOUR_SITE,
    "harbor": K.HARBOUR_SITE,
    "cove": K.HARBOUR_SITE,
    "bay": K.HARBOUR_SITE,
    "crossroads": K.CROSSROADS,
}


def recorded_kind(subtype: str | None) -> PlaceKind | None:
    text = (subtype or "").strip().lower()
    if not text:
        return None
    if text in SUBTYPE_KINDS:
        return SUBTYPE_KINDS[text]
    return next((SUBTYPE_KINDS[word] for word in reversed(text.split()) if word in SUBTYPE_KINDS), None)


def untouched(ground: PlaceEnvironmentRow, subtype: str | None, ctx: TickContext) -> bool:
    old = OLD_PROFILES.get((subtype or "").strip().lower(), OLD_DEFAULT)
    return (
        ground.terrain == old.terrain
        and ground.cover == old.cover
        and ground.water_source == old.water
        and ground.height_advantage == height_of(ctx.rules, old.height)
        and ground.chokepoint == old.chokepoint
    )


def new_profile(ctx: TickContext, place_id: int, kind: PlaceKind) -> PlaceProfileRow:
    return PlaceProfileRow(
        entity_id=place_id, kind=kind, sacredness=sacred_base(ctx.rules, kind_spec(kind).sacred), pilgrims=0, secrets_seeded=False, locked=[]
    )


async def ensure_profiles(ctx: TickContext, book: EnvironmentBook) -> dict[int, PlaceKind]:
    recording = await fixup_due(ctx.session, KIND_FIXUP)
    clues = await KindClues.load(ctx.session)
    known = {row.entity_id: row.kind for row in await ctx.session.scalars(select(PlaceProfileRow))}
    made: dict[int, PlaceKind] = {}
    reshaped = 0
    for place in await canon(ctx.session, [EntityType.PLACE]):
        if place.id in known or held(place.id):
            continue
        ground = book.places.get(place.id)
        region_id = book.atlas.top_region(place.id)
        region = book.regions.get(region_id) if region_id is not None else None
        kind = (recorded_kind(place.subtype) if recording else None) or typed_kind(place, ground, region, clues)
        ctx.session.add(new_profile(ctx, place.id, kind))
        if recording and ground is not None and untouched(ground, place.subtype, ctx) and apply_kind(ctx.rules, ground, kind):
            reshaped += 1
        made[place.id] = kind
    if recording:
        ctx.session.add(AppliedFixupRow(key=KIND_FIXUP, result={"profiles": len(made), "reshaped": reshaped}))
    await ctx.session.flush()
    return made
