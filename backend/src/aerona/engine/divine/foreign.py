from sqlalchemy import select

from aerona.catalog.tenets import DOMAIN_JUDGEMENT, DOMAIN_TENETS, OPPOSED
from aerona.constants.units import PERCENT
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.faith import CultDoctrineRow, CultTenetRow
from aerona.db.tables.foreign_gods import ForeignGodRow
from aerona.db.tables.polity import TreatyPartyRow, TreatyProfileRow
from aerona.db.tables.sons import SonRow
from aerona.db.write_guard import held
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.faith import JudgementDoctrine, TenetKind
from aerona.domain.enums.foreign_god import ForeignGodStatus
from aerona.domain.enums.polity import PartyRole, TreatyKind, TreatyStatus
from aerona.domain.enums.son import SonStatus
from aerona.domain.models.entity_stats import CultStats
from aerona.engine.context import TickContext
from aerona.engine.divine.gods import God, domains_of, living_gods
from aerona.engine.notes import note
from aerona.engine.polity.accords import sign
from aerona.engine.primitives.queries import active_bonds, connect
from aerona.engine.primitives.records import RecordSpec, open_record
from aerona.engine.relations.book import ensure_relation, relation, shift

OLD_FAITH = "old_faith"


def world_of(god: God) -> int | None:
    return god.current_world_id if isinstance(god, SonRow) else god.world_id


async def regard(ctx: TickContext, holder: ForeignGodRow, other: God) -> int:
    table = ctx.rules.god_relations
    change = 0
    shared = len(set(domains_of(holder)) & set(domains_of(other)))
    change -= shared * table.shared_domain
    if isinstance(other, SonRow):
        change += round(holder.stance * table.stance_pct / PERCENT)
    elif other.stance < 0 and holder.stance < 0:
        change += table.common_cause
    if world_of(other) == holder.world_id:
        change += table.neighbour if change >= 0 else -table.neighbour
    return change


async def god_opinions(ctx: TickContext) -> int:
    gods = await living_gods(ctx.session)
    foreign = [god for god in gods if isinstance(god, ForeignGodRow) and god.status is not ForeignGodStatus.DEAD]
    moved = 0
    for holder in foreign:
        if held(holder.id):
            continue
        for other in gods:
            if other.id == holder.id:
                continue
            row = await ensure_relation(ctx.session, holder.id, other.id, ctx.epoch)
            if row is None:
                continue
            shift(ctx.rules, row, ctx.epoch, friendship=await regard(ctx, holder, other))
            moved += 1
    return moved


async def friendship(ctx: TickContext, holder_id: int, other_id: int) -> int:
    row = await relation(ctx.session, holder_id, other_id)
    return row.friendship if row is not None else 0


async def pantheon_leagues(ctx: TickContext) -> int:
    table = ctx.rules.god_relations
    foreign = [
        god
        for god in await ctx.session.scalars(select(ForeignGodRow).where(ForeignGodRow.status == ForeignGodStatus.AWAKE).order_by(ForeignGodRow.id))
        if god.stance <= -table.league_stance
    ]
    joined = 0
    for index, first in enumerate(foreign):
        for second in foreign[index + 1 :]:
            if held(first.id, second.id):
                continue
            warm = min(await friendship(ctx, first.id, second.id), await friendship(ctx, second.id, first.id))
            if warm < table.league_friendship or await active_bonds(ctx.session, [BondKind.ALLY], sources=[first.id], targets=[second.id]):
                continue
            await connect(ctx.session, first.id, second.id, BondKind.ALLY, ctx.epoch, description="leagued against the pantheon")
            await note(
                ctx,
                f"The foreign gods {first.name} and {second.name} leagued together against the pantheon.",
                key="divine.league",
                kind=ChronicleKind.FOREIGN_GOD,
                world_id=first.world_id,
            )
            joined += 1
    return joined


async def league_of(ctx: TickContext, god_id: int) -> list[ForeignGodRow]:
    bonds = await active_bonds(ctx.session, [BondKind.ALLY], sources=[god_id]) + await active_bonds(ctx.session, [BondKind.ALLY], targets=[god_id])
    allies = {bond.target_node_id if bond.source_node_id == god_id else bond.source_node_id for bond in bonds}
    found = [await ctx.session.get(ForeignGodRow, ally) for ally in sorted(allies)]
    return [god for god in found if god is not None and god.status is ForeignGodStatus.AWAKE]


