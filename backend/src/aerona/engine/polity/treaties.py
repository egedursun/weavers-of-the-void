from types import MappingProxyType

from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.cosmos import AppliedFixupRow
from aerona.db.tables.economy import TradeRouteTollRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.polity import OathRow, PolityProfileRow, TreatyBreachRow, TreatyClauseRow, TreatyProfileRow, VassalageRow
from aerona.db.tables.society import CommunitySocietyRow
from aerona.db.tables.warfare import ArmyRow, TributeRow, WarRow, WarSideRow
from aerona.db.write_guard import held
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.economy import GoodsFlow
from aerona.domain.enums.entity import COMMUNITY_TYPES, EntityStatus, EntityType
from aerona.domain.enums.intrigue import FavourOrigin, HookDemand
from aerona.domain.enums.mind import MemoryKind
from aerona.domain.enums.mortal import MarriageKind
from aerona.domain.enums.polity import ClauseKind, PartyRole, TreatyKind, TreatyStatus
from aerona.domain.enums.society import Commodity
from aerona.domain.enums.war import TributeStatus, WarCause, WarSide, WarStatus
from aerona.engine.communication.post import proposal_pending
from aerona.engine.context import TickContext
from aerona.engine.intrigue.beliefs import daring
from aerona.engine.intrigue.favours import owe
from aerona.engine.intrigue.leverage import leaned_on
from aerona.engine.military.support import new_side
from aerona.engine.mind.drives import greed_drive
from aerona.engine.mortal.kinship import marry
from aerona.engine.notes import note
from aerona.engine.polity.accords import (
    DEFAULT_CLAUSES,
    Clause,
    accept,
    clause_pairs,
    end_treaty,
    parties_of,
    reject,
    sign,
    sworn_by,
    treaty_between,
)
from aerona.engine.polity.book import Realm, RealmBook
from aerona.engine.polity.loyalty import vassal_loyalty
from aerona.engine.polity.oaths import break_oath
from aerona.engine.polity.regard import on_breach
from aerona.engine.polity.repute import shift_honour, shift_infamy
from aerona.engine.polity.subjects import kind_for, pays_tribute, sends_levies
from aerona.engine.primitives.folk import present_among
from aerona.engine.primitives.numbers import round_half_up
from aerona.engine.primitives.prosperity import add_prosperity
from aerona.engine.primitives.queries import active_bonds, living_entity
from aerona.engine.primitives.society import move_stock
from aerona.engine.primitives.stats import move_stat, shift_stat
from aerona.engine.primitives.strength import MilitaryStrength
from aerona.engine.primitives.transfers import move_amount
from aerona.engine.relations.persuasion import envoy_sways
from aerona.engine.renown.currencies import realm_of_community, ruler_of_realm
from aerona.engine.services.community_relations import change_relation, relation
from aerona.engine.services.war import declare_war

BOND_KINDS = MappingProxyType(
    {
        BondKind.TRUCE: TreatyKind.TRUCE,
        BondKind.ALLY: TreatyKind.ALLIANCE_DEFENSIVE,
        BondKind.PAYS_TRIBUTE: TreatyKind.TRIBUTE,
        BondKind.TRADES_WITH: TreatyKind.TRADE_PACT,
    }
)
ADOPT_FIXUP = "treaties_from_bonds"
KIND = "kind"
PEACEFUL = frozenset({ClauseKind.NON_AGGRESSION, ClauseKind.CALL_TO_ARMS})
OFFENSIVE = frozenset({TreatyKind.ALLIANCE_OFFENSIVE, TreatyKind.CONDOTTA})
DEFENSIVE = frozenset({TreatyKind.ALLIANCE_DEFENSIVE, TreatyKind.MARRIAGE_PACT, TreatyKind.VASSALAGE, TreatyKind.GUARANTEE, TreatyKind.COALITION})


