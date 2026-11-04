from collections.abc import Sequence
from dataclasses import dataclass, field, replace
from types import MappingProxyType

from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.polity import OathRow, TreatyBreachRow, TreatyClauseRow, TreatyPartyRow, TreatyProfileRow, VassalageRow
from aerona.db.tables.warfare import ArmyRow
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.entity import COMMUNITY_TYPES, EntityStatus, EntityType
from aerona.domain.enums.mind import MemoryKind
from aerona.domain.enums.mortal import MarriageKind
from aerona.domain.enums.polity import ClauseKind, OathKind, PartyRole, TreatyKind, TreatyStatus
from aerona.domain.enums.war import WarCause
from aerona.domain.models.entity_stats import TreatyStats
from aerona.engine.context import TickContext
from aerona.engine.lore.language import barrier
from aerona.engine.mortal.kinship import marry
from aerona.engine.notes import note
from aerona.engine.polity.book import RealmBook
from aerona.engine.polity.oaths import break_oath, oath_god, swear
from aerona.engine.primitives.queries import active_bonds, close, connect, living_entity
from aerona.engine.primitives.records import RecordSpec, create_record
from aerona.engine.primitives.stats import set_stats, stat
from aerona.engine.services.community_relations import change_relation, relation
from aerona.engine.services.war import declare_war

BOND_KINDS = MappingProxyType(
    {
        BondKind.TRUCE: TreatyKind.TRUCE,
        BondKind.ALLY: TreatyKind.ALLIANCE_DEFENSIVE,
        BondKind.PAYS_TRIBUTE: TreatyKind.VASSALAGE,
        BondKind.TRADES_WITH: TreatyKind.TRADE_PACT,
    }
)
BETRAYAL_WORDS = ("betray", "broken", "abandon", "covenant broken")
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
        TreatyKind.INTERWORLD: (ClauseKind.TRADE_RIGHTS,),
    }
)
PEACEFUL = frozenset({ClauseKind.NON_AGGRESSION, ClauseKind.CALL_TO_ARMS})


@dataclass(frozen=True)
class Clause:
    kind: ClauseKind
    obligor: int | None = None
    beneficiary: int | None = None
    params: dict[str, int | str | bool] = field(default_factory=dict)


