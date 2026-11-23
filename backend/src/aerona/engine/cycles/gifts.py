from dataclasses import dataclass

from sqlalchemy import select

from aerona.catalog.gift_occasions import COMPETITIVE, HOLDING, OCCASIONS
from aerona.catalog.life_traits import GATHERING_KIND_TRAITS, GIFT_STATE_TRAITS, having
from aerona.constants.units import PERCENT
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.culture import ArtworkProfileRow
from aerona.db.tables.cycles import CircuitRow, DivineDebtRow, GiftRow, KinshipSystemRow
from aerona.db.tables.divine import DivineStandingRow
from aerona.db.tables.economy import NodeMaterialRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.gatherings import GatheringGuestRow, GatheringRow
from aerona.db.tables.military import FeudRow
from aerona.db.tables.mortal import MarriageRow
from aerona.db.tables.polity import HouseMemberRow
from aerona.db.write_guard import held
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.collective import NormBehaviour, NormSituation
from aerona.domain.enums.culture import ItemDeed
from aerona.domain.enums.cycles import GiftOccasion, GiftState
from aerona.domain.enums.entity import COMMUNITY_TYPES, EntityStatus, EntityType
from aerona.domain.enums.gathering import GatheringStatus
from aerona.domain.enums.life_traits import GatheringKindTrait, GiftStateTrait
from aerona.domain.enums.military import FeudStatus
from aerona.domain.enums.mind import MemoryKind, PreferenceKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.records import FactUnit, StepAction, StepOutcome
from aerona.domain.enums.unions import UnionExchange
from aerona.engine.body.customs import people_of
from aerona.engine.collective.book import shift
from aerona.engine.collective.norms import norm_pull, norms_of, stance_in
from aerona.engine.context import TickContext
from aerona.engine.crafts.rights import wed_portion
from aerona.engine.cycles.kinship import giver_and_taker
from aerona.engine.cycles.lineage import union_of
from aerona.engine.cycles.standing import name_of, raise_standing, regard
from aerona.engine.divine.gods import divine_of
from aerona.engine.divine.standing import standing_row, tally_epoch
from aerona.engine.ecology.beasts import hand_over
from aerona.engine.economy.purse import coin_of, receive_coin, take_coin
from aerona.engine.lore.items import material_key
from aerona.engine.mind.preferences import fit, prefs_of
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.queries import living_entity
from aerona.engine.primitives.stats import stat_or
from aerona.engine.recording.record import StepDraft, record
from aerona.engine.services.community_relations import end_blood_feud, relation
from aerona.engine.unions.customs import payer
from aerona.rules.registry import Rules

FRIENDS = (BondKind.ALLY, BondKind.COMPANION, BondKind.SWORN_KIN)
POTLATCH_FEASTS = having(GATHERING_KIND_TRAITS, GatheringKindTrait.POTLATCH_FEASTS)
OBLIGING = having(GIFT_STATE_TRAITS, GiftStateTrait.OBLIGING)


@dataclass
class GiftTally:
    given: int = 0
    returned: int = 0
    refused: int = 0
    lapsed: int = 0
    potlatches: int = 0
    passes: int = 0
    circuits: int = 0
    offerings: int = 0
    payments: int = 0
    exceeded: int = 0
    released: int = 0
    births: int = 0
    funerals: int = 0
    amends: int = 0
    patronage: int = 0
    hospitality: int = 0


async def obligation(ctx: TickContext, node_id: int) -> float:
    entity = await ctx.session.get(EntityRow, node_id)
    if entity is None:
        return 1.0
    people = entity if entity.entity_type is EntityType.PEOPLE else await people_of(ctx.session, entity)
    if people is None:
        return 1.0
    stance = stance_in(await norms_of(ctx.session, people.id), NormSituation.HOSPITALITY, NormBehaviour.GIFTS)
    return max(0.0, 1 + norm_pull(stance) * ctx.rules.reciprocity.norm_weight / PERCENT)


async def gift_value(ctx: TickContext, receiver_id: int, item_id: int | None, base: int) -> int:
    if item_id is None:
        return max(0, base)
    material = await ctx.session.scalar(select(NodeMaterialRow).where(NodeMaterialRow.node_id == item_id).limit(1))
    liking = fit(await prefs_of(ctx.session, receiver_id), PreferenceKind.MATERIAL, material_key(material))
    return max(0, round_half_up(base * (1 + liking * ctx.rules.reciprocity.preference_weight / PERCENT / PERCENT)))


async def spend(ctx: TickContext, giver_id: int, amount: int) -> bool:
    giver = await ctx.session.get(EntityRow, giver_id)
    if giver is None:
        return await divine_of(ctx.session, giver_id) is not None
    if amount <= 0:
        return True
    if await coin_of(ctx.session, ctx.rules, giver) < amount:
        return False
    return await take_coin(ctx.session, ctx.rules, giver, amount)


