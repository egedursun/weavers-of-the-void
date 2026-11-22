from collections.abc import Awaitable, Callable

from sqlalchemy import Select, or_, select

from aerona.catalog.life.minds import SHIELDED_HOSTS_INTRUSION_AIMS
from aerona.catalog.life_traits import CLAUSE_KIND_TRAITS, ORDER_KIND_TRAITS, SPELL_TECHNIQUE_TRAITS, having
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.constructs import InstructionOrderRow, InstructionSetRow
from aerona.db.tables.disease import DiseaseProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.living import LivingLineRow
from aerona.db.tables.made import IntrusionRow, MadeRealmRow, ReplicatorLineRow, ReplicatorPresenceRow
from aerona.db.tables.mind import MemoryRow
from aerona.db.tables.networks import NetworkProfileRow
from aerona.db.tables.polity import PolityMemberRow, TreatyClauseRow
from aerona.db.tables.powers import PowerRow
from aerona.domain.enums.arcana import SpellForm
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import MortalRole
from aerona.domain.enums.life_traits import ClauseKindTrait, OrderKindTrait, SpellTechniqueTrait
from aerona.domain.enums.made import IntrusionAim, ReplicatorOutput, ReplicatorStage
from aerona.domain.enums.mind import MemoryKind
from aerona.domain.enums.polity import ClauseKind
from aerona.engine.context import TickContext
from aerona.engine.mass_weapons.limits import past_limit

WEAPON_ORDERS = having(ORDER_KIND_TRAITS, OrderKindTrait.WEAPON_ORDERS)
METHOD_CLAUSES = having(CLAUSE_KIND_TRAITS, ClauseKindTrait.METHOD_CLAUSES)
SEIZED = "it seized what the other side's minds and machines obeyed"
HARMING = having(SPELL_TECHNIQUE_TRAITS, SpellTechniqueTrait.HARMING)


async def side_of(ctx: TickContext, party_id: int) -> set[int]:
    members = set(await ctx.session.scalars(select(PolityMemberRow.member_entity_id).where(PolityMemberRow.polity_entity_id == party_id)))
    return {party_id, *members}


async def intruded(ctx: TickContext, actors: set[int], victims: set[int], aims: set[IntrusionAim], hosts: set[int] | None = None) -> bool:
    statement = select(IntrusionRow).where(IntrusionRow.epoch == ctx.epoch, IntrusionRow.actor_node_id.in_(actors), IntrusionRow.aim.in_(aims))
    for row in await ctx.session.scalars(statement):
        target = row.target_node_id
        if target is None:
            continue
        if hosts is not None:
            if target in hosts:
                return True
            continue
        owner = await ctx.session.get(NetworkProfileRow, target)
        holder = owner.owner_node_id if owner is not None else None
        entity = await ctx.session.get(EntityRow, target)
        if target in victims or holder in victims or (entity is not None and entity.location_id in victims):
            return True
    return False


async def copied_soldiers(ctx: TickContext, actors: set[int]) -> bool:
    soldiers = select(EntityRow.id).where(
        EntityRow.mortal_role.in_([MortalRole.WARRIOR, MortalRole.SWORN_WARRIOR, MortalRole.OFFICER]), EntityRow.affiliated_entity_id.in_(actors)
    )
    found = await ctx.session.scalar(
        select(BondRow.id).where(BondRow.kind == BondKind.COPY_OF, BondRow.epoch == ctx.epoch, BondRow.target_node_id.in_(soldiers)).limit(1)
    )
    return found is not None


async def armed_with_orders(ctx: TickContext, actors: set[int], victims: set[int]) -> bool:
    sets = select(InstructionSetRow.id).where(InstructionSetRow.holder_node_id.in_(actors))
    statement = select(InstructionOrderRow).where(
        InstructionOrderRow.set_id.in_(sets), InstructionOrderRow.kind.in_(list(WEAPON_ORDERS)), InstructionOrderRow.lapsed.is_(False)
    )
    return any(order.target_node_id in victims for order in await ctx.session.scalars(statement))


async def replicator_weapons(ctx: TickContext, actors: set[int], victims: set[int]) -> bool:
    lines = select(ReplicatorLineRow.id).where(
        ReplicatorLineRow.owner_node_id.in_(actors),
        ReplicatorLineRow.output == ReplicatorOutput.DISASSEMBLY,
        ReplicatorLineRow.stage.not_in([ReplicatorStage.STOPPED, ReplicatorStage.EXTINCT]),
    )
    regions = {town.location_id for town in await ctx.session.scalars(select(EntityRow).where(EntityRow.id.in_(victims))) if town.location_id is not None}
    present = await ctx.session.scalar(
        select(ReplicatorPresenceRow.id).where(ReplicatorPresenceRow.line_id.in_(lines), ReplicatorPresenceRow.place_node_id.in_(regions)).limit(1)
    )
    return present is not None


