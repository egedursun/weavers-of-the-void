from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.arcana import CONDITIONAL_DURATIONS, RANGES, RITE_CONDITIONS
from aerona.catalog.life.crafts import KNOWN_NAME_TOKENS
from aerona.catalog.orders import TIMED_CONDITIONS
from aerona.db.tables.arcana import RiteGrammarRow
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.constructs import InstructionOrderRow, InstructionSetRow
from aerona.db.tables.crafts import SympatheticLinkRow
from aerona.db.tables.customs import MembershipRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.intrigue import TrueNameRow
from aerona.db.tables.polity import ClaimRow
from aerona.db.tables.statecraft import CrisisRow
from aerona.domain.enums.arcana import SpellDuration, SpellRange
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.constructs import CommandToken, OrderTime
from aerona.domain.enums.crafts import LinkToken
from aerona.domain.enums.customs import Naturalisation
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.polity import ClaimBasis
from aerona.domain.enums.statecraft import CrisisDemand, CrisisState


async def not_mortal(session: AsyncSession, node_id: int | None) -> bool:
    entity = await session.get(EntityRow, node_id) if node_id is not None else None
    return entity is None or entity.entity_type is not EntityType.MORTAL


async def faceless_hand_overs(session: AsyncSession) -> list[int]:
    rows = await session.scalars(
        select(CrisisRow).where(CrisisRow.demand == CrisisDemand.HAND_OVER, CrisisRow.state == CrisisState.ESCALATING).order_by(CrisisRow.id)
    )
    return [row.id for row in rows if await not_mortal(session, row.subject_node_id)]


async def drop_hand_over(session: AsyncSession, key: int) -> None:
    row = await session.get(CrisisRow, key)
    if row is not None and row.state is CrisisState.ESCALATING:
        row.state = CrisisState.BACKED_DOWN


async def unpartnered_unions(session: AsyncSession) -> list[int]:
    rows = await session.scalars(select(MembershipRow).where(MembershipRow.path == Naturalisation.UNION).order_by(MembershipRow.mortal_entity_id))
    return [row.mortal_entity_id for row in rows if await not_mortal(session, row.spouse_entity_id)]


async def mark_residence(session: AsyncSession, key: int) -> None:
    row = await session.get(MembershipRow, key)
    if row is not None and row.path is Naturalisation.UNION:
        row.path = Naturalisation.RESIDENCE
        row.spouse_entity_id = None


async def orphaned_adoptions(session: AsyncSession) -> list[int]:
    rows = await session.scalars(select(ClaimRow).where(ClaimRow.basis == ClaimBasis.ADOPTION, ClaimRow.ended_epoch.is_(None)).order_by(ClaimRow.id))
    return [row.id for row in rows if await not_mortal(session, row.backer_entity_id)]


async def end_adoption(session: AsyncSession, key: int) -> None:
    row = await session.get(ClaimRow, key)
    if row is not None and row.ended_epoch is None:
        row.ended_epoch = row.since_epoch


async def unlinked_rites(session: AsyncSession) -> list[int]:
    linked = sorted(kind for kind, spec in RANGES.items() if spec.through_link)
    rows = await session.scalars(select(RiteGrammarRow).where(RiteGrammarRow.range.in_(linked)).order_by(RiteGrammarRow.rite_entity_id))
    holders = set(await session.scalars(select(SympatheticLinkRow.holder_node_id)))
    found = []
    for row in rows:
        keepers = await session.scalars(
            select(BondRow.source_node_id).where(BondRow.target_node_id == row.rite_entity_id, BondRow.kind == BondKind.OWNS, BondRow.state == BondState.ACTIVE)
        )
        if not holders & set(keepers):
            found.append(row.rite_entity_id)
    return found


async def reach_by_sight(session: AsyncSession, key: int) -> None:
    row = await session.get(RiteGrammarRow, key)
    if row is not None:
        row.range = SpellRange.SIGHT


def condition_unnamed(row: RiteGrammarRow) -> bool:
    if row.condition is None:
        return True
    spec = RITE_CONDITIONS[row.condition]
    return (spec.needs_act and row.condition_act is None) or (spec.needs_epoch and row.condition_epoch is None)


async def unconditioned_rites(session: AsyncSession) -> list[int]:
    conditional = sorted(CONDITIONAL_DURATIONS)
    rows = await session.scalars(select(RiteGrammarRow).where(RiteGrammarRow.duration.in_(conditional)).order_by(RiteGrammarRow.rite_entity_id))
    return [row.rite_entity_id for row in rows if condition_unnamed(row)]


async def last_an_epoch(session: AsyncSession, key: int) -> None:
    row = await session.get(RiteGrammarRow, key)
    if row is not None:
        row.duration = SpellDuration.EPOCH


async def unknown_true_names(session: AsyncSession) -> list[int]:
    rows = await session.scalars(select(SympatheticLinkRow).where(SympatheticLinkRow.token.in_(sorted(KNOWN_NAME_TOKENS))).order_by(SympatheticLinkRow.id))
    found = []
    for row in rows:
        name = await session.get(TrueNameRow, row.target_node_id)
        if name is None or row.holder_node_id not in name.known_by:
            found.append(row.id)
    return found


async def link_by_name(session: AsyncSession, key: int) -> None:
    row = await session.get(SympatheticLinkRow, key)
    if row is not None:
        row.token = LinkToken.NAME


async def untimed_orders(session: AsyncSession) -> list[int]:
    timed = sorted(TIMED_CONDITIONS)
    rows = await session.scalars(
        select(InstructionOrderRow.id).where(InstructionOrderRow.condition.in_(timed), InstructionOrderRow.times.is_(None)).order_by(InstructionOrderRow.id)
    )
    return list(rows)


async def run_by_day(session: AsyncSession, key: int) -> None:
    row = await session.get(InstructionOrderRow, key)
    if row is not None:
        row.times = OrderTime.DAY


async def nameless_commands(session: AsyncSession) -> list[int]:
    rows = await session.scalars(select(InstructionSetRow).where(InstructionSetRow.command_token == CommandToken.TRUE_NAME).order_by(InstructionSetRow.id))
    return [row.id for row in rows if await session.get(TrueNameRow, row.owner_entity_id) is None]


async def command_by_word(session: AsyncSession, key: int) -> None:
    row = await session.get(InstructionSetRow, key)
    if row is not None:
        row.command_token = CommandToken.WORD