async def adopt_bonds(ctx: TickContext) -> int:
    if await ctx.session.get(AppliedFixupRow, ADOPT_FIXUP) is not None:
        return 0
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
        parties = [(first.id, PartyRole.SIGNATORY), (second.id, PartyRole.SIGNATORY)]
        until = (
            bond.truce_until_epoch
            if bond.kind is BondKind.TRUCE
            else ctx.epoch + ctx.rules.treaties.trade_epochs
            if bond.kind is BondKind.TRADES_WITH
            else ctx.epoch + ctx.rules.campaigns.tribute_epochs
            if bond.kind is BondKind.PAYS_TRIBUTE
            else None
        )
        clauses = [Clause(item, first.id, second.id, tribute_terms(ctx) if item is ClauseKind.TRIBUTE else {}) for item in DEFAULT_CLAUSES.get(kind, ())]
        if kind is TreatyKind.ALLIANCE_DEFENSIVE:
            clauses.append(Clause(ClauseKind.CALL_TO_ARMS, second.id, first.id))
        await sign(ctx, kind, parties, clauses=clauses, until=until, bond=bond, witnessed=False)
        made += 1
    ctx.session.add(AppliedFixupRow(key=ADOPT_FIXUP, result={"treaties": made}))
    await ctx.session.flush()
    return made


def tribute_terms(ctx: TickContext) -> dict[str, int | str | bool]:
    return {"amount": ctx.rules.campaigns.tribute_flow, "commodity": Commodity.GOODS.value, "epochs": ctx.rules.campaigns.tribute_epochs}


async def in_force(ctx: TickContext) -> list[TreatyProfileRow]:
    return list(
        await ctx.session.scalars(select(TreatyProfileRow).where(TreatyProfileRow.status == TreatyStatus.IN_FORCE).order_by(TreatyProfileRow.treaty_entity_id))
    )


async def clauses_of(ctx: TickContext, treaty_id: int) -> list[TreatyClauseRow]:
    return list(await ctx.session.scalars(select(TreatyClauseRow).where(TreatyClauseRow.treaty_entity_id == treaty_id).order_by(TreatyClauseRow.id)))


async def breach(ctx: TickContext, profile: TreatyProfileRow, breaker_id: int, *, clause: TreatyClauseRow | None, reason: str) -> None:
    table = ctx.rules.treaties
    row = TreatyBreachRow(
        treaty_entity_id=profile.treaty_entity_id,
        clause_id=clause.id if clause is not None else None,
        breaker_node_id=breaker_id,
        epoch=ctx.epoch,
        note=reason[:120],
    )
    ctx.session.add(row)
    await end_treaty(ctx, profile, TreatyStatus.BROKEN, reason)
    wronged = [party.party_node_id for party in await parties_of(ctx.session, profile.treaty_entity_id) if party.party_node_id != breaker_id]
    await on_breach(ctx, breaker_id, wronged)
    breaker = await living_entity(ctx.session, breaker_id)
    treaty = await ctx.session.get(EntityRow, profile.treaty_entity_id)
    write = await ctx.chronicle(
        ChronicleKind.DIPLOMACY,
        f"{breaker.name if breaker is not None else 'A party'} broke {treaty.name if treaty else 'the treaty'}: {reason}.",
        template_key="treaty.broken",
        entity_ids=[breaker_id, profile.treaty_entity_id],
        son_id=profile.witness_son_id,
    )
    row.incident_id = write.incident_id
    if breaker is None:
        return
    ruler = await sworn_by(ctx, breaker)
    if ruler is not None:
        await shift_honour(ctx, ruler.id, -table.breach_honour)
        await shift_infamy(ctx, ruler.id, table.breach_infamy)
    if profile.oath_id is not None:
        oath = await ctx.session.get(OathRow, profile.oath_id)
        if oath is not None:
            await break_oath(ctx, oath, reason)
    victims = [
        party.party_node_id
        for party in await parties_of(ctx.session, profile.treaty_entity_id)
        if party.party_node_id != breaker_id and party.role is not PartyRole.GUARANTOR
    ]
    for victim in victims:
        other = await living_entity(ctx.session, victim)
        if other is not None and other.entity_type in COMMUNITY_TYPES and breaker.entity_type in COMMUNITY_TYPES:
            await change_relation(ctx, victim, breaker.id, -table.breach_relation, MemoryKind.BETRAYED_ME, note="broke the treaty")
    await call_guarantors(ctx, profile, breaker)


