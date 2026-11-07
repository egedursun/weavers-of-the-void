from collections.abc import Sequence
from dataclasses import dataclass, field, replace
from types import MappingProxyType

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.units import PERCENT
from aerona.db.repositories.bonds import BondDraft, BondRepository
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.polity import TreatyClauseRow, TreatyPartyRow, TreatyProfileRow
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.culture import LanguageRegister
from aerona.domain.enums.entity import COMMUNITY_TYPES, EntityStatus, EntityType
from aerona.domain.enums.mind import MemoryKind
from aerona.domain.enums.polity import ClauseKind, OathKind, PartyRole, TreatyKind, TreatyStatus
from aerona.domain.models.entity_stats import TreatyStats
from aerona.engine.communication.post import offer_treaty
from aerona.engine.context import TickContext
from aerona.engine.lore.language import register_barrier
from aerona.engine.mind.memories import remember
from aerona.engine.polity.oaths import oath_god, swear
from aerona.engine.polity.regard import on_kept, on_marriage
from aerona.engine.primitives.queries import active_bonds, close, connect, living_entity
from aerona.engine.primitives.records import RecordSpec, create_record
from aerona.engine.primitives.stats import set_stats, stat

TREATY_WORDS = MappingProxyType(
    {
        TreatyKind.PEACE: "the Peace",
        TreatyKind.TRUCE: "the Truce",
        TreatyKind.ALLIANCE_DEFENSIVE: "the Alliance",
        TreatyKind.ALLIANCE_OFFENSIVE: "the War Pact",
        TreatyKind.NON_AGGRESSION: "the Pact of Restraint",
        TreatyKind.VASSALAGE: "the Oath of Vassalage",
        TreatyKind.TRIBUTE: "the Tribute",
        TreatyKind.MARRIAGE_PACT: "the Marriage Pact",
        TreatyKind.TRADE_PACT: "the Trade Pact",
        TreatyKind.CONDOTTA: "the Condotta",
        TreatyKind.GUARANTEE: "the Guarantee",
        TreatyKind.INTERWORLD: "the Treaty of the Worlds",
        TreatyKind.COALITION: "the Coalition",
    }
)
DEFAULT_CLAUSES = MappingProxyType(
    {
        TreatyKind.ALLIANCE_DEFENSIVE: (ClauseKind.CALL_TO_ARMS,),
        TreatyKind.ALLIANCE_OFFENSIVE: (ClauseKind.CALL_TO_ARMS,),
        TreatyKind.NON_AGGRESSION: (ClauseKind.NON_AGGRESSION,),
        TreatyKind.PEACE: (ClauseKind.NON_AGGRESSION,),
        TreatyKind.TRUCE: (ClauseKind.NON_AGGRESSION,),
        TreatyKind.VASSALAGE: (ClauseKind.TRIBUTE, ClauseKind.CALL_TO_ARMS),
        TreatyKind.TRIBUTE: (ClauseKind.TRIBUTE,),
        TreatyKind.TRADE_PACT: (ClauseKind.TRADE_RIGHTS, ClauseKind.TOLLS_WAIVED),
        TreatyKind.MARRIAGE_PACT: (ClauseKind.MARRIAGE,),
        TreatyKind.INTERWORLD: (ClauseKind.TRADE_RIGHTS, ClauseKind.NON_AGGRESSION),
        TreatyKind.GUARANTEE: (ClauseKind.NON_AGGRESSION,),
        TreatyKind.CONDOTTA: (ClauseKind.CALL_TO_ARMS,),
        TreatyKind.COALITION: (ClauseKind.CALL_TO_ARMS,),
    }
)
DERIVED = MappingProxyType(
    {
        TreatyKind.ALLIANCE_DEFENSIVE: BondKind.ALLY,
        TreatyKind.ALLIANCE_OFFENSIVE: BondKind.ALLY,
        TreatyKind.MARRIAGE_PACT: BondKind.ALLY,
        TreatyKind.TRUCE: BondKind.TRUCE,
        TreatyKind.PEACE: BondKind.TRUCE,
        TreatyKind.VASSALAGE: BondKind.PAYS_TRIBUTE,
        TreatyKind.TRIBUTE: BondKind.PAYS_TRIBUTE,
        TreatyKind.TRADE_PACT: BondKind.TRADES_WITH,
        TreatyKind.INTERWORLD: BondKind.TRADES_WITH,
        TreatyKind.COALITION: BondKind.ALLY,
    }
)
TRIBUTARY_ROLES = (PartyRole.VASSAL,)
PARTY_TYPES = frozenset({*COMMUNITY_TYPES, EntityType.POLITY, EntityType.HOUSE, EntityType.BEAST, EntityType.MORTAL})