async def bestow(ctx: TickContext, receiver_id: int, amount: int) -> None:
    receiver = await ctx.session.get(EntityRow, receiver_id)
    if receiver is not None:
        await receive_coin(ctx.session, ctx.rules, receiver, amount)


async def refuses(ctx: TickContext, giver_id: int, receiver_id: int) -> bool:
    receiver = await ctx.session.get(EntityRow, receiver_id)
    if receiver is None or held(receiver_id):
        return False
    standing = await relation(ctx.session, ctx.rules, receiver_id, giver_id)
    return standing <= ctx.rules.reciprocity.refuse_below


async def give(
    ctx: TickContext,
    giver_id: int,
    receiver_id: int,
    base: int,
    occasion: GiftOccasion,
    *,
    item_id: int | None = None,
    destroyed: bool = False,
    answers: GiftRow | None = None,
    obliging: bool | None = None,
    pay: bool = True,
    circuit_id: int | None = None,
    tell: bool = False,
) -> GiftRow | None:
    table = ctx.rules.reciprocity
    spec = OCCASIONS[occasion]
    if obliging is None:
        obliging = spec.debt(ctx.rules) > 0
    if giver_id == receiver_id:
        return None
    value = await gift_value(ctx, receiver_id, item_id, base)
    if pay and not await spend(ctx, giver_id, value):
        return None
    due = ctx.epoch + max(1, round_half_up(table.return_epochs / max(0.25, await obligation(ctx, receiver_id)))) if obliging else None
    row = GiftRow(
        giver_node_id=giver_id,
        receiver_node_id=receiver_id,
        value=value,
        occasion=occasion,
        item_entity_id=item_id,
        state=GiftState.DESTROYED if destroyed else GiftState.OPEN if obliging else GiftState.RETURNED,
        answers_gift_id=answers.id if answers is not None else None,
        due_epoch=None if occasion is GiftOccasion.FUNERAL else due,
        settled_epoch=None if obliging else ctx.epoch,
        epoch=ctx.epoch,
        circuit_id=circuit_id,
        locked=[],
    )
    ctx.session.add(row)
    await ctx.session.flush()
    if not destroyed and pay:
        await bestow(ctx, receiver_id, value)
    if item_id is not None and not destroyed:
        await hand_over(ctx, item_id, receiver_id, ItemDeed.GIVEN, f"given by {await name_of(ctx, giver_id)}")
    await raise_standing(ctx, giver_id, value * table.give_prestige / PERCENT * spec.standing / PERCENT)
    await regard(ctx, (receiver_id, giver_id), table.gift_regard, MemoryKind.GIFTED_ME, occasion.value)
    if tell:
        await record(
            ctx,
            "gift.given",
            roles={IncidentRole.GIVER: giver_id, IncidentRole.RECEIVER: receiver_id},
            facts={"value": value, "occasion": occasion, "owed": round_half_up(value * spec.debt(ctx.rules) / PERCENT)},
            steps=(StepDraft(StepAction.GIVE, actor=giver_id, target=receiver_id, amount=value, unit=FactUnit.COIN),),
        )
    if obliging and await refuses(ctx, giver_id, receiver_id):
        await refuse(ctx, row)
    return row


def owed_back(rules: Rules, gift: GiftRow) -> int:
    return max(1, round_half_up(gift.value * OCCASIONS[gift.occasion].debt(rules) / PERCENT))


def exceeding(rules: Rules, gift: GiftRow) -> int:
    return round_half_up(gift.value * rules.gifts.exceed_ratio_pct / PERCENT)


async def outgiving(ctx: TickContext, gift: GiftRow, answer: GiftRow) -> bool:
    if gift.answers_gift_id is None:
        return False
    before = await ctx.session.get(GiftRow, gift.answers_gift_id)
    return before is not None and before.state is GiftState.EXCEEDED


async def drain_rivals(ctx: TickContext, gift: GiftRow) -> None:
    table = ctx.rules.gifts
    for side in (gift.giver_node_id, gift.receiver_node_id):
        entity = await ctx.session.get(EntityRow, side)
        if entity is None or held(side):
            continue
        cost = round_half_up(await coin_of(ctx.session, ctx.rules, entity) * table.rivalry_drain_pct / PERCENT)
        if cost > 0 and await take_coin(ctx.session, ctx.rules, entity, cost):
            await raise_standing(ctx, side, cost * ctx.rules.reciprocity.give_prestige / PERCENT)


