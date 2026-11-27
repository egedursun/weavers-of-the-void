from collections import Counter
from typing import Any

from sqlalchemy import select

from aerona.catalog.life_traits import PACKAGE_KIND_TRAITS, having
from aerona.constants.units import PERCENT
from aerona.db.tables.afflictions import AfflictionRow
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.ecology import BeastProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.foreign_gods import ForeignGodRow
from aerona.db.tables.sons import SonRow
from aerona.db.tables.transform import TransformationRow
from aerona.db.types import PydanticJSON
from aerona.domain.enums.affliction import Transmission
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.domain import Domain
from aerona.domain.enums.entity import COMMUNITY_TYPES, EntityStatus, EntityType, MortalRole
from aerona.domain.enums.life_traits import PackageKindTrait
from aerona.domain.enums.transform import TransformKind, TransformState
from aerona.domain.models.entity_stats import BeastStats, MortalStats
from aerona.engine.body.agelessness import spec_of
from aerona.engine.context import TickContext
from aerona.engine.cosmos.foreign_gods import NewForeignGod, add_foreign_god
from aerona.engine.ecology.beasts import profile_beast
from aerona.engine.primitives.queries import canon
from aerona.engine.primitives.stats import stat
from aerona.engine.transform.ledger import Ledger
from aerona.engine.transform.moves import bind, end, move_bonds

BEAST_CURSES = having(PACKAGE_KIND_TRAITS, PackageKindTrait.BEAST_CURSES)


async def worshipping(ctx: TickContext, node_id: int) -> list[int]:
    statement = (
        select(BondRow.source_node_id)
        .join(EntityRow, EntityRow.id == BondRow.source_node_id)
        .where(
            BondRow.target_node_id == node_id,
            BondRow.kind == BondKind.WORSHIPS,
            BondRow.state == BondState.ACTIVE,
            EntityRow.status == EntityStatus.CANON,
            EntityRow.entity_type.in_(COMMUNITY_TYPES),
        )
    )
    return sorted(set(await ctx.session.scalars(statement)))


async def local_god_pressures(ctx: TickContext) -> dict[int, int]:
    need = ctx.rules.transform.local_god_worshippers
    found: dict[int, int] = {}
    for spirit in await canon(ctx.session, [EntityType.SPIRIT]):
        if len(await worshipping(ctx, spirit.id)) >= need:
            found[spirit.id] = PERCENT
    return found


async def spirit_check(ctx: TickContext, spirit_id: int) -> str | None:
    spirit = await ctx.session.get(EntityRow, spirit_id)
    if spirit is None or spirit.entity_type is not EntityType.SPIRIT or spirit.status is not EntityStatus.CANON:
        return "Only a living spirit can be raised to a local god."
    if spirit.world_id is None:
        return f"{spirit.name} is on no world."
    return None


async def patron_domain(ctx: TickContext, communities: list[int]) -> Domain | None:
    patrons: Counter[Domain] = Counter()
    for bond in await ctx.session.scalars(
        select(BondRow).where(BondRow.source_node_id.in_(communities), BondRow.kind == BondKind.WORSHIPS, BondRow.state == BondState.ACTIVE)
    ):
        son = await ctx.session.get(SonRow, bond.target_node_id)
        god = await ctx.session.get(ForeignGodRow, bond.target_node_id) if son is None else None
        domain = son.domain_primary if son is not None else god.domain_primary if god is not None else None
        if domain is not None:
            patrons[domain] += 1
    return patrons.most_common(1)[0][0] if patrons else None


async def raise_spirit(ctx: TickContext, spirit_id: int, ledger: Ledger) -> int:
    spirit = await ctx.session.get_one(EntityRow, spirit_id)
    communities = await worshipping(ctx, spirit.id)
    domain = spirit.domain or await patron_domain(ctx, communities) or Domain.MEMORY
    god = await add_foreign_god(
        ctx.session,
        ctx.rules,
        ctx.rng(f"local_god.{spirit.id}"),
        ctx.epoch,
        NewForeignGod(
            name=spirit.name, world_id=spirit.world_id or 0, domains=(domain, None), description=f"The spirit {spirit.name}, worshipped into a local god."
        ),
    )
    ledger.made(god.id)
    await move_bonds(ctx, ledger, spirit.id, god.id, kinds=(BondKind.WORSHIPS,), reason=f"worship of the spirit {spirit.name} given to the god it became")
    await bind(ctx, ledger, (god.id, spirit.id, BondKind.DESCENDS_FROM), f"the spirit {spirit.name} before it was a god")
    end(ctx, ledger, spirit, EntityStatus.DESTROYED)
    return god.id


