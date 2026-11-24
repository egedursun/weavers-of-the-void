from collections import defaultdict
from dataclasses import dataclass, field

from markupsafe import Markup, escape
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.strata import STRATA
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.geology import DeepPassageRow, RegionStratumRow
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.geology import UndergroundStratum
from aerona.engine.primitives.distance import RegionAtlas
from aerona.rules.registry import Rules
from aerona.services.books.mapsvg import MapPicture, build_picture, load_map
from aerona.services.wiki import settlement_tiers


@dataclass(frozen=True)
class DeepRealm:
    cell: str
    holder: str


@dataclass
class DeepStratum:
    stratum: UndergroundStratum
    label: str
    anchor: str
    cells: int
    realms: list[DeepRealm] = field(default_factory=list)
    picture: MapPicture | None = None
    svg: Markup | None = None


def _number(value: float) -> str:
    return f"{value:.2f}".rstrip("0").rstrip(".")


def plate_svg(picture: MapPicture) -> Markup:
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{picture.view_box}" role="img" aria-label="Map">',
        f'<rect x="{_number(picture.x)}" y="{_number(picture.y)}" width="{_number(picture.width)}" height="{_number(picture.height)}" fill="{picture.halo}"/>',
    ]
    for stroke in picture.strokes:
        dash = f' stroke-dasharray="{stroke.dash}"' if stroke.dash else ""
        parts.append(
            f'<path d="{stroke.d}" fill="none" stroke="{stroke.colour}" stroke-width="{_number(stroke.width)}" stroke-opacity="{stroke.opacity}"'
            f' stroke-linecap="round" stroke-linejoin="round"{dash}/>'
        )
    for place in picture.settlements:
        parts.append(f'<circle cx="{_number(place.x)}" cy="{_number(place.y)}" r="{_number(place.radius)}" fill="{picture.ink}"/>')
    for label in picture.labels:
        parts.append(
            f'<text x="{_number(label.x)}" y="{_number(label.y)}" font-size="{_number(label.size)}" text-anchor="{label.anchor}"'
            f' font-family="Georgia, serif" fill="{picture.ink}">{escape(label.text)}</text>'
        )
    parts.append("</svg>")
    return Markup("".join(parts))


async def world_below(session: AsyncSession, rules: Rules, world_id: int, epoch: int, anchor: str) -> list[DeepStratum]:
    regions = select(RegionEnvironmentRow.entity_id).where(RegionEnvironmentRow.world_id == world_id)
    cells = list(await session.scalars(select(RegionStratumRow).where(RegionStratumRow.region_entity_id.in_(regions)).order_by(RegionStratumRow.id)))
    if not cells:
        return []
    names = {
        entity_id: name
        for entity_id, name in await session.execute(
            select(EntityRow.id, EntityRow.name).where(EntityRow.world_id == world_id, EntityRow.status == EntityStatus.CANON)
        )
    }
    atlas = await RegionAtlas.load(session)
    settlements = list(
        await session.scalars(
            select(EntityRow)
            .where(EntityRow.world_id == world_id, EntityRow.status == EntityStatus.CANON, EntityRow.entity_type == EntityType.SETTLEMENT)
            .order_by(EntityRow.id)
        )
    )
    by_level: dict[UndergroundStratum, list[int]] = defaultdict(list)
    for settlement in settlements:
        level = atlas.level_of(settlement.id)
        if level is not None:
            by_level[level].append(settlement.id)
    passages = list(await session.scalars(select(DeepPassageRow).where(DeepPassageRow.world_id == world_id).order_by(DeepPassageRow.id)))
    loaded = await load_map(session, world_id)
    tiers = {entity_id: info.tier.value for entity_id, info in (await settlement_tiers(session, rules, world_id, epoch)).items()}
    found: list[DeepStratum] = []
    for stratum in STRATA:
        level_cells = [cell for cell in cells if cell.stratum is stratum]
        if not level_cells:
            continue
        label = STRATA[stratum].label
        realms = [
            DeepRealm(cell.name or f"{label} beneath {names.get(cell.region_entity_id, 'a region')}", names[cell.realm_entity_id])
            for cell in level_cells
            if cell.realm_entity_id is not None and cell.realm_entity_id in names
        ]
        entry = DeepStratum(stratum, label, f"{anchor}-{stratum.value}", len(level_cells), realms)
        if by_level.get(stratum) and loaded is not None:
            world_map, signature = loaded
            centres = {region.id: region.centroid for region in world_map.regions if region.centroid is not None}
            held = {cell.region_entity_id for cell in level_cells}
            ways = [
                [*centres[row.first_region_entity_id], *centres[row.second_region_entity_id]]
                for row in passages
                if row.first_stratum is stratum
                and row.second_stratum is stratum
                and row.first_region_entity_id in centres
                and row.second_region_entity_id in centres
            ]
            entry.picture = build_picture(
                world_map,
                world_id=world_id,
                signature=f"{signature}-{stratum.value}",
                names={key: value for key, value in names.items() if key in held or key in by_level[stratum]},
                tiers={key: value for key, value in tiers.items() if key in by_level[stratum]},
                roads=ways,
            )
            entry.svg = plate_svg(entry.picture) if entry.picture is not None else None
        found.append(entry)
    return found