async def exceed(ctx: TickContext, gift: GiftRow, answer: GiftRow) -> None:
    rivalry = await outgiving(ctx, gift, answer)
    if "state" not in gift.locked:
        gift.state = GiftState.EXCEEDED
        gift.settled_epoch = ctx.epoch
    if rivalry:
        await drain_rivals(ctx, gift)
    await record(
        ctx,
        "gift.exceeded",
        roles={IncidentRole.GIVER: gift.giver_node_id, IncidentRole.RECEIVER: gift.receiver_node_id},
        facts={"value": gift.value, "answered": answer.value, "occasion": gift.occasion, "rivalry": int(rivalry)},
        steps=(StepDraft(StepAction.RETURN_GIFT, actor=gift.receiver_node_id, target=gift.giver_node_id, amount=answer.value, unit=FactUnit.COIN),),
    )


async def release_gift_debt(ctx: TickContext, gift: GiftRow) -> bool:
    table = ctx.rules.gifts
    if gift.state not in OBLIGING or "state" in gift.locked:
        return False
    gift.state = GiftState.RELEASED
    gift.settled_epoch = ctx.epoch
    await raise_standing(ctx, gift.giver_node_id, gift.value * ctx.rules.reciprocity.give_prestige / PERCENT)
    await regard(ctx, (gift.receiver_node_id, gift.giver_node_id), table.release_loyalty, MemoryKind.GOODWILL, "released a debt")
    await record(
        ctx,
        "gift.released",
        roles={IncidentRole.GIVER: gift.giver_node_id, IncidentRole.RECEIVER: gift.receiver_node_id},
        facts={"value": gift.value, "occasion": gift.occasion, "loyalty": table.release_loyalty},
        steps=(StepDraft(StepAction.RELEASE, actor=gift.giver_node_id, target=gift.receiver_node_id),),
    )
    return True


async def divine_gift(ctx: TickContext, giver_id: int, receiver_id: int, value: int) -> GiftRow | None:
    if value <= 0:
        return None
    owed = await ctx.session.scalars(
        select(GiftRow)
        .where(GiftRow.giver_node_id == receiver_id, GiftRow.receiver_node_id == giver_id, GiftRow.state.in_(list(OBLIGING)))
        .order_by(GiftRow.id)
    )
    for gift in owed:
        if "state" not in gift.locked:
            gift.state = GiftState.RETURNED
            gift.settled_epoch = ctx.epoch
    return await give(ctx, giver_id, receiver_id, value, GiftOccasion.COURTESY, pay=False)


async def refuse(ctx: TickContext, gift: GiftRow) -> None:
    table = ctx.rules.reciprocity
    if gift.state not in OBLIGING or "state" in gift.locked:
        return
    gift.state = GiftState.REFUSED
    gift.settled_epoch = ctx.epoch
    await regard(ctx, (gift.giver_node_id, gift.receiver_node_id), -table.refusal_insult, MemoryKind.HUMILIATED_ME, "refused a gift")
    await record(
        ctx,
        "gifts.refused",
        roles={IncidentRole.GIVER: gift.giver_node_id, IncidentRole.RECEIVER: gift.receiver_node_id},
        facts={"value": gift.value, "occasion": gift.occasion, "insult": table.refusal_insult},
        steps=(
            StepDraft(StepAction.REFUSE, actor=gift.receiver_node_id, target=gift.giver_node_id, outcome=StepOutcome.REFUSED),
            StepDraft(StepAction.INSULT, actor=gift.receiver_node_id, target=gift.giver_node_id, amount=table.refusal_insult, unit=FactUnit.STANDING),
        ),
    )


async def return_gift(ctx: TickContext, gift: GiftRow, *, value: int | None = None, item_id: int | None = None) -> GiftRow | None:
    table = ctx.rules.reciprocity
    competitive = gift.occasion in COMPETITIVE or gift.state is GiftState.DESTROYED
    wanted = value if value is not None else round_half_up(owed_back(ctx.rules, gift) * (PERCENT + (table.outgive_pct if competitive else 0)) / PERCENT)
    exceeds = wanted >= exceeding(ctx.rules, gift)
    answer = await give(
        ctx,
        gift.receiver_node_id,
        gift.giver_node_id,
        wanted,
        GiftOccasion.FEAST if competitive else GiftOccasion.RETURN,
        item_id=item_id,
        destroyed=competitive and gift.state is GiftState.DESTROYED,
        answers=gift,
        obliging=competitive or exceeds,
    )
    if answer is None:
        return None
    if exceeds:
        await exceed(ctx, gift, answer)
    elif "state" not in gift.locked:
        gift.state = GiftState.RETURNED
        gift.settled_epoch = ctx.epoch
    in_kind = answer.value >= gift.value
    if in_kind:
        await regard(ctx, (gift.giver_node_id, gift.receiver_node_id), table.return_regard, MemoryKind.GOODWILL, "returned a gift in kind")
    await record(
        ctx,
        "gifts.returned",
        roles={IncidentRole.GIVER: gift.giver_node_id, IncidentRole.RECEIVER: gift.receiver_node_id},
        facts={"value": gift.value, "answered": answer.value, "occasion": gift.occasion, "in_kind": int(in_kind)},
        steps=(
            StepDraft(
                StepAction.RETURN_GIFT,
                actor=gift.receiver_node_id,
                target=gift.giver_node_id,
                amount=answer.value,
                unit=FactUnit.COIN,
                outcome=StepOutcome.SUCCESS if in_kind else StepOutcome.PARTIAL,
            ),
        ),
    )
    return answer