async def call_guarantors(ctx: TickContext, profile: TreatyProfileRow, breaker: EntityRow) -> int:
    joined = 0
    for party in await parties_of(ctx.session, profile.treaty_entity_id):
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
        parties = {party.party_node_id for party in await parties_of(ctx.session, profile.treaty_entity_id)}
        bond = next((item for item in fresh if {item.source_node_id, item.target_node_id} <= parties), None)
        if bond is None:
            continue
        clauses = await clauses_of(ctx, profile.treaty_entity_id)
        if any(clause.kind in PEACEFUL for clause in clauses) or profile.kind in {TreatyKind.PEACE, TreatyKind.TRUCE, TreatyKind.NON_AGGRESSION}:
            peaceful = next((item for item in clauses if item.kind in PEACEFUL), None)
            await breach(ctx, profile, bond.source_node_id, clause=peaceful, reason="it went to war against a sworn party")
            broken += 1
    return broken


async def allies_called(ctx: TickContext, party_id: int, side: WarSide | None = None) -> list[int]:
    found: list[int] = []
    for profile in await in_force(ctx):
        if side is WarSide.ATTACKER and profile.kind in DEFENSIVE:
            continue
        if side is WarSide.DEFENDER and profile.kind in OFFENSIVE:
            continue
        for clause in await clauses_of(ctx, profile.treaty_entity_id):
            if clause.kind is ClauseKind.CALL_TO_ARMS and clause.beneficiary_node_id == party_id and clause.obligor_node_id is not None:
                found.append(clause.obligor_node_id)
    return found


async def leader_of(ctx: TickContext, community_id: int) -> int | None:
    realm = await realm_of_community(ctx.session, community_id)
    return await ruler_of_realm(ctx.session, realm) if realm is not None else None


async def answer_call(ctx: TickContext, ally_id: int, party_id: int) -> bool:
    table = ctx.rules.treaties
    if ctx.rng(f"call.{ally_id}.{party_id}.{ctx.epoch}").chance(table.call_to_arms_chance):
        return True
    asker, answerer = await leader_of(ctx, party_id), await leader_of(ctx, ally_id)
    if asker is not None and answerer is not None and await leaned_on(ctx, asker, answerer, HookDemand.SUPPORT):
        ctx.count("calls_answered_for_a_debt")
        return True
    ally = await living_entity(ctx.session, ally_id)
    if ally is not None and ally.entity_type in COMMUNITY_TYPES:
        await change_relation(ctx, party_id, ally_id, -table.refuse_relation_loss, MemoryKind.BETRAYED_ME, note="did not answer the call to arms")
    return False


