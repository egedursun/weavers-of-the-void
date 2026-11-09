import asyncio
import hashlib
import re
import secrets
import time
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from io import BytesIO
from typing import Any

from PIL import Image
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import InstrumentedAttribute

from aerona.catalog.image_styles import style_signature
from aerona.constants.imaging import IN_CLAUSE_CHUNK, PNG_SIGNATURE
from aerona.constants.schema import TITLE_MAX_LENGTH
from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.db.repositories.nodes import NodeRepository
from aerona.db.tables.celestial import StarRow, WorldRow
from aerona.db.tables.cosmography import ClusterRow, DimensionRow, GalaxyRow
from aerona.db.tables.cosmos import CosmosRow, CreatorRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.foreign_gods import ForeignGodRow
from aerona.db.tables.meta import ImageRow
from aerona.db.tables.node import NodeRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.meta import ImageMime, ImageOrigin
from aerona.domain.enums.node import NodeKind
from aerona.domain.enums.world import ImageStyle
from aerona.media.keys import original_key
from aerona.media.store import MediaStore
from aerona.services.images.collection import MediaCollector

UPLOAD_MAX_BYTES = 30 * 1024 * 1024
CAPTION_MAX_LENGTH = min(120, TITLE_MAX_LENGTH)
RANDOM_HEX_BYTES = 3
FILE_NAME_ONLY = re.compile(r"^[\w.-]+\.(?:png|jpe?g|webp|gif|avif)$", re.IGNORECASE)
MAGIC: dict[ImageMime, tuple[bytes, ...]] = {
    ImageMime.PNG: (PNG_SIGNATURE,),
    ImageMime.JPEG: (b"\xff\xd8\xff",),
    ImageMime.WEBP: (b"RIFF",),
}
EXTENSIONS: dict[ImageMime, str] = {ImageMime.PNG: ".png", ImageMime.JPEG: ".jpg", ImageMime.WEBP: ".webp"}
WEBP_MARK = b"WEBP"
WEBP_MARK_OFFSET = 8
KIND_PREFIX: dict[NodeKind, str] = {
    NodeKind.CREATOR: "creator",
    NodeKind.SON: "son",
    NodeKind.FOREIGN_GOD: "god",
    NodeKind.WORLD: "world",
    NodeKind.STAR: "star",
    NodeKind.GALAXY: "galaxy",
    NodeKind.CLUSTER: "cluster",
    NodeKind.DIMENSION: "dimension",
    NodeKind.ENTITY: "entity",
}
TARGET_ORDER: tuple[NodeKind, ...] = (
    NodeKind.CREATOR,
    NodeKind.SON,
    NodeKind.FOREIGN_GOD,
    NodeKind.DIMENSION,
    NodeKind.CLUSTER,
    NodeKind.GALAXY,
    NodeKind.WORLD,
    NodeKind.STAR,
    NodeKind.ENTITY,
)
PROMPT_TABLES: dict[NodeKind, type[NodeRow]] = {
    NodeKind.CREATOR: CreatorRow,
    NodeKind.SON: SonRow,
    NodeKind.FOREIGN_GOD: ForeignGodRow,
    NodeKind.WORLD: WorldRow,
    NodeKind.STAR: StarRow,
    NodeKind.GALAXY: GalaxyRow,
    NodeKind.CLUSTER: ClusterRow,
    NodeKind.DIMENSION: DimensionRow,
    NodeKind.ENTITY: EntityRow,
}
PROMPT_COLUMNS: dict[NodeKind, InstrumentedAttribute[str | None]] = {
    NodeKind.CREATOR: CreatorRow.image_prompt,
    NodeKind.SON: SonRow.image_prompt,
    NodeKind.FOREIGN_GOD: ForeignGodRow.image_prompt,
    NodeKind.WORLD: WorldRow.image_prompt,
    NodeKind.STAR: StarRow.image_prompt,
    NodeKind.GALAXY: GalaxyRow.image_prompt,
    NodeKind.CLUSTER: ClusterRow.image_prompt,
    NodeKind.DIMENSION: DimensionRow.image_prompt,
    NodeKind.ENTITY: EntityRow.image_prompt,
}


@dataclass(frozen=True)
class ImageTarget:
    node_id: int
    kind: NodeKind
    name: str
    image_prompt: str | None


@dataclass(frozen=True)
class ImageListItem:
    image: ImageRow
    target_name: str | None
    target_kind: NodeKind | None
    target_world_id: int | None
    target_type: EntityType | None = None
    target_importance: int | None = None