async def lapse(ctx: TickContext, gift: GiftRow) -> None:
    table = ctx.rules.reciprocity
    gift.state = GiftState.LAPSED
    gift.settled_epoch = ctx.epoch
    weight = await obligation(ctx, gift.receiver_node_id)
    await raise_standing(ctx, gift.receiver_node_id, -gift.value * table.lapse_prestige / PERCENT * weight)
    await raise_standing(ctx, gift.giver_node_id, gift.value * table.lapse_prestige / PERCENT * weight)
    await record(
        ctx,
        "gifts.lapsed",
        roles={IncidentRole.GIVER: gift.giver_node_id, IncidentRole.RECEIVER: gift.receiver_node_id},
        facts={
            "value": gift.value,
            "occasion": gift.occasion,
            "prestige_lost": round_half_up(gift.value * table.lapse_prestige / PERCENT * weight),
            "in_rivalry": int(gift.occasion in COMPETITIVE),
        },
        steps=(StepDraft(StepAction.DEFAULT, actor=gift.receiver_node_id, target=gift.giver_node_id, outcome=StepOutcome.FAILURE),),
    )


async def settle_due(ctx: TickContext, tally: GiftTally) -> None:
    due = list(
        await ctx.session.scalars(
            select(GiftRow).where(GiftRow.state.in_(list(OBLIGING)), GiftRow.due_epoch.is_not(None), GiftRow.due_epoch <= ctx.epoch).order_by(GiftRow.id)
        )
    )
    for gift in due:
        if held(gift.receiver_node_id) or "state" in gift.locked:
            continue
        receiver = await living_entity(ctx.session, gift.receiver_node_id)
        if receiver is None:
            await lapse(ctx, gift)
            tally.lapsed += 1
            continue
        if await answer_due(ctx, gift, receiver, tally) is not None:
            tally.returned += 1
        elif await relation(ctx.session, ctx.rules, gift.giver_node_id, gift.receiver_node_id) >= ctx.rules.gifts.release_regard and ctx.rng(
            f"gift.release.{gift.id}"
        ).chance(ctx.rules.gifts.release_pct):
            await release_gift_debt(ctx, gift)
            tally.released += 1
        else:
            await lapse(ctx, gift)
            tally.lapsed += 1


async def answer_due(ctx: TickContext, gift: GiftRow, receiver: EntityRow, tally: GiftTally) -> GiftRow | None:
    rival = gift.answers_gift_id is not None and await outgiving(ctx, gift, gift)
    bold = rival or ctx.rng(f"gift.exceed.{gift.id}").chance(ctx.rules.gifts.exceed_pct)
    if bold and await coin_of(ctx.session, ctx.rules, receiver) >= exceeding(ctx.rules, gift):
        answer = await return_gift(ctx, gift, value=exceeding(ctx.rules, gift))
        if answer is not None:
            tally.exceeded += 1
            return answer
    return await return_gift(ctx, gift)


async def rival_at(ctx: TickContext, gathering: GatheringRow) -> int | None:
    guests = await ctx.session.scalars(
        select(GatheringGuestRow.node_id).where(
            GatheringGuestRow.gathering_id == gathering.id, GatheringGuestRow.node_id != gathering.host_node_id, GatheringGuestRow.attended.is_not(False)
        )
    )
    host = await ctx.session.get(EntityRow, gathering.host_node_id)
    best: tuple[int, int] | None = None
    for guest_id in guests:
        guest = await living_entity(ctx.session, guest_id)
        if guest is None or host is None or guest.entity_type is not host.entity_type:
            continue
        rank = (guest.importance or 0, -guest.id)
        if best is None or rank > (best[0], -best[1]):
            best = (rank[0], guest.id)
    return best[1] if best is not None else None