async def pact_between(ctx: TickContext, first: int, second: int) -> TreatyProfileRow | None:
    mine = select(TreatyPartyRow.treaty_entity_id).where(TreatyPartyRow.party_node_id == first)
    theirs = select(TreatyPartyRow.treaty_entity_id).where(TreatyPartyRow.party_node_id == second)
    return await ctx.session.scalar(
        select(TreatyProfileRow).where(
            TreatyProfileRow.kind == TreatyKind.DIVINE_PACT,
            TreatyProfileRow.status == TreatyStatus.IN_FORCE,
            TreatyProfileRow.treaty_entity_id.in_(mine),
            TreatyProfileRow.treaty_entity_id.in_(theirs),
        )
    )


async def seal_pact(ctx: TickContext, son: SonRow, god: ForeignGodRow, epochs: int | None = None) -> EntityRow:
    table = ctx.rules.god_relations
    span = epochs if epochs is not None else table.pact_epochs
    treaty = await sign(ctx, TreatyKind.DIVINE_PACT, [(son.id, PartyRole.SIGNATORY), (god.id, PartyRole.SIGNATORY)], until=ctx.epoch + span, witnessed=False)
    god.stance = min(PERCENT, god.stance + table.pact_stance)
    await note(ctx, f"{son.name} and the foreign god {god.name} sealed a divine pact.", key="divine.pact", son_id=son.id, kind=ChronicleKind.FOREIGN_GOD)
    return treaty


async def divine_pacts(ctx: TickContext) -> int:
    table = ctx.rules.god_relations
    sealed = 0
    sons = list(await ctx.session.scalars(select(SonRow).where(SonRow.status != SonStatus.DEAD).order_by(SonRow.id)))
    for god in await ctx.session.scalars(select(ForeignGodRow).where(ForeignGodRow.status == ForeignGodStatus.AWAKE).order_by(ForeignGodRow.id)):
        for son in sons:
            if sealed >= table.pact_cap or held(son.id, god.id) or son.current_world_id != god.world_id:
                continue
            if await friendship(ctx, god.id, son.id) < table.pact_friendship or await pact_between(ctx, son.id, god.id) is not None:
                continue
            await seal_pact(ctx, son, god)
            sealed += 1
    return sealed


def doctrine_tenets(rules_max: int, god: ForeignGodRow) -> list[TenetKind]:
    chosen: list[TenetKind] = []
    for domain in domains_of(god):
        for tenet in DOMAIN_TENETS.get(domain, ()):
            if tenet in chosen or any(frozenset({tenet, other}) in OPPOSED for other in chosen):
                continue
            chosen.append(tenet)
    return chosen[:rules_max]


async def native_cult(ctx: TickContext, god: ForeignGodRow) -> EntityRow | None:
    worshippers = select(BondRow.source_node_id).where(BondRow.target_node_id == god.id, BondRow.kind == BondKind.WORSHIPS, BondRow.state == BondState.ACTIVE)
    return await ctx.session.scalar(
        select(EntityRow)
        .where(EntityRow.id.in_(worshippers), EntityRow.entity_type == EntityType.CULT, EntityRow.status == EntityStatus.CANON, EntityRow.subtype == OLD_FAITH)
        .limit(1)
    )


async def old_god_doctrine(ctx: TickContext) -> int:
    seeded = 0
    gods = await ctx.session.scalars(select(ForeignGodRow).where(ForeignGodRow.status != ForeignGodStatus.DEAD).order_by(ForeignGodRow.id))
    for god in gods:
        if held(god.id) or await native_cult(ctx, god) is not None:
            continue
        believers = await active_bonds(ctx.session, [BondKind.WORSHIPS], targets=[god.id])
        if not believers:
            continue
        cult = await open_record(
            ctx.session,
            ctx.epoch,
            RecordSpec(
                entity_type=EntityType.CULT,
                name=f"The old faith of {god.name}",
                body=f"The native worship of {god.name}.",
                stats=CultStats(),
                power=1,
                world_id=god.world_id,
                subtype=OLD_FAITH,
            ),
        )
        await connect(ctx.session, cult.id, god.id, BondKind.WORSHIPS, ctx.epoch, description="the old faith")
        ctx.session.add(CultDoctrineRow(cult_entity_id=cult.id, judgement=DOMAIN_JUDGEMENT.get(god.domain_primary, JudgementDoctrine.DEEDS), locked=[]))
        for tenet in doctrine_tenets(ctx.rules.doctrine.tenets_max, god):
            ctx.session.add(CultTenetRow(cult_entity_id=cult.id, tenet=tenet, since_epoch=ctx.epoch))
        seeded += 1
    await ctx.session.flush()
    return seeded