@dataclass(frozen=True)
class Clause:
    kind: ClauseKind
    obligor: int | None = None
    beneficiary: int | None = None
    params: dict[str, int | str | bool] = field(default_factory=dict)


def halved(value: int | str | bool) -> int | str | bool:
    return value // 2 if isinstance(value, int) and not isinstance(value, bool) else value


async def misread(ctx: TickContext, clause: Clause) -> Clause:
    if clause.obligor is None or clause.beneficiary is None or clause.obligor == clause.beneficiary:
        return clause
    court = LanguageRegister.COURT
    if await register_barrier(ctx.session, ctx.rules, clause.obligor, clause.beneficiary, ctx.epoch, ours=court, theirs=court) >= 1:
        return clause
    if not ctx.rng(f"misread.{clause.kind.value}.{clause.obligor}.{clause.beneficiary}.{ctx.epoch}").chance(ctx.rules.interpreters.misread_chance):
        return clause
    params = {key: halved(value) for key, value in clause.params.items()}
    params["misread"] = True
    ctx.count("treaty_clause_misread")
    return replace(clause, params=params)


async def sworn_by(ctx: TickContext, party: EntityRow) -> EntityRow | None:
    if party.entity_type is EntityType.MORTAL:
        return party
    bonds = await active_bonds(ctx.session, [BondKind.RULES], targets=[party.id])
    for bond in bonds:
        ruler = await living_entity(ctx.session, bond.source_node_id)
        if ruler is not None and ruler.entity_type is EntityType.MORTAL:
            return ruler
    return None


def bond_ends(kind: TreatyKind, parties: Sequence[tuple[int, PartyRole]], clauses: Sequence[Clause]) -> tuple[int, int] | None:
    principals = [party for party, role in parties if role is not PartyRole.GUARANTOR]
    if len(principals) < 2:
        return None
    if DERIVED.get(kind) is BondKind.PAYS_TRIBUTE:
        payer = next((party for party, role in parties if role in TRIBUTARY_ROLES), None)
        lord = next((party for party, role in parties if role is PartyRole.OVERLORD), None)
        tribute = next((clause for clause in clauses if clause.kind is ClauseKind.TRIBUTE), None)
        payer = payer if payer is not None else tribute.obligor if tribute is not None else principals[0]
        lord = lord if lord is not None else tribute.beneficiary if tribute is not None else principals[1]
        return (payer, lord) if payer is not None and lord is not None and payer != lord else None
    return principals[0], principals[1]


async def derive_bond(ctx: TickContext, treaty: EntityRow, kind: TreatyKind, ends: tuple[int, int] | None, until: int | None) -> BondRow | None:
    bond_kind = DERIVED.get(kind)
    if bond_kind is None or ends is None:
        return None
    first, second = (await living_entity(ctx.session, ends[0]), await living_entity(ctx.session, ends[1]))
    if first is None or second is None or first.entity_type not in COMMUNITY_TYPES or second.entity_type not in COMMUNITY_TYPES:
        return None
    draft = BondDraft(first.id, second.id, bond_kind, ctx.epoch, treaty.name, truce_until_epoch=until if bond_kind is BondKind.TRUCE else None)
    return await BondRepository(ctx.session).connect(draft)