async def potlatch(ctx: TickContext, tally: GiftTally) -> None:
    table = ctx.rules.potlatch
    feasts = await ctx.session.scalars(
        select(GatheringRow)
        .where(GatheringRow.epoch == ctx.epoch, GatheringRow.status == GatheringStatus.HELD, GatheringRow.kind.in_(list(POTLATCH_FEASTS)))
        .order_by(GatheringRow.id)
    )
    for feast in feasts:
        if held(feast.host_node_id):
            continue
        rival = await rival_at(ctx, feast)
        host = await ctx.session.get(EntityRow, feast.host_node_id)
        if rival is None or host is None or not ctx.rng(f"potlatch.{feast.id}").chance(table.claim_pct * await obligation(ctx, host.id)):
            continue
        base = max(table.minimum, round_half_up(await coin_of(ctx.session, ctx.rules, host) * table.stake_pct / PERCENT))
        destroyed = ctx.rng(f"potlatch.destroy.{feast.id}").chance(table.destroy_pct)
        gift = await give(ctx, host.id, rival, base, GiftOccasion.FEAST, destroyed=destroyed)
        if gift is None:
            continue
        tally.potlatches += 1
        await record(
            ctx,
            "potlatch.claimed",
            roles={IncidentRole.HOST: host.id, IncidentRole.OPPONENT: rival},
            facts={"value": gift.value, "destroyed": int(destroyed)},
            steps=(StepDraft(StepAction.SACRIFICE if destroyed else StepAction.GIVE, actor=host.id, target=rival, amount=gift.value, unit=FactUnit.COIN),),
            place=host.location_id,
        )


async def courtesy(ctx: TickContext, tally: GiftTally) -> None:
    table = ctx.rules.reciprocity
    allies = await ctx.session.scalars(select(BondRow).where(BondRow.kind == BondKind.ALLY, BondRow.state == BondState.ACTIVE).order_by(BondRow.id))
    for bond in allies:
        giver, receiver = bond.source_node_id, bond.target_node_id
        if held(giver) or not ctx.rng(f"gift.courtesy.{bond.id}.{ctx.epoch}").chance(table.courtesy_pct * await obligation(ctx, giver)):
            continue
        if await give(ctx, giver, receiver, table.courtesy_value, GiftOccasion.ALLIANCE) is not None:
            tally.given += 1


async def pass_circuit(ctx: TickContext, circuit: CircuitRow, tally: GiftTally) -> bool:
    table = ctx.rules.ceremonial_circuits
    stops = [stop for stop in circuit.stops if await living_entity(ctx.session, stop) is not None]
    if len(stops) < 2 or any(held(stop) for stop in stops):
        return False
    here = stops[circuit.position % len(stops)]
    there = stops[(circuit.position + 1) % len(stops)]
    circuit.position = (circuit.position + 1) % len(stops)
    circuit.passes += 1
    await pass_on(ctx, circuit, here, there)
    await give(ctx, here, there, table.pass_value, GiftOccasion.CIRCUIT, item_id=circuit.item_entity_id, obliging=False, pay=False, circuit_id=circuit.id)
    await raise_standing(ctx, there, table.holder_prestige)
    await regard(ctx, (here, there), table.bond_regard, MemoryKind.GOODWILL, circuit.name)
    tally.passes += 1
    await record(
        ctx,
        "circuits.passed",
        roles={IncidentRole.GIVER: here, IncidentRole.RECEIVER: there, IncidentRole.INSTRUMENT: circuit.item_entity_id},
        facts={"circuit": circuit.name, "passes": circuit.passes, "value": table.pass_value},
    )
    return True


async def pass_on(ctx: TickContext, circuit: CircuitRow, here: int, there: int) -> None:
    held_gift = await ctx.session.scalar(
        select(GiftRow)
        .where(GiftRow.circuit_id == circuit.id, GiftRow.receiver_node_id == here, GiftRow.state.in_(list(HOLDING)))
        .order_by(GiftRow.id.desc())
        .limit(1)
    )
    if held_gift is None or "state" in held_gift.locked:
        return
    held_gift.state = GiftState.PASSED_ON
    held_gift.settled_epoch = ctx.epoch
    await record(
        ctx,
        "gift.passed_on",
        roles={IncidentRole.GIVER: here, IncidentRole.RECEIVER: there},
        facts={"circuit": circuit.name, "value": held_gift.value},
        steps=(StepDraft(StepAction.GIVE, actor=here, target=there, amount=held_gift.value, unit=FactUnit.COIN),),
    )


CIRCUIT_KINDS = (EntityType.SETTLEMENT, EntityType.PEOPLE)