def caption_valid(caption: str | None) -> bool:
    return bool(caption and caption.strip() and not FILE_NAME_ONLY.match(caption.strip()))


def detect_mime(data: bytes, declared: ImageMime) -> bool:
    if not any(data.startswith(magic) for magic in MAGIC[declared]):
        return False
    return declared is not ImageMime.WEBP or data[WEBP_MARK_OFFSET : WEBP_MARK_OFFSET + len(WEBP_MARK)] == WEBP_MARK


def new_file_name(kind: NodeKind, node_id: int, mime: ImageMime) -> str:
    return f"{KIND_PREFIX[kind]}{node_id}-{int(time.time() * 1000)}-{secrets.token_hex(RANDOM_HEX_BYTES)}{EXTENSIONS[mime]}"


async def resolve_target(session: AsyncSession, node_id: int) -> ImageTarget:
    kind = await NodeRepository(session).kind_of(node_id)
    if kind is None:
        raise NotFoundError("No such image target.")
    row = await session.get(PROMPT_TABLES[kind], node_id)
    if row is None:
        raise NotFoundError("No such image target.")
    return ImageTarget(node_id=node_id, kind=kind, name=row.name, image_prompt=getattr(row, "image_prompt", None))


async def cover_of(session: AsyncSession, node_id: int) -> str | None:
    statement = select(ImageRow.file_name).where(ImageRow.target_node_id == node_id).order_by(ImageRow.is_cover.desc(), ImageRow.id.desc()).limit(1)
    file_name: str | None = await session.scalar(statement)
    return file_name


async def all_covers(session: AsyncSession) -> dict[int, str]:
    statement = (
        select(ImageRow.target_node_id, ImageRow.file_name)
        .where(ImageRow.target_node_id.is_not(None))
        .order_by(ImageRow.target_node_id, ImageRow.is_cover.desc(), ImageRow.id.desc())
    )
    covers: dict[int, str] = {}
    for node_id, file_name in await session.execute(statement):
        covers.setdefault(node_id, file_name)
    return covers


async def covers_of(session: AsyncSession, node_ids: Iterable[int]) -> dict[int, str]:
    wanted = set(node_ids)
    if not wanted:
        return {}
    statement = (
        select(ImageRow.target_node_id, ImageRow.file_name)
        .where(ImageRow.target_node_id.in_(wanted))
        .order_by(ImageRow.target_node_id, ImageRow.is_cover.desc(), ImageRow.id.desc())
    )
    covers: dict[int, str] = {}
    for node_id, file_name in await session.execute(statement):
        covers.setdefault(node_id, file_name)
    return covers


async def image_by_file_name(session: AsyncSession, file_name: str) -> ImageRow | None:
    image: ImageRow | None = await session.scalar(select(ImageRow).where(ImageRow.file_name == file_name).limit(1))
    return image


async def has_image(session: AsyncSession, node_id: int) -> bool:
    return await session.scalar(select(ImageRow.id).where(ImageRow.target_node_id == node_id).limit(1)) is not None


@dataclass(frozen=True)
class WorldStyle:
    style: ImageStyle
    custom: str

    @property
    def signature(self) -> str:
        return style_signature(self.style, self.custom)


async def world_style(session: AsyncSession) -> WorldStyle:
    cosmos = await session.scalar(select(CosmosRow).limit(1))
    if cosmos is None:
        return WorldStyle(ImageStyle.PHOTOREAL, "")
    return WorldStyle(cosmos.image_style, cosmos.image_style_custom)


async def _targets_among(session: AsyncSession, condition: Callable[[Any], Any], limit: int | None = None) -> list[ImageTarget]:
    found: list[ImageTarget] = []
    for kind in TARGET_ORDER:
        table = PROMPT_TABLES[kind]
        statement = select(table).where(condition(table.id))
        if kind is NodeKind.ENTITY:
            statement = statement.where(EntityRow.status == EntityStatus.CANON).order_by(func.coalesce(EntityRow.importance, 0).desc(), EntityRow.id)
        else:
            statement = statement.order_by(table.id)
        for row in await session.scalars(statement):
            found.append(ImageTarget(row.id, kind, row.name, getattr(row, "image_prompt", None)))
            if limit is not None and len(found) >= limit:
                return found
    return found