async def keep_clauses(ctx: TickContext, book: RealmBook) -> dict[str, int]:
    table = ctx.rules.treaties
    counts = {"expired": 0, "renewed": 0, "broken": 0, "kept": 0, "guarded": 0}
    strength = await MilitaryStrength.load(ctx.session, ctx.rules)
    for profile in await in_force(ctx):
        bond = await ctx.session.get(BondRow, profile.source_bond_id) if profile.source_bond_id is not None else None
        if bond is not None and bond.state is not BondState.ACTIVE and "status" not in profile.locked:
            await end_treaty(ctx, profile, TreatyStatus.EXPIRED, "the bond it made lapsed")
            counts["expired"] += 1
            continue
        if profile.until_epoch is not None and ctx.epoch >= profile.until_epoch and "until_epoch" not in profile.locked:
            parties = [party.party_node_id for party in await parties_of(ctx.session, profile.treaty_entity_id)]
            friendly = len(parties) >= 2 and await relation(ctx.session, ctx.rules, parties[0], parties[1]) >= table.renew_relation
            if friendly and profile.kind not in {TreatyKind.TRUCE, TreatyKind.TRIBUTE}:
                profile.until_epoch = ctx.epoch + table.alliance_epochs
                profile.renewals += 1
                counts["renewed"] += 1
            else:
                await end_treaty(
                    ctx, profile, TreatyStatus.FULFILLED if profile.kind in {TreatyKind.TRIBUTE, TreatyKind.TRUCE} else TreatyStatus.EXPIRED, "its term ran out"
                )
                counts["expired"] += 1
            continue
        if profile.kind is TreatyKind.GUARANTEE:
            counts["guarded"] += await guard(ctx, profile)
        if profile.kind is TreatyKind.INTERWORLD:
            await bridge_worlds(ctx, profile)
        for clause in await clauses_of(ctx, profile.treaty_entity_id):
            if await keep_clause(ctx, profile, clause, strength):
                counts["kept"] += 1
            elif profile.status is TreatyStatus.BROKEN:
                counts["broken"] += 1
                break
    await vassal_rows(ctx, book)
    return counts


async def misread_breach(ctx: TickContext, profile: TreatyProfileRow, clause: TreatyClauseRow) -> bool:
    if not clause.params.get("misread") or clause.obligor_node_id is None or clause.beneficiary_node_id is None:
        return False
    seed = f"misread_breach.{profile.treaty_entity_id}.{clause.id}.{ctx.epoch}"
    if not ctx.rng(seed).chance(ctx.rules.interpreters.misread_breach_chance):
        return False
    obligor = await living_entity(ctx.session, clause.obligor_node_id)
    beneficiary = await living_entity(ctx.session, clause.beneficiary_node_id)
    if obligor is None or beneficiary is None:
        return False
    label = clause.kind.value.replace("_", " ")
    await note(
        ctx,
        f"Neither court read the other's tongue: {obligor.name} kept the clause of {label} as something less than {beneficiary.name} meant, "
        "and the misreading was counted a breach.",
        key="treaty.misread_breach",
        ids=[obligor.id, beneficiary.id],
    )
    ctx.count("treaty_clause_misread_breach")
    await breach(ctx, profile, obligor.id, clause=clause, reason="it kept the clause only as its own tongue had read it")
    return True


async def keep_clause(ctx: TickContext, profile: TreatyProfileRow, clause: TreatyClauseRow, strength: MilitaryStrength) -> bool:
    if await misread_breach(ctx, profile, clause):
        return False
    if clause.kind is ClauseKind.TRIBUTE:
        return await pay_tribute(ctx, profile, clause)
    if clause.kind is ClauseKind.HOSTAGE:
        return await keep_hostage(ctx, profile, clause)
    if clause.kind is ClauseKind.TOLLS_WAIVED:
        return await tolls_kept(ctx, profile, clause)
    if clause.kind is ClauseKind.DEMILITARISED and "region_id" in clause.params and clause.obligor_node_id is not None:
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
                EntityRow.entity_type == EntityType.MORTAL, EntityRow.status == EntityStatus.CANON, await present_among(ctx.session, [clause.obligor_node_id])
            )
        )
        for fugitive in fugitives:
            homes = {bond.target_node_id for bond in await active_bonds(ctx.session, [BondKind.MEMBER_OF, BondKind.PROTECTS], sources=[fugitive.id])}
            if clause.beneficiary_node_id in homes:
                fugitive.location_id = clause.beneficiary_node_id
    clause.last_kept_epoch = ctx.epoch
    return True