async def gift_partners(ctx: TickContext) -> dict[int, set[int]]:
    returned = select(GiftRow.giver_node_id, GiftRow.receiver_node_id).where(GiftRow.state == GiftState.RETURNED)
    communities = set(await ctx.session.scalars(select(EntityRow.id).where(EntityRow.entity_type.in_(CIRCUIT_KINDS), EntityRow.status == EntityStatus.CANON)))
    partners: dict[int, set[int]] = {}
    for giver, receiver in (await ctx.session.execute(returned)).all():
        if giver in communities and receiver in communities and giver != receiver:
            partners.setdefault(giver, set()).add(receiver)
            partners.setdefault(receiver, set()).add(giver)
    return partners


async def found_circuits(ctx: TickContext, tally: GiftTally) -> None:
    partners = await gift_partners(ctx)
    covered = [set(stops) for stops in await ctx.session.scalars(select(CircuitRow.stops).order_by(CircuitRow.id))]
    begun: set[int] = set()
    for first in sorted(partners):
        for second, third in sorted((b, c) for b in partners[first] for c in partners[first] if first < b < c and c in partners.get(b, set())):
            ring = {first, second, third}
            if ring & begun or any(ring <= stops for stops in covered) or any(held(stop) for stop in ring):
                continue
            if not ctx.rng(f"circuit.found.{first}.{second}.{third}.{ctx.epoch}").chance(ctx.rules.ceremonial_circuits.found_pct):
                continue
            opener = await ctx.session.get(EntityRow, first)
            if opener is None:
                continue
            circuit = CircuitRow(
                name=f"the circuit of {opener.name}",
                item_entity_id=None,
                stops=[first, second, third],
                position=0,
                passes=0,
                started_epoch=ctx.epoch,
                locked=[],
            )
            ctx.session.add(circuit)
            await ctx.session.flush()
            covered.append(ring)
            begun |= ring
            tally.circuits += 1
            await record(
                ctx,
                "circuits.founded",
                roles={IncidentRole.GIVER: first, IncidentRole.MEMBER: [second, third]},
                facts={"circuit": circuit.name, "stops": len(ring)},
            )


async def keep_circuits(ctx: TickContext, tally: GiftTally) -> None:
    await found_circuits(ctx, tally)
    for circuit in list(await ctx.session.scalars(select(CircuitRow).order_by(CircuitRow.id))):
        if "position" not in circuit.locked:
            await pass_circuit(ctx, circuit, tally)


async def offer(ctx: TickContext, community_id: int, god_id: int, value: int) -> DivineDebtRow:
    row = await ctx.session.get(DivineDebtRow, (god_id, community_id))
    if row is None:
        row = DivineDebtRow(god_node_id=god_id, community_entity_id=community_id, offered=0, answered=0, locked=[])
        ctx.session.add(row)
    if "offered" not in row.locked:
        row.offered = (row.offered or 0) + max(0, value)
    row.last_offering_epoch = ctx.epoch
    return row


async def keep_offerings(ctx: TickContext, tally: GiftTally) -> None:
    table = ctx.rules.sacrifice_exchange
    worship = await ctx.session.execute(
        select(BondRow.source_node_id, BondRow.target_node_id)
        .join(EntityRow, EntityRow.id == BondRow.source_node_id)
        .where(
            BondRow.kind == BondKind.WORSHIPS,
            BondRow.state == BondState.ACTIVE,
            EntityRow.status == EntityStatus.CANON,
            EntityRow.entity_type.in_(list(COMMUNITY_TYPES)),
        )
        .order_by(BondRow.source_node_id, BondRow.target_node_id)
    )
    pairs = [(community, god) for community, god in worship.all()]
    tallies = (await tally_epoch(ctx, {god for _, god in pairs})).tallies
    for community_id, god_id in pairs:
        if held(community_id, god_id) or await divine_of(ctx.session, god_id) is None:
            continue
        community = await ctx.session.get(EntityRow, community_id)
        piety = stat_or(community, "piety", table.base_piety) if community is not None else table.base_piety
        row = await offer(ctx, community_id, god_id, round_half_up(table.offering_per_piety * piety / PERCENT))
        tally.offerings += 1
        answered = tallies.get((community_id, god_id))
        if answered is not None and (answered.answered or answered.kind) and "answered" not in row.locked:
            row.answered = (row.answered or 0) + (answered.answered + answered.kind) * table.answer_value
            row.last_answer_epoch = ctx.epoch
        await weigh_debt(ctx, row)


async def weigh_debt(ctx: TickContext, row: DivineDebtRow) -> None:
    table = ctx.rules.sacrifice_exchange
    standing: DivineStandingRow = await standing_row(ctx, row.community_entity_id, row.god_node_id)
    owed = row.offered - row.answered
    if owed > table.debt_at:
        shift(standing, "neglect", (owed - table.debt_at) * table.debt_neglect / PERCENT)
        shift(standing, "love", -(owed - table.debt_at) * table.debt_love / PERCENT)
    elif owed < 0:
        shift(standing, "love", -owed * table.generous_love / PERCENT)
    if row.offered > table.forgive_at and "offered" not in row.locked and "answered" not in row.locked:
        settled = min(row.offered, row.answered)
        row.offered -= settled
        row.answered -= settled