async def sign(
    ctx: TickContext,
    kind: TreatyKind,
    parties: Sequence[tuple[int, PartyRole]],
    *,
    clauses: Sequence[Clause] = (),
    until: int | None = None,
    bond: BondRow | None = None,
    witnessed: bool = True,
    derive: bool = True,
) -> EntityRow:
    names = [entity.name for party, _ in parties if (entity := await ctx.session.get(EntityRow, party)) is not None]
    first = await ctx.session.get(EntityRow, parties[0][0])
    treaty = await create_record(
        ctx,
        RecordSpec(
            entity_type=EntityType.TREATY,
            name=f"{TREATY_WORDS[kind]} of {' and '.join(names[:3])}",
            body=f"{TREATY_WORDS[kind]} bound {', '.join(names)}.",
            stats=TreatyStats(parties=len(parties), trust=50),
            power=2,
            location_id=None,
            world_id=first.world_id if first is not None else None,
            subtype=kind.value.replace("_", " "),
            pending=False,
        ),
    )
    witness = await oath_god(ctx, treaty.world_id) if witnessed else None
    chosen = [await misread(ctx, clause) for clause in list(clauses) or [Clause(item, parties[0][0], parties[-1][0]) for item in DEFAULT_CLAUSES.get(kind, ())]]
    derived = bond if bond is not None else (await derive_bond(ctx, treaty, kind, bond_ends(kind, parties, chosen), until) if derive else None)
    profile = TreatyProfileRow(
        treaty_entity_id=treaty.id,
        kind=kind,
        status=TreatyStatus.IN_FORCE,
        signed_epoch=ctx.epoch,
        until_epoch=until,
        witness_son_id=witness.id if witness is not None else None,
        source_bond_id=derived.id if derived is not None else None,
        locked=[],
    )
    ctx.session.add(profile)
    for party, role in parties:
        ctx.session.add(TreatyPartyRow(treaty_entity_id=treaty.id, party_node_id=party, role=role))
    for clause in chosen:
        ctx.session.add(
            TreatyClauseRow(
                treaty_entity_id=treaty.id, kind=clause.kind, obligor_node_id=clause.obligor, beneficiary_node_id=clause.beneficiary, params=clause.params
            )
        )
    await ctx.session.flush()
    for party, _ in parties:
        await connect(ctx.session, party, treaty.id, BondKind.PARTY_TO, ctx.epoch, description="signatory")
    if witness is not None and first is not None:
        swearer = await sworn_by(ctx, first)
        if swearer is not None:
            oath = await swear(
                ctx, swearer, OathKind.FEALTY if kind is TreatyKind.VASSALAGE else OathKind.PROTECTION, recipient_id=parties[-1][0], witness=witness
            )
            profile.oath_id = oath.id
    await execute_on_signing(ctx, treaty, chosen)
    if kind is TreatyKind.MARRIAGE_PACT and len(parties) >= 2:
        await on_marriage(ctx, parties[0][0], parties[-1][0])
    ctx.count(f"treaty.{kind.value}")
    return treaty