async def pay_tribute(ctx: TickContext, profile: TreatyProfileRow, clause: TreatyClauseRow) -> bool:
    table = ctx.rules.treaties
    if clause.params.get("hoard"):
        return True
    payer = await living_entity(ctx.session, clause.obligor_node_id) if clause.obligor_node_id is not None else None
    receiver = await living_entity(ctx.session, clause.beneficiary_node_id) if clause.beneficiary_node_id is not None else None
    if payer is None or receiver is None:
        clause.last_kept_epoch = ctx.epoch
        return True
    if profile.signed_epoch == ctx.epoch:
        clause.last_kept_epoch = ctx.epoch
        return True
    greed = await greed_drive(ctx.session, ctx.rules, receiver.id) if receiver.entity_type in COMMUNITY_TYPES else 1.0
    amount = round_half_up(int(clause.params.get("amount", ctx.rules.campaigns.tribute_flow)) * greed)
    paid = False
    if shift_stat(payer, "prosperity", -amount) is not None:
        add_prosperity(ctx.rules, receiver, amount)
        paid = True
    if move_stat(payer, receiver, "wealth", amount):
        paid = True
    commodity = str(clause.params.get("commodity", Commodity.GOODS.value))
    payer_society = await ctx.session.get(CommunitySocietyRow, payer.id)
    receiver_society = await ctx.session.get(CommunitySocietyRow, receiver.id)
    if payer_society is not None and receiver_society is not None and commodity in {item.value for item in Commodity}:
        kind = Commodity(commodity)
        held = getattr(payer_society, f"stock_{kind.value}", 0) or 0
        goods = round_half_up(held * min(PERCENT, ctx.rules.campaigns.tribute_goods_pct * greed) / PERCENT)
        if goods > 0:
            await move_stock(ctx.session, ctx.rules, payer.id, receiver.id, kind, index=goods, epoch=ctx.epoch, flow=GoodsFlow.TRIBUTE)
            paid = True
    payer_realm = await ctx.session.get(PolityProfileRow, payer.id)
    receiver_realm = await ctx.session.get(PolityProfileRow, receiver.id)
    if payer_realm is not None and receiver_realm is not None:
        moved = min(payer_realm.treasury, amount * table.realm_tribute_scale)
        paid = (move_amount(payer_realm, receiver_realm, "treasury", moved) and moved > 0) or paid
    if paid:
        clause.last_kept_epoch = ctx.epoch
        ctx.count("tributes_paid")
        return True
    last = clause.last_kept_epoch if clause.last_kept_epoch is not None else profile.signed_epoch
    if ctx.epoch - last > table.unpaid_grace:
        await breach(ctx, profile, payer.id, clause=clause, reason="it stopped paying the tribute it owed")
        return False
    return True


async def keep_hostage(ctx: TickContext, profile: TreatyProfileRow, clause: TreatyClauseRow) -> bool:
    table = ctx.rules.treaties
    key = clause.params.get("mortal_id", clause.params.get("hostage"))
    hostage = await living_entity(ctx.session, int(key)) if key is not None else None
    if hostage is None or clause.beneficiary_node_id is None:
        clause.last_kept_epoch = ctx.epoch
        return True
    due = profile.signed_epoch + table.hostage_epochs
    if ctx.epoch < due:
        if (
            hostage.location_id not in {clause.beneficiary_node_id, None}
            and hostage.location_id == clause.obligor_node_id
            and clause.last_kept_epoch is not None
        ):
            await breach(ctx, profile, clause.obligor_node_id or hostage.id, clause=clause, reason="it took back the hostage it had given")
            return False
        hostage.location_id = clause.beneficiary_node_id
    else:
        hostage.location_id = clause.obligor_node_id
    clause.last_kept_epoch = ctx.epoch
    return True


async def tolls_kept(ctx: TickContext, profile: TreatyProfileRow, clause: TreatyClauseRow) -> bool:
    parties = {party.party_node_id for party in await parties_of(ctx.session, profile.treaty_entity_id)}
    charged = await ctx.session.scalar(
        select(TradeRouteTollRow)
        .where(TradeRouteTollRow.controller_entity_id.in_(list(parties)), TradeRouteTollRow.rate_pct > 0, TradeRouteTollRow.set_by_player.is_(True))
        .limit(1)
    )
    if charged is not None and charged.controller_entity_id is not None:
        await breach(ctx, profile, charged.controller_entity_id, clause=clause, reason="it charged tolls it had sworn to waive")
        return False
    clause.last_kept_epoch = ctx.epoch
    return True