async def kin_line(ctx: TickContext, mortal_id: int) -> int:
    house = await ctx.session.scalar(select(HouseMemberRow.house_entity_id).where(HouseMemberRow.mortal_entity_id == mortal_id).limit(1))
    return house if house is not None else mortal_id


async def pay_union(ctx: TickContext, pair: tuple[EntityRow, EntityRow], value: int, marriage_id: int) -> bool:
    paying, paid = await kin_line(ctx, pair[0].id), await kin_line(ctx, pair[1].id)
    if paying == paid:
        return False
    if await give(ctx, paying, paid, value, GiftOccasion.MARRIAGE, obliging=False) is None:
        return False
    await wed_portion(ctx, paying, paid, marriage_id)
    return True


async def marriage_payments(ctx: TickContext, tally: GiftTally) -> None:
    marriages = await ctx.session.scalars(select(MarriageRow).where(MarriageRow.start_epoch == ctx.epoch).order_by(MarriageRow.id))
    for marriage in marriages:
        first = await living_entity(ctx.session, marriage.first_id)
        second = await living_entity(ctx.session, marriage.second_id)
        if first is None or second is None or held(first.id, second.id):
            continue
        people = await people_of(ctx.session, first)
        custom = await union_of(ctx.session, first)
        if custom is None or custom.exchange is UnionExchange.NONE:
            continue
        if custom.exchange is not UnionExchange.SERVICE:
            pair = payer(custom, first, second)
            if pair is not None and await pay_union(ctx, pair, custom.exchange_value, marriage.id):
                tally.payments += 1
            continue
        system = await ctx.session.get(KinshipSystemRow, people.id) if people is not None else None
        if system is None:
            continue
        leaving, staying = await giver_and_taker(ctx, first, second, system)
        giver_line = await kin_line(ctx, leaving.id)
        if giver_line == await kin_line(ctx, staying.id):
            continue
        if await give(ctx, staying.id, giver_line, custom.exchange_value, GiftOccasion.MARRIAGE, obliging=False, pay=False) is not None:
            tally.payments += 1


def balance(gifts: list[GiftRow], node_id: int) -> int:
    owed = sum(gift.value for gift in gifts if gift.receiver_node_id == node_id and gift.state in OBLIGING)
    owing = sum(gift.value for gift in gifts if gift.giver_node_id == node_id and gift.state in OBLIGING)
    return clamp_int(owing - owed, -(10**9), 10**9)


async def occasion_gift(ctx: TickContext, giver_id: int, receiver_id: int, occasion: GiftOccasion, value: int) -> GiftRow | None:
    if held(giver_id) or await living_entity(ctx.session, receiver_id) is None:
        return None
    return await give(ctx, giver_id, receiver_id, value, occasion, tell=True)


async def birth_gifts(ctx: TickContext, tally: GiftTally) -> None:
    table = ctx.rules.gifts
    births = await ctx.session.execute(
        select(BondRow.source_node_id, BondRow.target_node_id).where(BondRow.kind == BondKind.PARENT_OF, BondRow.epoch == ctx.epoch - 1).order_by(BondRow.id)
    )
    for parent, child in births.all():
        line = await kin_line(ctx, parent)
        if line in {parent, child} or not ctx.rng(f"gift.birth.{child}.{line}").chance(table.birth_gift_pct):
            continue
        if await occasion_gift(ctx, line, child, GiftOccasion.BIRTH, table.occasion_value) is not None:
            await regard(ctx, (child, line), table.patronage_loyalty, MemoryKind.GIFTED_ME, "a gift at birth")
            tally.births += 1


async def funeral_gifts(ctx: TickContext, tally: GiftTally) -> None:
    table = ctx.rules.gifts
    dead = await ctx.session.scalars(
        select(EntityRow).where(EntityRow.entity_type == EntityType.MORTAL, EntityRow.end_epoch == ctx.epoch - 1).order_by(EntityRow.id)
    )
    for mortal in list(dead):
        bereaved = await kin_line(ctx, mortal.id)
        owed = await ctx.session.scalars(
            select(GiftRow)
            .where(GiftRow.giver_node_id.in_([bereaved, mortal.id]), GiftRow.occasion == GiftOccasion.FUNERAL, GiftRow.state.in_(list(OBLIGING)))
            .order_by(GiftRow.id)
        )
        for gift in list(owed):
            if not held(gift.receiver_node_id) and "state" not in gift.locked and await return_gift(ctx, gift) is not None:
                tally.returned += 1
        if bereaved == mortal.id:
            continue
        friends = await ctx.session.scalars(
            select(BondRow.source_node_id)
            .where(BondRow.target_node_id == mortal.id, BondRow.kind.in_(FRIENDS), BondRow.source_node_id != bereaved)
            .order_by(BondRow.source_node_id)
            .limit(table.gifts_per_occasion)
        )
        for friend in list(friends):
            if not ctx.rng(f"gift.funeral.{mortal.id}.{friend}").chance(table.funeral_gift_pct):
                continue
            if await occasion_gift(ctx, friend, bereaved, GiftOccasion.FUNERAL, table.occasion_value) is not None:
                tally.funerals += 1


