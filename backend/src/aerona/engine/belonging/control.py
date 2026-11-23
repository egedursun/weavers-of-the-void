from collections.abc import Mapping
from dataclasses import dataclass

from aerona.core.errors import ValidationFailedError
from aerona.db.base import Base
from aerona.db.tables.belonging import (
    FUGITIVE_FIELDS,
    IDENTITY_FIELDS,
    PEER_GROUP_FIELDS,
    PEER_MEMBER_FIELDS,
    SANCTUARY_FIELDS,
    SANCTUARY_LAW_FIELDS,
    SATIRE_FIELDS,
    FugitiveRow,
    HeldIdentityRow,
    PeerGroupRow,
    PeerMemberRow,
    SanctuaryLawRow,
    SanctuaryRow,
    SatireRow,
)
from aerona.engine.belonging.identities import IdentityTally, keep_identities
from aerona.engine.belonging.peers import PeerTally, keep_peers
from aerona.engine.belonging.sanctuary import SanctuaryTally, keep_sanctuaries
from aerona.engine.belonging.satire import SatireTally, keep_satire
from aerona.engine.collective.control import saved
from aerona.engine.context import TickContext
from aerona.engine.cycles.control import node_exists
from aerona.engine.divine.control import apply
from aerona.engine.gatherings.control import Values, allowed, found


@dataclass(frozen=True)
class Kind:
    table: type[Base]
    fields: tuple[str, ...]
    label: str
    keys: tuple[str, ...]


KINDS: Mapping[str, Kind] = {
    "held_identity": Kind(HeldIdentityRow, IDENTITY_FIELDS, "identity", ("holder_entity_id", "layer")),
    "peer_group": Kind(PeerGroupRow, PEER_GROUP_FIELDS, "peer group", ("id",)),
    "peer_member": Kind(PeerMemberRow, PEER_MEMBER_FIELDS, "member of a peer group", ("group_id", "mortal_entity_id")),
    "fugitive": Kind(FugitiveRow, FUGITIVE_FIELDS, "fugitive", ("id",)),
    "sanctuary": Kind(SanctuaryRow, SANCTUARY_FIELDS, "sanctuary", ("id",)),
    "sanctuary_law": Kind(SanctuaryLawRow, SANCTUARY_LAW_FIELDS, "law of sanctuary", ("polity_entity_id",)),
    "satire": Kind(SatireRow, SATIRE_FIELDS, "satire", ("id",)),
}


async def checked(ctx: TickContext, values: Values) -> None:
    for name, value in values.items():
        if value is not None and isinstance(value, int) and name.endswith(("_node_id", "_entity_id")):
            await node_exists(ctx, value, name.removesuffix("_id").replace("_", " "))
    group = values.get("group_id")
    if isinstance(group, int) and await ctx.session.get(PeerGroupRow, group) is None:
        raise ValidationFailedError("No such peer group.")
    if values.get("fugitive_entity_id") is not None and values.get("fugitive_entity_id") == values.get("host_entity_id"):
        raise ValidationFailedError("A fugitive cannot shelter with itself.")


STAMPS = {"satire": "epoch", "sanctuary": "granted_epoch", "peer_group": "formed_epoch", "peer_member": "joined_epoch", "held_identity": "updated_epoch"}


def key_of(kind: Kind, keys: Values) -> object:
    picked = tuple(keys[name] for name in kind.keys)
    return picked[0] if len(picked) == 1 else picked


async def set_record(ctx: TickContext, name: str, keys: Values, values: Values) -> Base:
    kind = KINDS[name]
    await checked(ctx, {**keys, **values})
    row = await ctx.session.get(kind.table, key_of(kind, keys)) if "id" not in kind.keys else None
    if row is None:
        stamp = {STAMPS[name]: ctx.epoch} if name in STAMPS else {}
        row = await saved(ctx, kind.table(**keys, **values, **stamp, locked=[]))
    else:
        apply(row, allowed(values, kind.fields, kind.label), [])
        await ctx.session.flush()
    return row


async def edit_record(ctx: TickContext, name: str, key: object, values: Values, release: list[str]) -> Base:
    kind = KINDS[name]
    await checked(ctx, values)
    row = apply(await found(ctx, kind.table, key, kind.label), allowed(values, kind.fields, kind.label), release)
    await ctx.session.flush()
    return row


async def delete_record(ctx: TickContext, name: str, key: object) -> None:
    kind = KINDS[name]
    await ctx.session.delete(await found(ctx, kind.table, key, kind.label))
    await ctx.session.flush()


@dataclass
class BelongingRun:
    identities: IdentityTally
    peers: PeerTally


async def run_belonging(ctx: TickContext) -> BelongingRun:
    tally = BelongingRun(IdentityTally(), PeerTally())
    await keep_identities(ctx, tally.identities)
    await keep_peers(ctx, tally.peers)
    return tally


async def run_sanctuary(ctx: TickContext) -> SanctuaryTally:
    tally = SanctuaryTally()
    await keep_sanctuaries(ctx, tally)
    return tally


async def run_satire(ctx: TickContext) -> SatireTally:
    tally = SatireTally()
    await keep_satire(ctx, tally)
    return tally