async def missing_targets(session: AsyncSession, limit: int | None = None) -> list[ImageTarget]:
    with_image = select(ImageRow.target_node_id)
    return await _targets_among(session, lambda column: column.not_in(with_image), limit)


async def off_style_covers(session: AsyncSession, signature: str) -> set[int]:
    statement = (
        select(ImageRow.target_node_id, ImageRow.origin, ImageRow.style)
        .where(ImageRow.target_node_id.is_not(None))
        .order_by(ImageRow.target_node_id, ImageRow.is_cover.desc(), ImageRow.id.desc())
    )
    covers: dict[int, bool] = {}
    for node_id, origin, style in await session.execute(statement):
        covers.setdefault(node_id, origin is ImageOrigin.GENERATED and (style or ImageStyle.PHOTOREAL.value) != signature)
    return {node_id for node_id, off in covers.items() if off}


async def restyle_targets(session: AsyncSession, signature: str) -> list[ImageTarget]:
    off = await off_style_covers(session, signature)
    if not off:
        return []
    return [target for target in await _targets_among(session, lambda column: column.in_(off)) if target.image_prompt]


async def cover_in_style(session: AsyncSession, node_id: int, signature: str) -> bool:
    return node_id not in await off_style_covers(session, signature) and await has_image(session, node_id)


async def missing_count(session: AsyncSession) -> int:
    return len(await missing_targets(session))


class ImageRecords:
    def __init__(self, collector: MediaCollector) -> None:
        self._collector = collector

    @property
    def store(self) -> MediaStore:
        return self._collector.store

    async def _store(
        self,
        session: AsyncSession,
        target: ImageTarget,
        data: bytes,
        mime: ImageMime,
        *,
        origin: ImageOrigin,
        caption: str | None,
        prompt: str | None,
        style: str | None = None,
        cover: bool = False,
    ) -> ImageRow:
        digest = hashlib.sha256(data).hexdigest()
        duplicate = await session.scalar(select(ImageRow).where(ImageRow.target_node_id == target.node_id, ImageRow.sha256 == digest).limit(1))
        if duplicate is not None and await self.store.exists(duplicate.object_key):
            return duplicate
        name = new_file_name(target.kind, target.node_id, mime)
        shared = await session.scalar(select(ImageRow.object_key).where(ImageRow.sha256 == digest).limit(1))
        key = shared if shared is not None and await self.store.exists(shared) else original_key(name)
        if key != shared:
            await self.store.put(key, data)
        width, height = await asyncio.to_thread(_dimensions, data)
        first = not await has_image(session, target.node_id)
        if cover and not first:
            await session.execute(update(ImageRow).where(ImageRow.target_node_id == target.node_id).values(is_cover=False))
        row = ImageRow(
            target_node_id=target.node_id,
            file_name=name,
            object_key=key,
            sha256=digest,
            mime=mime,
            origin=origin,
            caption=caption.strip()[:CAPTION_MAX_LENGTH] if caption_valid(caption) and caption else None,
            prompt=prompt,
            style=style,
            is_cover=first or cover,
            size_bytes=len(data),
            width=width,
            height=height,
        )
        session.add(row)
        await session.flush()
        return row

    async def add_generated(
        self, session: AsyncSession, node_id: int, png: bytes, prompt: str | None, *, style: str | None = None, cover: bool = False
    ) -> ImageRow | None:
        kind = await NodeRepository(session).kind_of(node_id)
        if kind is None or not png.startswith(PNG_SIGNATURE):
            return None
        target = await resolve_target(session, node_id)
        return await self._store(session, target, png, ImageMime.PNG, origin=ImageOrigin.GENERATED, caption=None, prompt=prompt, style=style, cover=cover)

    async def upload(self, session: AsyncSession, node_id: int, data: bytes, mime: ImageMime, caption: str | None = None) -> ImageRow:
        target = await resolve_target(session, node_id)
        if not data:
            raise ValidationFailedError("The image is empty.")
        if len(data) > UPLOAD_MAX_BYTES:
            raise ValidationFailedError("The image is too large.")
        if not detect_mime(data, mime):
            raise ValidationFailedError("The file content does not match its image type.")
        return await self._store(session, target, data, mime, origin=ImageOrigin.UPLOADED, caption=caption, prompt=None)

    async def set_cover(self, session: AsyncSession, image_id: int) -> ImageRow:
        image = await _require(session, image_id)
        await session.execute(update(ImageRow).where(ImageRow.target_node_id == image.target_node_id, ImageRow.id != image.id).values(is_cover=False))
        image.is_cover = True
        await session.flush()
        return image

    async def set_caption(self, session: AsyncSession, image_id: int, caption: str | None) -> ImageRow:
        image = await _require(session, image_id)
        if caption and not caption_valid(caption):
            raise ValidationFailedError("A caption cannot be just a file name.")
        image.caption = caption.strip()[:CAPTION_MAX_LENGTH] if caption else None
        await session.flush()
        return image

    async def delete(self, session: AsyncSession, image_id: int) -> str:
        image = await _require(session, image_id)
        target, key, was_cover = image.target_node_id, image.object_key, image.is_cover
        await session.delete(image)
        await session.flush()
        if was_cover:
            newest = await session.scalar(select(ImageRow).where(ImageRow.target_node_id == target).order_by(ImageRow.id.desc()).limit(1))
            if newest is not None:
                newest.is_cover = True
                await session.flush()
        return key

    async def release(self, keys: Iterable[str]) -> int:
        return await self._collector.collect(keys)