async def amends(ctx: TickContext, tally: GiftTally) -> None:
    table = ctx.rules.gifts
    feuds = await ctx.session.scalars(select(FeudRow).where(FeudRow.status == FeudStatus.ACTIVE).order_by(FeudRow.id))
    for feud in list(feuds):
        wronger, wronged = feud.second_entity_id, feud.first_entity_id
        if held(wronger, wronged) or not ctx.rng(f"gift.amends.{feud.id}.{ctx.epoch}").chance(table.amends_pct):
            continue
        refused = await refuses(ctx, wronger, wronged)
        gift = await give(ctx, wronger, wronged, table.amends_value, GiftOccasion.AMENDS, tell=True, pay=not refused)
        if gift is None:
            continue
        tally.amends += 1
        if refused:
            if "state" not in gift.locked:
                gift.state = GiftState.REFUSED
            if "intensity" not in feud.locked:
                feud.intensity = clamp_int(feud.intensity + table.amends_grievance_cut // 2, 0, PERCENT)
            continue
        if "grievance" not in feud.locked:
            feud.grievance = clamp_int(feud.grievance - table.amends_grievance_cut, 0, PERCENT)
        if feud.grievance <= 0 and "status" not in feud.locked:
            await end_blood_feud(ctx.session, wronged, wronger, epoch=ctx.epoch, status=FeudStatus.SETTLED)


async def patronage(ctx: TickContext, tally: GiftTally) -> None:
    table = ctx.rules.gifts
    pairs = await ctx.session.execute(
        select(ArtworkProfileRow.patron_entity_id, ArtworkProfileRow.author_entity_id)
        .where(ArtworkProfileRow.patron_entity_id.is_not(None), ArtworkProfileRow.author_entity_id.is_not(None))
        .group_by(ArtworkProfileRow.patron_entity_id, ArtworkProfileRow.author_entity_id)
    )
    for patron, client in pairs.all():
        if patron is None or client is None or patron == client:
            continue
        if not ctx.rng(f"gift.patronage.{patron}.{client}.{ctx.epoch}").chance(table.patronage_pct):
            continue
        if await occasion_gift(ctx, patron, client, GiftOccasion.PATRONAGE, table.occasion_value) is not None:
            await regard(ctx, (client, patron), table.patronage_loyalty, MemoryKind.GOODWILL, "a patron's gift")
            tally.patronage += 1


async def hospitality(ctx: TickContext, tally: GiftTally) -> None:
    table = ctx.rules.gifts
    gatherings = await ctx.session.scalars(
        select(GatheringRow).where(GatheringRow.epoch == ctx.epoch, GatheringRow.status == GatheringStatus.HELD).order_by(GatheringRow.id)
    )
    for gathering in list(gatherings):
        guests = await ctx.session.scalars(
            select(GatheringGuestRow.node_id)
            .where(
                GatheringGuestRow.gathering_id == gathering.id,
                GatheringGuestRow.node_id != gathering.host_node_id,
                GatheringGuestRow.attended.is_not(False),
            )
            .order_by(GatheringGuestRow.node_id)
            .limit(table.gifts_per_occasion)
        )
        for guest in list(guests):
            if not ctx.rng(f"gift.guest.{gathering.id}.{guest}").chance(table.hospitality_pct):
                continue
            if await occasion_gift(ctx, gathering.host_node_id, guest, GiftOccasion.HOSPITALITY, table.occasion_value) is not None:
                tally.hospitality += 1


async def keep_gifts(ctx: TickContext, tally: GiftTally) -> None:
    await settle_due(ctx, tally)
    await birth_gifts(ctx, tally)
    await funeral_gifts(ctx, tally)
    await amends(ctx, tally)
    await patronage(ctx, tally)
    await hospitality(ctx, tally)
    await courtesy(ctx, tally)
    await potlatch(ctx, tally)
    await keep_circuits(ctx, tally)
    await keep_offerings(ctx, tally)
    await marriage_payments(ctx, tally)
    await ctx.session.flush()