async def guard(ctx: TickContext, profile: TreatyProfileRow) -> int:
    roles = await parties_of(ctx.session, profile.treaty_entity_id)
    guarantors = [row.party_node_id for row in roles if row.role is PartyRole.GUARANTOR]
    wards = [row.party_node_id for row in roles if row.role is not PartyRole.GUARANTOR]
    joined = 0
    for ward in wards:
        attacks = await ctx.session.scalars(
            select(WarRow)
            .join(WarSideRow, WarSideRow.war_id == WarRow.id)
            .where(WarSideRow.entity_id == ward, WarSideRow.side == WarSide.DEFENDER, WarSideRow.left_epoch.is_(None), WarRow.status == WarStatus.ONGOING)
        )
        for war in attacks:
            attacker = await ctx.session.scalar(select(WarSideRow.entity_id).where(WarSideRow.war_id == war.id, WarSideRow.side == WarSide.ATTACKER).limit(1))
            for guarantor in guarantors:
                if attacker is None or guarantor == attacker or guarantor in wards:
                    continue
                odds = ctx.rules.treaties.guarantor_chance * await daring(ctx, guarantor, attacker)
                willing = ctx.rng(f"guard.{profile.treaty_entity_id}.{guarantor}.{war.id}").chance(odds)
                if willing and await declare_war(ctx, guarantor, attacker, "it stood by the land it guaranteed", cause=WarCause.PUNITIVE):
                    await owe(ctx, ward, guarantor, FavourOrigin.WAR_SUPPORT, ctx.rules.intrigue.war_favour)
                    joined += 1
    return joined


async def bridge_worlds(ctx: TickContext, profile: TreatyProfileRow) -> None:
    table = ctx.rules.treaties
    parties = [row.party_node_id for row in await parties_of(ctx.session, profile.treaty_entity_id)]
    for index, first in enumerate(parties):
        for second in parties[index + 1 :]:
            one, two = await living_entity(ctx.session, first), await living_entity(ctx.session, second)
            if one is None or two is None or one.entity_type not in COMMUNITY_TYPES or two.entity_type not in COMMUNITY_TYPES:
                continue
            await change_relation(ctx, first, second, table.interworld_relation, MemoryKind.TRADED_WITH, note="the treaty of the worlds")
            add_prosperity(ctx.rules, one, table.interworld_prosperity)
            add_prosperity(ctx.rules, two, table.interworld_prosperity)


async def champion_for(ctx: TickContext, first_id: int, second_id: int) -> bool:
    return frozenset((first_id, second_id)) in await clause_pairs(ctx.session, ClauseKind.CHAMPION)


async def vassal_rows(ctx: TickContext, book: RealmBook) -> None:
    for profile in await in_force(ctx):
        if profile.kind is not TreatyKind.VASSALAGE:
            continue
        roles = {party.role: party.party_node_id for party in await parties_of(ctx.session, profile.treaty_entity_id)}
        vassal = book.realm_of(roles.get(PartyRole.VASSAL))
        overlord = book.realm_of(roles.get(PartyRole.OVERLORD))
        if vassal is None or overlord is None or vassal.entity.id == overlord.entity.id:
            continue
        row = book.vassals.get(vassal.entity.id)
        if row is None:
            row = VassalageRow(
                vassal_entity_id=vassal.entity.id,
                overlord_entity_id=overlord.entity.id,
                treaty_entity_id=profile.treaty_entity_id,
                since_epoch=ctx.epoch,
                kind=await kind_for(ctx, book, vassal, overlord),
                locked=[],
            )
            ctx.session.add(row)
            book.vassals[vassal.entity.id] = row
        elif KIND not in row.locked and not held(vassal.entity.id):
            row.kind = await kind_for(ctx, book, vassal, overlord)
        row.overlord_entity_id = overlord.entity.id
        row.treaty_entity_id = profile.treaty_entity_id
        first, second = roles.get(PartyRole.VASSAL), roles.get(PartyRole.OVERLORD)
        if first is not None and second is not None and "loyalty" not in row.locked:
            row.loyalty = await vassal_loyalty(ctx, first, second, row.tribute_pct)