async def civil_hosts(ctx: TickContext, victims: set[int]) -> set[int]:
    return {
        row.host_node_id
        for row in await ctx.session.scalars(select(MadeRealmRow).where(MadeRealmRow.keeper_node_id.in_(victims)))
        if row.host_node_id is not None
    }


def folk_of(sides: set[int]) -> Select[int]:
    return select(EntityRow.id).where(or_(EntityRow.id.in_(sides), EntityRow.location_id.in_(sides)))


async def compelled(ctx: TickContext, actors: set[int], victims: set[int]) -> bool:
    found = await ctx.session.scalar(
        select(MemoryRow.id)
        .where(
            MemoryRow.kind == MemoryKind.COMPELLED_ME,
            MemoryRow.epoch == ctx.epoch,
            MemoryRow.holder_node_id.in_(folk_of(victims)),
            MemoryRow.subject_node_id.in_(folk_of(actors)),
        )
        .limit(1)
    )
    return found is not None


async def plague_powers(ctx: TickContext, actors: set[int]) -> bool:
    found = await ctx.session.scalar(
        select(PowerRow.id)
        .where(
            PowerRow.holder_node_id.in_(folk_of(actors)),
            PowerRow.form == SpellForm.BODY,
            PowerRow.technique.in_(list(HARMING)),
            PowerRow.last_used_epoch == ctx.epoch,
        )
        .limit(1)
    )
    return found is not None


async def designed_against(ctx: TickContext, actors: set[int], victims: set[int]) -> bool:
    lines = select(LivingLineRow.id).where(LivingLineRow.maker_node_id.in_(folk_of(actors)))
    found = await ctx.session.scalar(
        select(DiseaseProfileRow.disease_entity_id)
        .where(DiseaseProfileRow.designed_line_id.in_(lines), DiseaseProfileRow.target_node_id.in_(folk_of(victims)))
        .limit(1)
    )
    return found is not None


async def method_breached(ctx: TickContext, clause: TreatyClauseRow) -> str | None:
    if clause.kind not in METHOD_CLAUSES or clause.obligor_node_id is None or clause.beneficiary_node_id is None:
        return None
    actors, victims = await side_of(ctx, clause.obligor_node_id), await side_of(ctx, clause.beneficiary_node_id)
    kind = ClauseKind(clause.kind)
    checks: dict[ClauseKind, tuple[Callable[[], Awaitable[bool]], str]] = {
        ClauseKind.MIND_SEIZURE_BAN: (lambda: intruded(ctx, actors, victims, {IntrusionAim.SEIZE}), SEIZED),
        ClauseKind.CIVIL_NETWORK_SHIELD: (lambda: intruded(ctx, actors, victims, {IntrusionAim.DENY}), "it cut a network the other side's people lived by"),
        ClauseKind.CIVIL_HOST_SHIELD: (lambda: shielded_hosts(ctx, actors, victims), "it struck what holds the other side's realm"),
        ClauseKind.SOLDIER_COPY_BAN: (lambda: copied_soldiers(ctx, actors), "it copied its soldiers"),
        ClauseKind.AUTONOMOUS_WEAPONS_BAN: (lambda: armed_with_orders(ctx, actors, victims), "it set instructed weapons on the other side"),
        ClauseKind.REPLICATOR_WEAPON_BAN: (lambda: replicator_weapons(ctx, actors, victims), "it loosed self-making machines on the other side's lands"),
        ClauseKind.NO_MIND_COMPULSION: (lambda: compelled(ctx, actors, victims), "it compelled the minds of the other side's people by a power"),
        ClauseKind.NO_PLAGUE_POWERS: (lambda: plague_powers(ctx, actors), "it used powers that harm the body"),
        ClauseKind.NO_DESIGNED_DISEASE: (lambda: designed_against(ctx, actors, victims), "it made a disease aimed at the other side"),
        ClauseKind.MASS_WEAPON_LIMIT: (lambda: past_limit(ctx, actors, clause), "it built or tested weapons of mass harm past its limit"),
    }
    test, reason = checks[kind]
    return reason if await test() else None


async def shielded_hosts(ctx: TickContext, actors: set[int], victims: set[int]) -> bool:
    return await intruded(ctx, actors, victims, set(SHIELDED_HOSTS_INTRUSION_AIMS), await civil_hosts(ctx, victims))