async def execute_on_signing(ctx: TickContext, treaty: EntityRow, clauses: Sequence[Clause]) -> None:
    table = ctx.rules.treaties
    for clause in clauses:
        obligor = await living_entity(ctx.session, clause.obligor) if clause.obligor is not None else None
        beneficiary = await living_entity(ctx.session, clause.beneficiary) if clause.beneficiary is not None else None
        if obligor is None or beneficiary is None:
            continue
        if clause.kind is ClauseKind.WERGILD:
            value = int(clause.params.get("amount", table.wergild_value))
            if stat(obligor, "wealth") is not None:
                set_stats(obligor, wealth=max(0, (stat(obligor, "wealth") or 0) - value // 10))
            if stat(beneficiary, "wealth") is not None:
                set_stats(beneficiary, wealth=min(PERCENT, (stat(beneficiary, "wealth") or 0) + value // 10))
        elif clause.kind is ClauseKind.CESSION and "region_id" in clause.params:
            region = int(clause.params["region_id"])
            for settlement in await ctx.session.scalars(
                select(EntityRow).where(EntityRow.entity_type == EntityType.SETTLEMENT, EntityRow.status == EntityStatus.CANON, EntityRow.location_id == region)
            ):
                for bond in await active_bonds(ctx.session, [BondKind.RULES], targets=[settlement.id]):
                    await close(ctx.session, bond, ctx.epoch, f"ceded by {treaty.name}")
                await connect(ctx.session, beneficiary.id, settlement.id, BondKind.RULES, ctx.epoch, description=f"ceded by {treaty.name}")
        elif clause.kind is ClauseKind.TRADE_RIGHTS and obligor.entity_type in COMMUNITY_TYPES and beneficiary.entity_type in COMMUNITY_TYPES:
            await connect(ctx.session, obligor.id, beneficiary.id, BondKind.TRADES_WITH, ctx.epoch, description=treaty.name)


async def parties_of(session: AsyncSession, treaty_id: int) -> list[TreatyPartyRow]:
    return list(await session.scalars(select(TreatyPartyRow).where(TreatyPartyRow.treaty_entity_id == treaty_id)))


async def end_treaty(ctx: TickContext, profile: TreatyProfileRow, status: TreatyStatus, reason: str) -> None:
    profile.status = status
    profile.ended_epoch = ctx.epoch
    treaty = await ctx.session.get(EntityRow, profile.treaty_entity_id)
    bond = await ctx.session.get(BondRow, profile.source_bond_id) if profile.source_bond_id is not None else None
    if bond is not None and bond.state is BondState.ACTIVE:
        await close(ctx.session, bond, ctx.epoch, reason)
    if treaty is not None:
        treaty.end_epoch = ctx.epoch
        treaty.fate_note = f"Epoch {ctx.epoch}: {reason}."
    if status in {TreatyStatus.FULFILLED, TreatyStatus.EXPIRED}:
        await remember_kept(ctx, profile, treaty)
        parties = list(await ctx.session.scalars(select(TreatyPartyRow.party_node_id).where(TreatyPartyRow.treaty_entity_id == profile.treaty_entity_id)))
        await on_kept(ctx, parties, profile.kind)


async def remember_kept(ctx: TickContext, profile: TreatyProfileRow, treaty: EntityRow | None) -> None:
    table = ctx.rules.treaties
    parties = [row.party_node_id for row in await parties_of(ctx.session, profile.treaty_entity_id) if row.role is not PartyRole.GUARANTOR]
    years = max(1, ctx.epoch - profile.signed_epoch)
    weight = min(PERCENT, table.kept_memory * years)
    for holder in parties:
        for subject in parties:
            if holder != subject:
                await remember(
                    ctx.session,
                    ctx.rules,
                    holder_id=holder,
                    subject_id=subject,
                    kind=MemoryKind.KEPT_OATH,
                    magnitude=weight,
                    epoch=ctx.epoch,
                    note=f"kept {treaty.name if treaty is not None else 'a treaty'}"[:120],
                    event_id=profile.treaty_entity_id,
                )


async def treaty_between(session: AsyncSession, first: int, second: int, kinds: Sequence[TreatyKind]) -> TreatyProfileRow | None:
    first_side = select(TreatyPartyRow.treaty_entity_id).where(TreatyPartyRow.party_node_id == first)
    second_side = select(TreatyPartyRow.treaty_entity_id).where(TreatyPartyRow.party_node_id == second)
    found: TreatyProfileRow | None = await session.scalar(
        select(TreatyProfileRow)
        .where(
            TreatyProfileRow.status == TreatyStatus.IN_FORCE,
            TreatyProfileRow.kind.in_(list(kinds)),
            TreatyProfileRow.treaty_entity_id.in_(first_side),
            TreatyProfileRow.treaty_entity_id.in_(second_side),
        )
        .order_by(TreatyProfileRow.treaty_entity_id.desc())
        .limit(1)
    )
    return found


async def clause_pairs(session: AsyncSession, kind: ClauseKind) -> set[frozenset[int]]:
    pairs: set[frozenset[int]] = set()
    treaties = select(TreatyProfileRow.treaty_entity_id).where(TreatyProfileRow.status == TreatyStatus.IN_FORCE)
    held = set(
        await session.scalars(select(TreatyClauseRow.treaty_entity_id).where(TreatyClauseRow.kind == kind, TreatyClauseRow.treaty_entity_id.in_(treaties)))
    )
    if not held:
        return pairs
    members: dict[int, list[int]] = {}
    for row in await session.scalars(select(TreatyPartyRow).where(TreatyPartyRow.treaty_entity_id.in_(list(held)))):
        members.setdefault(row.treaty_entity_id, []).append(row.party_node_id)
    for parties in members.values():
        for index, first in enumerate(parties):
            for second in parties[index + 1 :]:
                pairs.add(frozenset((first, second)))
    return pairs


async def propose(
    ctx: TickContext,
    kind: TreatyKind,
    parties: Sequence[tuple[int, PartyRole]],
    *,
    proposer_id: int,
    clauses: Sequence[Clause] = (),
    epochs: int | None = None,
) -> EntityRow:
    names = [entity.name for party, _ in parties if (entity := await ctx.session.get(EntityRow, party)) is not None]
    first = await ctx.session.get(EntityRow, parties[0][0])
    treaty = await create_record(
        ctx,
        RecordSpec(
            entity_type=EntityType.TREATY,
            name=f"{TREATY_WORDS[kind]} of {' and '.join(names[:3])}",
            body=f"{TREATY_WORDS[kind]} offered to {', '.join(names)}.",
            stats=TreatyStats(parties=len(parties), trust=50),
            power=2,
            location_id=None,
            world_id=first.world_id if first is not None else None,
            subtype=kind.value.replace("_", " "),
            pending=False,
        ),
    )
    ctx.session.add(
        TreatyProfileRow(
            treaty_entity_id=treaty.id,
            kind=kind,
            status=TreatyStatus.PROPOSED,
            signed_epoch=ctx.epoch,
            until_epoch=epochs,
            proposed_by_node_id=proposer_id,
            locked=[],
        )
    )
    for party, role in parties:
        ctx.session.add(TreatyPartyRow(treaty_entity_id=treaty.id, party_node_id=party, role=role))
    terms = list(clauses) or [Clause(item, parties[0][0], parties[-1][0]) for item in DEFAULT_CLAUSES.get(kind, ())]
    for clause in terms:
        ctx.session.add(
            TreatyClauseRow(
                treaty_entity_id=treaty.id, kind=clause.kind, obligor_node_id=clause.obligor, beneficiary_node_id=clause.beneficiary, params=clause.params
            )
        )
    await ctx.session.flush()
    await offer_treaty(ctx, proposer_id, [party for party, _ in parties], treaty.id, [clause.kind.value for clause in terms])
    ctx.count("treaty_proposed")
    return treaty


async def accept(ctx: TickContext, profile: TreatyProfileRow) -> EntityRow | None:
    treaty = await ctx.session.get(EntityRow, profile.treaty_entity_id)
    if treaty is None or profile.status is not TreatyStatus.PROPOSED:
        return None
    parties = [(row.party_node_id, row.role) for row in await parties_of(ctx.session, profile.treaty_entity_id)]
    rows = list(
        await ctx.session.scalars(select(TreatyClauseRow).where(TreatyClauseRow.treaty_entity_id == profile.treaty_entity_id).order_by(TreatyClauseRow.id))
    )
    clauses = [Clause(row.kind, row.obligor_node_id, row.beneficiary_node_id, dict(row.params)) for row in rows]
    span = profile.until_epoch
    profile.status = TreatyStatus.IN_FORCE
    profile.signed_epoch = ctx.epoch
    profile.until_epoch = ctx.epoch + span if span is not None else None
    bond = await derive_bond(ctx, treaty, profile.kind, bond_ends(profile.kind, parties, clauses), profile.until_epoch)
    profile.source_bond_id = bond.id if bond is not None else None
    for party, _ in parties:
        await connect(ctx.session, party, treaty.id, BondKind.PARTY_TO, ctx.epoch, description="signatory")
    witness = await oath_god(ctx, treaty.world_id)
    first = await ctx.session.get(EntityRow, parties[0][0])
    if witness is not None and first is not None:
        profile.witness_son_id = witness.id
        swearer = await sworn_by(ctx, first)
        if swearer is not None:
            oath = await swear(
                ctx, swearer, OathKind.FEALTY if profile.kind is TreatyKind.VASSALAGE else OathKind.PROTECTION, recipient_id=parties[-1][0], witness=witness
            )
            profile.oath_id = oath.id
    await execute_on_signing(ctx, treaty, clauses)
    ctx.count(f"treaty.{profile.kind.value}")
    return treaty


def reject(ctx: TickContext, profile: TreatyProfileRow) -> None:
    profile.status = TreatyStatus.REJECTED
    profile.ended_epoch = ctx.epoch
