from collections.abc import Mapping
from dataclasses import dataclass, field

from sqlalchemy import select

from aerona.core.errors import ValidationFailedError
from aerona.core.grammar import an
from aerona.db.base import Base
from aerona.db.tables.culture import BookContentRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.means import (
    CONTAINER_FIELDS,
    NAVIGATION_FIELDS,
    SECURITY_FIELDS,
    WATER_LIFT_FIELDS,
    WRITING_CUSTOM_FIELDS,
    WRITTEN_FIELDS,
    ContainerStockRow,
    NavigationKitRow,
    SecurityRow,
    WaterLiftRow,
    WritingCustomRow,
    WrittenWorkRow,
)
from aerona.domain.enums.entity import EntityType
from aerona.engine.collective.control import saved
from aerona.engine.context import TickContext
from aerona.engine.cycles.control import node_exists
from aerona.engine.divine.control import apply
from aerona.engine.gatherings.control import Values, allowed, found
from aerona.engine.means.containers import ContainerTally, keep_containers
from aerona.engine.means.media import MediaTally, keep_media
from aerona.engine.means.navigation import NavigationTally, keep_navigation
from aerona.engine.means.security import SecurityTally, keep_security
from aerona.engine.means.water import WaterTally, build_lifts


@dataclass(frozen=True)
class Kind:
    table: type[Base]
    fields: tuple[str, ...]
    label: str
    keys: tuple[str, ...]
    holder: str
    holders: frozenset[EntityType] | None


SETTLEMENTS = frozenset({EntityType.SETTLEMENT})
KINDS: Mapping[str, Kind] = {
    "writing_custom": Kind(
        WritingCustomRow, WRITING_CUSTOM_FIELDS, "custom of writing", ("people_entity_id",), "people_entity_id", frozenset({EntityType.PEOPLE})
    ),
    "written_work": Kind(WrittenWorkRow, WRITTEN_FIELDS, "written work", ("work_entity_id",), "work_entity_id", None),
    "security": Kind(SecurityRow, SECURITY_FIELDS, "vault", ("holder_entity_id",), "holder_entity_id", None),
    "water_lift": Kind(WaterLiftRow, WATER_LIFT_FIELDS, "water-lifting device", ("settlement_entity_id", "device"), "settlement_entity_id", SETTLEMENTS),
    "navigation_kit": Kind(NavigationKitRow, NAVIGATION_FIELDS, "navigation instrument", ("holder_entity_id", "aid"), "holder_entity_id", SETTLEMENTS),
    "container_stock": Kind(ContainerStockRow, CONTAINER_FIELDS, "stock of containers", ("community_entity_id", "kind"), "community_entity_id", SETTLEMENTS),
}
STAMPS = {
    "writing_custom": "since_epoch",
    "written_work": "written_epoch",
    "security": "since_epoch",
    "water_lift": "since_epoch",
    "navigation_kit": "since_epoch",
}


async def checked(ctx: TickContext, kind: Kind, values: Values) -> None:
    holder = values.get(kind.holder)
    if isinstance(holder, int):
        await node_exists(ctx, holder, kind.label)
        entity = await ctx.session.get(EntityRow, holder)
        if kind.holders is not None and (entity is None or entity.entity_type not in kind.holders):
            raise ValidationFailedError(f"{an(kind.label, capital=True)} is held by {' or '.join(sorted(item.value for item in kind.holders))}.")
    written = (
        await ctx.session.scalar(select(BookContentRow.book_entity_id).where(BookContentRow.book_entity_id == holder).limit(1))
        if isinstance(holder, int)
        else None
    )
    if kind.table is WrittenWorkRow and isinstance(holder, int) and written is None:
        raise ValidationFailedError("Only a written work keeps a medium of writing.")


def key_of(kind: Kind, keys: Values) -> object:
    picked = tuple(keys[name] for name in kind.keys)
    return picked[0] if len(picked) == 1 else picked


async def set_record(ctx: TickContext, name: str, keys: Values, values: Values) -> Base:
    kind = KINDS[name]
    await checked(ctx, kind, {**keys, **values})
    row = await ctx.session.get(kind.table, key_of(kind, keys))
    if row is None:
        stamp = {STAMPS[name]: ctx.epoch} if name in STAMPS else {}
        row = await saved(ctx, kind.table(**keys, **values, **stamp, locked=[]))
    else:
        apply(row, allowed(values, kind.fields, kind.label), [])
        await ctx.session.flush()
    return row


async def edit_record(ctx: TickContext, name: str, key: object, values: Values, release: list[str]) -> Base:
    kind = KINDS[name]
    row = apply(await found(ctx, kind.table, key, kind.label), allowed(values, kind.fields, kind.label), release)
    await ctx.session.flush()
    return row


async def delete_record(ctx: TickContext, name: str, key: object) -> None:
    kind = KINDS[name]
    await ctx.session.delete(await found(ctx, kind.table, key, kind.label))
    await ctx.session.flush()


@dataclass
class MeansRun:
    media: MediaTally = field(default_factory=MediaTally)
    security: SecurityTally = field(default_factory=SecurityTally)
    water: WaterTally = field(default_factory=WaterTally)
    navigation: NavigationTally = field(default_factory=NavigationTally)
    containers: ContainerTally = field(default_factory=ContainerTally)


async def run_means(ctx: TickContext) -> MeansRun:
    tally = MeansRun()
    await keep_media(ctx, tally.media)
    await keep_security(ctx, tally.security)
    await build_lifts(ctx, tally.water)
    await keep_navigation(ctx, tally.navigation)
    await keep_containers(ctx, tally.containers)
    return tally