async def sign(
    ctx: TickContext,
    kind: TreatyKind,
    parties: Sequence[tuple[int, PartyRole]],
    *,
    clauses: Sequence[Clause] = (),
    until: int | None = None,
    bond: BondRow | None = None,
    witnessed: bool = True,
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
    profile = TreatyProfileRow(
        treaty_entity_id=treaty.id,
        kind=kind,
        status=TreatyStatus.IN_FORCE,
        signed_epoch=ctx.epoch,
        until_epoch=until,
        witness_son_id=witness.id if witness is not None else None,
        source_bond_id=bond.id if bond is not None else None,
        locked=[],
    )
    ctx.session.add(profile)
    for party, role in parties:
        ctx.session.add(TreatyPartyRow(treaty_entity_id=treaty.id, party_node_id=party, role=role))
    chosen = [await misread(ctx, clause) for clause in list(clauses) or [Clause(item, parties[0][0], parties[-1][0]) for item in DEFAULT_CLAUSES.get(kind, ())]]
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
    ctx.count(f"treaty.{kind.value}")
    return treaty


def halved(value: int | str | bool) -> int | str | bool:
    return value // 2 if isinstance(value, int) and not isinstance(value, bool) else value


async def misread(ctx: TickContext, clause: Clause) -> Clause:
    if clause.obligor is None or clause.beneficiary is None or clause.obligor == clause.beneficiary:
        return clause
    if await barrier(ctx.session, ctx.rules, clause.obligor, clause.beneficiary, ctx.epoch) >= 1:
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
        elif clause.kind is ClauseKind.TRADE_RIGHTS:
            await connect(ctx.session, obligor.id, beneficiary.id, BondKind.TRADES_WITH, ctx.epoch, description=treaty.name)


async def adopt_bonds(ctx: TickContext) -> int:
    linked = set(await ctx.session.scalars(select(TreatyProfileRow.source_bond_id).where(TreatyProfileRow.source_bond_id.is_not(None))))
    made = 0
    bonds = await ctx.session.scalars(select(BondRow).where(BondRow.state == BondState.ACTIVE, BondRow.kind.in_(list(BOND_KINDS))).order_by(BondRow.id))
    for bond in list(bonds):
        if bond.id in linked:
            continue
        first, second = await living_entity(ctx.session, bond.source_node_id), await living_entity(ctx.session, bond.target_node_id)
        if first is None or second is None or first.entity_type not in COMMUNITY_TYPES or second.entity_type not in COMMUNITY_TYPES:
            continue
        kind = BOND_KINDS[bond.kind]
        if kind is TreatyKind.VASSALAGE:
            parties = [(first.id, PartyRole.VASSAL), (second.id, PartyRole.OVERLORD)]
        else:
            parties = [(first.id, PartyRole.SIGNATORY), (second.id, PartyRole.SIGNATORY)]
        until = (
            bond.truce_until_epoch
            if bond.kind is BondKind.TRUCE
            else ctx.epoch + ctx.rules.treaties.trade_epochs
            if bond.kind is BondKind.TRADES_WITH
            else None
        )
        if kind is TreatyKind.ALLIANCE_DEFENSIVE and bond.description and "marriage" in bond.description:
            kind = TreatyKind.MARRIAGE_PACT
        clauses = [Clause(item, first.id, second.id) for item in DEFAULT_CLAUSES.get(kind, ())]
        if kind in {TreatyKind.ALLIANCE_DEFENSIVE, TreatyKind.MARRIAGE_PACT}:
            clauses.append(Clause(ClauseKind.CALL_TO_ARMS, second.id, first.id))
        await sign(ctx, kind, parties, clauses=clauses, until=until, bond=bond, witnessed=bond.epoch == ctx.epoch)
        made += 1
    return made


async def in_force(ctx: TickContext) -> list[TreatyProfileRow]:
    return list(
        await ctx.session.scalars(select(TreatyProfileRow).where(TreatyProfileRow.status == TreatyStatus.IN_FORCE).order_by(TreatyProfileRow.treaty_entity_id))
    )


async def parties_of(ctx: TickContext, treaty_id: int) -> list[TreatyPartyRow]:
    return list(await ctx.session.scalars(select(TreatyPartyRow).where(TreatyPartyRow.treaty_entity_id == treaty_id)))


async def clauses_of(ctx: TickContext, treaty_id: int) -> list[TreatyClauseRow]:
    return list(await ctx.session.scalars(select(TreatyClauseRow).where(TreatyClauseRow.treaty_entity_id == treaty_id).order_by(TreatyClauseRow.id)))


async def end_treaty(ctx: TickContext, profile: TreatyProfileRow, status: TreatyStatus, reason: str) -> None:
    profile.status = status
    profile.ended_epoch = ctx.epoch
    treaty = await ctx.session.get(EntityRow, profile.treaty_entity_id)
    bond = await ctx.session.get(BondRow, profile.source_bond_id) if profile.source_bond_id is not None else None
    if bond is not None and bond.state is BondState.ACTIVE and status is not TreatyStatus.BROKEN:
        await close(ctx.session, bond, ctx.epoch, reason)
    if treaty is not None:
        treaty.end_epoch = ctx.epoch
        treaty.fate_note = f"Epoch {ctx.epoch}: {reason}."


async def breach(ctx: TickContext, profile: TreatyProfileRow, breaker_id: int, *, clause: TreatyClauseRow | None, reason: str) -> None:
    table = ctx.rules.treaties
    ctx.session.add(
        TreatyBreachRow(
            treaty_entity_id=profile.treaty_entity_id,
            clause_id=clause.id if clause is not None else None,
            breaker_node_id=breaker_id,
            epoch=ctx.epoch,
            note=reason[:120],
        )
    )
    await end_treaty(ctx, profile, TreatyStatus.BROKEN, reason)
    breaker = await living_entity(ctx.session, breaker_id)
    if breaker is None:
        return
    ruler = await sworn_by(ctx, breaker)
    if ruler is not None:
        ruler.importance = max(0, (ruler.importance or 0) - table.breach_infamy)
    if profile.oath_id is not None:
        oath = await ctx.session.get(OathRow, profile.oath_id)
        if oath is not None:
            await break_oath(ctx, oath, reason)
    victims = [
        party.party_node_id
        for party in await parties_of(ctx, profile.treaty_entity_id)
        if party.party_node_id != breaker_id and party.role is not PartyRole.GUARANTOR
    ]
    for victim in victims:
        if (await living_entity(ctx.session, victim)) is not None and breaker.entity_type in COMMUNITY_TYPES:
            await change_relation(ctx, victim, breaker.id, -table.breach_infamy, MemoryKind.BETRAYED_ME, note="broke the treaty")
    await call_guarantors(ctx, profile, breaker)
    treaty = await ctx.session.get(EntityRow, profile.treaty_entity_id)
    await note(
        ctx,
        f"{breaker.name} broke {treaty.name if treaty else 'the treaty'}: {reason}.",
        key="treaty.broken",
        ids=[breaker.id, profile.treaty_entity_id],
        son_id=profile.witness_son_id,
        kind=ChronicleKind.DIPLOMACY,
    )


async def call_guarantors(ctx: TickContext, profile: TreatyProfileRow, breaker: EntityRow) -> int:
    joined = 0
    for party in await parties_of(ctx, profile.treaty_entity_id):
        if party.role is not PartyRole.GUARANTOR:
            continue
        guarantor = await living_entity(ctx.session, party.party_node_id)
        if guarantor is None or not ctx.rng(f"guarantor.{profile.treaty_entity_id}.{guarantor.id}").chance(ctx.rules.treaties.guarantor_chance):
            continue
        if await declare_war(ctx, guarantor.id, breaker.id, f"{guarantor.name} stood by its guarantee", cause=WarCause.PUNITIVE):
            joined += 1
    return joined


async def hostilities(ctx: TickContext) -> int:
    broken = 0
    fresh = list(
        await ctx.session.scalars(select(BondRow).where(BondRow.kind == BondKind.ENEMY, BondRow.state == BondState.ACTIVE, BondRow.epoch >= ctx.epoch - 1))
    )
    if not fresh:
        return 0
    for profile in await in_force(ctx):
        parties = {party.party_node_id for party in await parties_of(ctx, profile.treaty_entity_id)}
        bond = next((item for item in fresh if {item.source_node_id, item.target_node_id} <= parties), None)
        if bond is None:
            continue
        clauses = await clauses_of(ctx, profile.treaty_entity_id)
        if any(clause.kind in PEACEFUL for clause in clauses) or profile.kind in {TreatyKind.PEACE, TreatyKind.TRUCE, TreatyKind.NON_AGGRESSION}:
            peaceful = next((item for item in clauses if item.kind in PEACEFUL), None)
            await breach(ctx, profile, bond.source_node_id, clause=peaceful, reason="it went to war against a sworn party")
            broken += 1
    return broken


async def allies_called(ctx: TickContext, party_id: int) -> list[int]:
    found: list[int] = []
    for profile in await in_force(ctx):
        for clause in await clauses_of(ctx, profile.treaty_entity_id):
            if clause.kind is ClauseKind.CALL_TO_ARMS and clause.beneficiary_node_id == party_id and clause.obligor_node_id is not None:
                found.append(clause.obligor_node_id)
    return found


async def answer_call(ctx: TickContext, ally_id: int, party_id: int) -> bool:
    table = ctx.rules.treaties
    if ctx.rng(f"call.{ally_id}.{party_id}.{ctx.epoch}").chance(table.call_to_arms_chance):
        return True
    ally = await living_entity(ctx.session, ally_id)
    if ally is not None and ally.entity_type in COMMUNITY_TYPES:
        await change_relation(ctx, party_id, ally_id, -table.refuse_relation_loss, MemoryKind.BETRAYED_ME, note="did not answer the call to arms")
    return False


async def keep_clauses(ctx: TickContext, book: RealmBook) -> dict[str, int]:
    table = ctx.rules.treaties
    counts = {"expired": 0, "renewed": 0, "broken": 0, "kept": 0}
    for profile in await in_force(ctx):
        bond = await ctx.session.get(BondRow, profile.source_bond_id) if profile.source_bond_id is not None else None
        if bond is not None and bond.state is not BondState.ACTIVE:
            reason = bond.closed_reason or "the bond lapsed"
            if any(word in reason.lower() for word in BETRAYAL_WORDS):
                await breach(ctx, profile, bond.source_node_id, clause=None, reason=reason)
                counts["broken"] += 1
            else:
                await end_treaty(ctx, profile, TreatyStatus.EXPIRED, reason)
                counts["expired"] += 1
            continue
        if profile.until_epoch is not None and ctx.epoch >= profile.until_epoch and "until_epoch" not in profile.locked:
            parties = [party.party_node_id for party in await parties_of(ctx, profile.treaty_entity_id)]
            friendly = len(parties) >= 2 and await relation(ctx.session, ctx.rules, parties[0], parties[1]) >= table.renew_relation
            if friendly and profile.kind is not TreatyKind.TRUCE:
                profile.until_epoch = ctx.epoch + table.alliance_epochs
                profile.renewals += 1
                counts["renewed"] += 1
            else:
                await end_treaty(ctx, profile, TreatyStatus.EXPIRED, "its term ran out")
                counts["expired"] += 1
            continue
        for clause in await clauses_of(ctx, profile.treaty_entity_id):
            if await keep_clause(ctx, profile, clause):
                counts["kept"] += 1
            elif profile.status is TreatyStatus.BROKEN:
                counts["broken"] += 1
                break
    await vassal_rows(ctx, book)
    return counts


async def keep_clause(ctx: TickContext, profile: TreatyProfileRow, clause: TreatyClauseRow) -> bool:
    table = ctx.rules.treaties
    if clause.kind is ClauseKind.HOSTAGE and "mortal_id" in clause.params:
        hostage = await living_entity(ctx.session, int(clause.params["mortal_id"]))
        if hostage is not None and clause.beneficiary_node_id is not None:
            due = profile.signed_epoch + table.hostage_epochs
            hostage.location_id = clause.beneficiary_node_id if ctx.epoch < due else clause.obligor_node_id
    elif clause.kind is ClauseKind.DEMILITARISED and "region_id" in clause.params and clause.obligor_node_id is not None:
        region = int(clause.params["region_id"])
        armies = await ctx.session.scalars(select(ArmyRow).where(ArmyRow.owner_entity_id == clause.obligor_node_id, ArmyRow.disbanded_epoch.is_(None)))
        for row in armies:
            army = await living_entity(ctx.session, row.entity_id)
            if army is not None and army.location_id == region:
                await breach(ctx, profile, clause.obligor_node_id, clause=clause, reason="it marched soldiers into the demilitarised land")
                return False
    elif clause.kind is ClauseKind.MARRIAGE and "first_id" in clause.params and "second_id" in clause.params:
        first_spouse = await living_entity(ctx.session, int(clause.params["first_id"]))
        second_spouse = await living_entity(ctx.session, int(clause.params["second_id"]))
        if first_spouse is not None and second_spouse is not None and first_spouse.entity_type is second_spouse.entity_type is EntityType.MORTAL:
            await marry(
                ctx.session,
                first_spouse,
                second_spouse,
                ctx.epoch,
                kind=MarriageKind.POLITICAL,
                treaty_id=profile.treaty_entity_id,
                description="marriage by treaty",
            )
    elif clause.kind is ClauseKind.EXTRADITION and clause.beneficiary_node_id is not None and clause.obligor_node_id is not None:
        fugitives = await ctx.session.scalars(
            select(EntityRow).where(
                EntityRow.entity_type == EntityType.MORTAL, EntityRow.status == EntityStatus.CANON, EntityRow.location_id == clause.obligor_node_id
            )
        )
        for fugitive in fugitives:
            homes = {bond.target_node_id for bond in await active_bonds(ctx.session, [BondKind.MEMBER_OF, BondKind.PROTECTS], sources=[fugitive.id])}
            if clause.beneficiary_node_id in homes:
                fugitive.location_id = clause.beneficiary_node_id
    clause.last_kept_epoch = ctx.epoch
    return True


async def tolls_waived(ctx: TickContext, first_id: int, second_id: int) -> bool:
    for profile in await in_force(ctx):
        parties = {party.party_node_id for party in await parties_of(ctx, profile.treaty_entity_id)}
        if {first_id, second_id} <= parties and any(clause.kind is ClauseKind.TOLLS_WAIVED for clause in await clauses_of(ctx, profile.treaty_entity_id)):
            return True
    return False


async def faith_free(ctx: TickContext, first_id: int, second_id: int) -> bool:
    for profile in await in_force(ctx):
        parties = {party.party_node_id for party in await parties_of(ctx, profile.treaty_entity_id)}
        if {first_id, second_id} <= parties and any(clause.kind is ClauseKind.RELIGIOUS_FREEDOM for clause in await clauses_of(ctx, profile.treaty_entity_id)):
            return True
    return False


async def champion_for(ctx: TickContext, first_id: int, second_id: int) -> bool:
    for profile in await in_force(ctx):
        parties = {party.party_node_id for party in await parties_of(ctx, profile.treaty_entity_id)}
        if {first_id, second_id} <= parties and any(clause.kind is ClauseKind.CHAMPION for clause in await clauses_of(ctx, profile.treaty_entity_id)):
            return True
    return False


async def vassal_rows(ctx: TickContext, book: RealmBook) -> None:
    for profile in await in_force(ctx):
        if profile.kind is not TreatyKind.VASSALAGE:
            continue
        roles = {party.role: party.party_node_id for party in await parties_of(ctx, profile.treaty_entity_id)}
        vassal = book.realm_of(roles.get(PartyRole.VASSAL))
        overlord = book.realm_of(roles.get(PartyRole.OVERLORD))
        if vassal is None or overlord is None or vassal.entity.id == overlord.entity.id:
            continue
        row = book.vassals.get(vassal.entity.id)
        if row is None:
            row = VassalageRow(
                vassal_entity_id=vassal.entity.id, overlord_entity_id=overlord.entity.id, treaty_entity_id=profile.treaty_entity_id, since_epoch=ctx.epoch
            )
            ctx.session.add(row)
            book.vassals[vassal.entity.id] = row
        row.overlord_entity_id = overlord.entity.id
        row.treaty_entity_id = profile.treaty_entity_id
        first, second = roles.get(PartyRole.VASSAL), roles.get(PartyRole.OVERLORD)
        if first is not None and second is not None:
            row.loyalty = max(0, min(PERCENT, PERCENT // 2 + await relation(ctx.session, ctx.rules, first, second) // 2))