async def cursed(ctx: TickContext, entity_id: int) -> bool:
    statement = select(AfflictionRow).where(
        AfflictionRow.bearer_node_id == entity_id,
        AfflictionRow.cured_epoch.is_(None),
        AfflictionRow.transmission == Transmission.CURSE,
        AfflictionRow.package.in_(tuple(BEAST_CURSES)),
    )
    return any(row.stage >= len(spec_of(row).stages) for row in await ctx.session.scalars(statement))


async def beast_curse_pressures(ctx: TickContext) -> dict[int, int]:
    found: dict[int, int] = {}
    for mortal in await canon(ctx.session, [EntityType.MORTAL]):
        if await cursed(ctx, mortal.id):
            found[mortal.id] = PERCENT
    return found


async def mortal_check(ctx: TickContext, mortal_id: int) -> str | None:
    mortal = await ctx.session.get(EntityRow, mortal_id)
    if mortal is None or mortal.entity_type is not EntityType.MORTAL or mortal.status is not EntityStatus.CANON:
        return "Only a living mortal can be cursed into a beast."
    return None


async def curse_into_beast(ctx: TickContext, mortal_id: int, ledger: Ledger) -> int:
    mortal = await ctx.session.get_one(EntityRow, mortal_id)
    stats = BeastStats(
        hp=stat(mortal, "hp"),
        strength=stat(mortal, "strength"),
        agility=stat(mortal, "agility"),
        cunning=stat(mortal, "intellect"),
        danger=PERCENT // 2,
    )
    ledger.retype(mortal, EntityType.BEAST)
    ledger.set(mortal, "stats", stats)
    if await ctx.session.get(BeastProfileRow, mortal.id) is None:
        profile = await profile_beast(ctx, mortal, None)
        ledger.added(profile)
    return mortal.id


async def once_mortal(ctx: TickContext, beast_id: int) -> TransformationRow | None:
    statement = (
        select(TransformationRow)
        .where(
            TransformationRow.kind == TransformKind.BEAST_CURSE, TransformationRow.result_node_id == beast_id, TransformationRow.state == TransformState.DONE
        )
        .order_by(TransformationRow.id.desc())
        .limit(1)
    )
    return await ctx.session.scalar(statement)


async def curse_lifted_pressures(ctx: TickContext) -> dict[int, int]:
    found: dict[int, int] = {}
    for beast in await canon(ctx.session, [EntityType.BEAST]):
        if await once_mortal(ctx, beast.id) is not None and not await cursed(ctx, beast.id):
            found[beast.id] = PERCENT
    return found


async def lifted_check(ctx: TickContext, beast_id: int) -> str | None:
    beast = await ctx.session.get(EntityRow, beast_id)
    if beast is None or beast.entity_type is not EntityType.BEAST or beast.status is not EntityStatus.CANON:
        return "Only a living beast can have its curse lifted."
    if await once_mortal(ctx, beast.id) is None:
        return f"{beast.name} was never a mortal."
    return None


def former_stats(row: TransformationRow | None) -> Any:
    column = EntityRow.__table__.c["stats"].type
    if row is None or not isinstance(column, PydanticJSON):
        return MortalStats()
    for step in row.undo:
        if step.get("column") == "stats" and step.get("before") is not None:
            return column.adapter.validate_python(step["before"])
    return MortalStats()


def former_role(row: TransformationRow | None) -> MortalRole | None:
    for step in row.undo if row is not None else []:
        if step.get("column") == "mortal_role" and step.get("before") is not None:
            return MortalRole(step["before"])
    return None


async def lift_curse(ctx: TickContext, beast_id: int, ledger: Ledger) -> int:
    beast = await ctx.session.get_one(EntityRow, beast_id)
    once = await once_mortal(ctx, beast.id)
    ledger.retype(beast, EntityType.MORTAL)
    ledger.set(beast, "stats", former_stats(once))
    role = former_role(once)
    if role is not None:
        ledger.set(beast, "mortal_role", role)
    return beast.id