async def vassal_duties(ctx: TickContext, book: RealmBook) -> dict[str, int]:
    table = ctx.rules.treaties
    counts = {"tribute": 0, "levies": 0, "revolts": 0, "switched": 0}
    strength = await MilitaryStrength.load(ctx.session, ctx.rules)
    for vassal_id, row in list(book.vassals.items()):
        vassal = book.realms.get(vassal_id)
        overlord = book.realms.get(row.overlord_entity_id)
        if vassal is None or overlord is None:
            continue
        owed = round_half_up(vassal.profile.treasury * row.tribute_pct / PERCENT) if pays_tribute(row) else 0
        if owed > 0 and move_amount(vassal.profile, overlord.profile, "treasury", owed):
            counts["tribute"] += owed
        if sends_levies(row):
            counts["levies"] += await send_levies(ctx, vassal.profile.core_entity_id, overlord.profile.core_entity_id, row.levy_pct)
        weak = overlord.profile.stability < table.weak_overlord_stability
        vassal_core = await living_entity(ctx.session, vassal.profile.core_entity_id) if vassal.profile.core_entity_id is not None else None
        lord_core = await living_entity(ctx.session, overlord.profile.core_entity_id) if overlord.profile.core_entity_id is not None else None
        if vassal_core is None or lord_core is None:
            continue
        stronger = await strength.power(vassal_core) > await strength.power(lord_core) * table.vassal_revolt_strength_pct / PERCENT
        restless = row.loyalty < table.revolt_loyalty or row.liberty >= ctx.rules.statecraft.liberty_revolt
        if not restless or not (weak or stronger):
            continue
        treaty = await ctx.session.get(TreatyProfileRow, row.treaty_entity_id) if row.treaty_entity_id is not None else None
        patron = await new_overlord(ctx, book, vassal, overlord)
        if patron is not None and ctx.rng(f"switch.{vassal_id}.{ctx.epoch}").chance(table.switch_chance):
            if treaty is not None and treaty.status is TreatyStatus.IN_FORCE:
                await breach(ctx, treaty, vassal_core.id, clause=None, reason="it bent the knee to another lord")
            patron_core = patron.profile.core_entity_id
            if patron_core is not None:
                await sign(
                    ctx,
                    TreatyKind.VASSALAGE,
                    [(vassal_core.id, PartyRole.VASSAL), (patron_core, PartyRole.OVERLORD)],
                    clauses=[
                        Clause(ClauseKind.TRIBUTE, vassal_core.id, patron_core, tribute_terms(ctx)),
                        Clause(ClauseKind.CALL_TO_ARMS, vassal_core.id, patron_core),
                    ],
                )
            await ctx.session.delete(row)
            book.vassals.pop(vassal_id, None)
            counts["switched"] += 1
        elif ctx.rng(f"vassal_revolt.{vassal_id}.{ctx.epoch}").chance(table.vassal_revolt_chance):
            if treaty is not None and treaty.status is TreatyStatus.IN_FORCE:
                await breach(ctx, treaty, vassal_core.id, clause=None, reason="it rose against its overlord")
            await declare_war(ctx, vassal_core.id, lord_core.id, f"{vassal.entity.name} threw off its overlord", cause=WarCause.INDEPENDENCE)
            await ctx.session.delete(row)
            book.vassals.pop(vassal_id, None)
            counts["revolts"] += 1
    return counts