async def _require(session: AsyncSession, image_id: int) -> ImageRow:
    image = await session.get(ImageRow, image_id)
    if image is None:
        raise NotFoundError("No such image.")
    return image


def _dimensions(data: bytes) -> tuple[int | None, int | None]:
    try:
        with Image.open(BytesIO(data)) as image:
            return image.width, image.height
    except (OSError, ValueError):
        return None, None


async def list_images(session: AsyncSession, node_id: int | None = None) -> list[ImageListItem]:
    statement = select(ImageRow)
    if node_id is not None:
        statement = statement.where(ImageRow.target_node_id == node_id).order_by(ImageRow.is_cover.desc(), ImageRow.id.desc())
    else:
        statement = statement.order_by(ImageRow.id.desc())
    images = list(await session.scalars(statement))
    ids = sorted({image.target_node_id for image in images})
    nodes = NodeRepository(session)
    names = await nodes.names_of(ids)
    kinds = await nodes.kinds_of(ids)
    worlds: dict[int, int | None] = {}
    types: dict[int, EntityType] = {}
    importance: dict[int, int | None] = {}
    for chunk in _chunks(ids):
        for god_id, world_id in await session.execute(select(ForeignGodRow.id, ForeignGodRow.world_id).where(ForeignGodRow.id.in_(chunk))):
            worlds[god_id] = world_id
        for son_id, son_world in await session.execute(select(SonRow.id, SonRow.current_world_id).where(SonRow.id.in_(chunk))):
            worlds[son_id] = son_world
        for own_id in await session.scalars(select(WorldRow.id).where(WorldRow.id.in_(chunk))):
            worlds[own_id] = own_id
        rows = await session.execute(select(EntityRow.id, EntityRow.world_id, EntityRow.entity_type, EntityRow.importance).where(EntityRow.id.in_(chunk)))
        for entity_id, entity_world, entity_type, rank in rows:
            worlds[entity_id] = entity_world
            types[entity_id] = entity_type
            importance[entity_id] = rank
    return [
        ImageListItem(
            image,
            names.get(image.target_node_id),
            kinds.get(image.target_node_id),
            worlds.get(image.target_node_id),
            types.get(image.target_node_id),
            importance.get(image.target_node_id),
        )
        for image in images
    ]


def _chunks(ids: list[int]) -> list[list[int]]:
    return [ids[start : start + IN_CLAUSE_CHUNK] for start in range(0, len(ids), IN_CLAUSE_CHUNK)]


async def clear_file_name_captions(session: AsyncSession) -> int:
    cleared = 0
    for image in await session.scalars(select(ImageRow).where(ImageRow.caption.is_not(None))):
        if not caption_valid(image.caption):
            image.caption = None
            cleared += 1
    await session.flush()
    return cleared


async def missing_prompt_targets(session: AsyncSession, limit: int) -> list[ImageTarget]:
    found: list[ImageTarget] = []
    for kind in TARGET_ORDER:
        table = PROMPT_TABLES[kind]
        statement = select(table).where(PROMPT_COLUMNS[kind].is_(None))
        if kind is NodeKind.ENTITY:
            statement = statement.where(EntityRow.status == EntityStatus.CANON).order_by(func.coalesce(EntityRow.importance, 0).desc(), EntityRow.id)
        for row in await session.scalars(statement.limit(limit)):
            found.append(ImageTarget(row.id, kind, row.name, None))
            if len(found) >= limit:
                return found
    return found