async def send_levies(ctx: TickContext, vassal_core: int | None, lord_core: int | None, share: int) -> int:
    if vassal_core is None or lord_core is None or share <= 0:
        return 0
    wars = await ctx.session.scalars(
        select(WarSideRow)
        .join(WarRow, WarRow.id == WarSideRow.war_id)
        .where(WarSideRow.entity_id == lord_core, WarSideRow.left_epoch.is_(None), WarRow.status == WarStatus.ONGOING)
    )
    sent = 0
    for side in wars:
        present = await ctx.session.scalar(select(WarSideRow.entity_id).where(WarSideRow.war_id == side.war_id, WarSideRow.entity_id == vassal_core))
        if present is not None or not ctx.rng(f"levy.{vassal_core}.{side.war_id}").chance(share):
            continue
        ctx.session.add(new_side(ctx, side.war_id, vassal_core, side.side))
        sent += 1
    return sent


async def new_overlord(ctx: TickContext, book: RealmBook, vassal: Realm, overlord: Realm) -> Realm | None:
    if vassal.profile.core_entity_id is None:
        return None
    best: tuple[int, Realm] | None = None
    for other in book.realms.values():
        if other.entity.id in {vassal.entity.id, overlord.entity.id} or other.profile.core_entity_id is None or other.entity.id in book.vassals:
            continue
        if other.entity.world_id != vassal.entity.world_id or other.profile.stability <= overlord.profile.stability:
            continue
        value = await relation(ctx.session, ctx.rules, vassal.profile.core_entity_id, other.profile.core_entity_id)
        if value >= ctx.rules.treaties.renew_relation and (best is None or value > best[0]):
            best = (value, other)
    return best[1] if best is not None else None


async def tribute_ledger(ctx: TickContext) -> int:
    ended = 0
    for row in await ctx.session.scalars(select(TributeRow).where(TributeRow.status == TributeStatus.ACTIVE)):
        bond = await ctx.session.get(BondRow, row.bond_id) if row.bond_id is not None else None
        if bond is not None and bond.state is not BondState.ACTIVE:
            row.status = TributeStatus.ENDED
            row.ended_epoch = ctx.epoch
            ended += 1
    return ended


async def sign_derived(
    ctx: TickContext, kind: TreatyKind, first: int, second: int, *, until: int | None, clauses: list[Clause] | None = None
) -> EntityRow | None:
    existing = await treaty_between(ctx.session, first, second, [kind])
    if existing is not None:
        return await ctx.session.get(EntityRow, existing.treaty_entity_id)
    roles = (
        [(first, PartyRole.VASSAL), (second, PartyRole.OVERLORD)]
        if kind is TreatyKind.VASSALAGE
        else [(first, PartyRole.SIGNATORY), (second, PartyRole.SIGNATORY)]
    )
    return await sign(ctx, kind, roles, clauses=clauses or [], until=until)


async def answer_proposals(ctx: TickContext) -> dict[str, int]:
    table = ctx.rules.treaties
    counts = {"accepted": 0, "rejected": 0}
    for profile in list(await ctx.session.scalars(select(TreatyProfileRow).where(TreatyProfileRow.status == TreatyStatus.PROPOSED))):
        if profile.signed_epoch >= ctx.epoch or await proposal_pending(ctx, profile.treaty_entity_id):
            continue
        parties = [row.party_node_id for row in await parties_of(ctx.session, profile.treaty_entity_id)]
        others = [party for party in parties if party != profile.proposed_by_node_id]
        proposer = profile.proposed_by_node_id
        warm = proposer is not None and all([await relation(ctx.session, ctx.rules, proposer, other) >= table.accept_relation for other in others])
        if warm or (proposer is not None and others and await envoy_sways(ctx, proposer, others, profile.treaty_entity_id)):
            await accept(ctx, profile)
            counts["accepted"] += 1
        elif ctx.epoch - profile.signed_epoch >= table.proposal_epochs:
            reject(ctx, profile)
            counts["rejected"] += 1
    return counts
