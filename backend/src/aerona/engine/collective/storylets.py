from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.storylets import STORYLETS, Choice, Effect, Storylet
from aerona.constants.units import PERCENT
from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.celestial import WorldRow
from aerona.db.tables.collective import CascadeRow, StoryletRunRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.gatherings import CollectionMemberRow, CollectionRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.db.tables.polity import PolityProfileRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.db.tables.storyteller import StorytellerRow
from aerona.db.tables.warfare import CasusBelliRow
from aerona.db.write_guard import held
from aerona.domain.enums.body import HarmCause
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.collective import CascadeOutcome, CollectiveTrigger, StoryletEffect, StoryletId, StoryletRole, StoryletStatus
from aerona.domain.enums.economy import GoodsFlow
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.gathering import CollectionKind, CollectionRole
from aerona.domain.enums.mind import ValueAxis, ValueHolder
from aerona.domain.enums.polity import ClaimBasis
from aerona.domain.enums.society import Commodity
from aerona.domain.enums.war import CasusBelliKind
from aerona.engine.body.hits import Harm
from aerona.engine.collective.accounts import house_of
from aerona.engine.collective.book import population_of, realm_of_town, ruler_id, shift
from aerona.engine.collective.crowds import stir
from aerona.engine.context import TickContext
from aerona.engine.economy.purse import give_coin, take_coin
from aerona.engine.history.collections import open_collection
from aerona.engine.lifecycle.succession import designate_heir
from aerona.engine.lifecycle.wounds import apply_hits
from aerona.engine.lore.prophecy import Args, met
from aerona.engine.mind.book import stored_values
from aerona.engine.mind.ethics import church_of, culture_of
from aerona.engine.mortal.kin import children_of
from aerona.engine.mortal.standing import add_infamy, add_renown
from aerona.engine.notes import note
from aerona.engine.polity.control import grant_claim
from aerona.engine.primitives.folk import present_among
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.primitives.queries import living_entity
from aerona.engine.primitives.records import retire_in
from aerona.engine.primitives.society import shift_stock, stock
from aerona.engine.primitives.stats import set_stats, stat, stat_or
from aerona.engine.relations.book import ensure_relation
from aerona.engine.relations.book import shift as shift_relation
from aerona.engine.storyteller.drama import pressed, world_drama

R = StoryletRole
E = StoryletEffect
Cast = dict[StoryletRole, int]
ELDER_PCT = 85
CLAIM_STRENGTH = 40
WEIGHT_UNIT = 10


@dataclass
class StoryletTally:
    opened: int = 0
    resolved: int = 0
    by_personality: int = 0
    expired: int = 0
    followed: int = 0


async def mortals_at(ctx: TickContext, place_id: int) -> list[EntityRow]:
    rows = await ctx.session.scalars(
        select(EntityRow)
        .where(EntityRow.entity_type == EntityType.MORTAL, EntityRow.status == EntityStatus.CANON, await present_among(ctx.session, [place_id]))
        .order_by(EntityRow.id)
    )
    return [row for row in rows if not held(row.id)]


async def realms_in(ctx: TickContext, world_id: int) -> list[tuple[EntityRow, PolityProfileRow]]:
    rows = await ctx.session.execute(
        select(EntityRow, PolityProfileRow)
        .join(PolityProfileRow, PolityProfileRow.polity_entity_id == EntityRow.id)
        .where(EntityRow.world_id == world_id, EntityRow.status == EntityStatus.CANON)
        .order_by(EntityRow.id)
    )
    return [(entity, profile) for entity, profile in rows if not held(entity.id)]


async def towns_in(ctx: TickContext, world_id: int) -> list[EntityRow]:
    rows = await ctx.session.scalars(
        select(EntityRow)
        .join(SettlementProfileRow, SettlementProfileRow.settlement_entity_id == EntityRow.id)
        .where(EntityRow.world_id == world_id, EntityRow.status == EntityStatus.CANON)
        .order_by(EntityRow.id)
    )
    return [row for row in rows if not held(row.id)]


async def cast_lost_heir(ctx: TickContext, world_id: int) -> Cast | None:
    for realm, profile in await realms_in(ctx, world_id):
        ruler = await ruler_id(ctx, realm.id)
        if ruler is None or profile.capital_entity_id is None:
            continue
        dynasty = await house_of(ctx, ruler)
        strangers = [row for row in await mortals_at(ctx, profile.capital_entity_id) if row.id != ruler and await house_of(ctx, row.id) != dynasty]
        if strangers:
            claimant = max(strangers, key=lambda row: (stat_or(row, "charisma", 0), -row.id))
            return {R.REALM: realm.id, R.RULER: ruler, R.CLAIMANT: claimant.id}
    return None


async def town_with_lord(ctx: TickContext, town: EntityRow) -> Cast | None:
    realm = await realm_of_town(ctx, town.id)
    ruler = await ruler_id(ctx, realm.polity_entity_id) if realm is not None else None
    if realm is None or ruler is None:
        return None
    return {R.TOWN: town.id, R.REALM: realm.polity_entity_id, R.RULER: ruler}


async def cast_hoarded_store(ctx: TickContext, world_id: int) -> Cast | None:
    for town in await towns_in(ctx, world_id):
        food = await stock(ctx.session, ctx.rules, town.id, Commodity.FOOD)
        if food * PERCENT / max(1, population_of(town)) < ctx.rules.collective_behaviour.famine_food:
            return await town_with_lord(ctx, town)
    return None


async def cast_beast_demand(ctx: TickContext, world_id: int) -> Cast | None:
    rows = await ctx.session.execute(
        select(BondRow.source_node_id, BondRow.target_node_id)
        .join(EntityRow, EntityRow.id == BondRow.target_node_id)
        .where(BondRow.kind == BondKind.HUNTS, BondRow.state == BondState.ACTIVE, EntityRow.world_id == world_id)
        .order_by(BondRow.id)
    )
    for beast_id, town_id in rows:
        beast, town = await living_entity(ctx.session, beast_id), await living_entity(ctx.session, town_id)
        if beast is None or town is None or held(beast.id) or await ctx.session.get(SettlementProfileRow, town.id) is None:
            continue
        cast = await town_with_lord(ctx, town)
        if cast is not None:
            return {**cast, R.BEAST: beast.id}
    return None


async def cast_forbidden_text(ctx: TickContext, world_id: int) -> Cast | None:
    scholar = await ctx.session.scalar(
        select(MortalProfileRow.entity_id)
        .join(EntityRow, EntityRow.id == MortalProfileRow.entity_id)
        .where(EntityRow.world_id == world_id, EntityRow.status == EntityStatus.CANON, MortalProfileRow.education > PERCENT // 2)
        .order_by(MortalProfileRow.education.desc(), MortalProfileRow.entity_id)
        .limit(1)
    )
    text = await ctx.session.scalar(
        select(EntityRow.id)
        .where(EntityRow.world_id == world_id, EntityRow.entity_type == EntityType.KNOWLEDGE, EntityRow.status == EntityStatus.CANON)
        .order_by(EntityRow.id)
        .limit(1)
    )
    if scholar is None or text is None or held(scholar) or held(text):
        return None
    people = await culture_of(ctx.session, scholar)
    cults = await church_of(ctx.session, people) if people is not None and people.entity_type is EntityType.PEOPLE else []
    if not cults:
        return None
    return {R.SCHOLAR: scholar, R.TEXT: text, R.CULT: cults[0]}


async def cast_defiled_site(ctx: TickContext, world_id: int) -> Cast | None:
    rows = await ctx.session.scalars(
        select(CascadeRow)
        .join(EntityRow, EntityRow.id == CascadeRow.settlement_entity_id)
        .where(EntityRow.world_id == world_id, CascadeRow.outcome == CascadeOutcome.MOB, CascadeRow.epoch >= ctx.epoch - 1)
        .order_by(CascadeRow.id)
    )
    for cascade in rows:
        town = await living_entity(ctx.session, cascade.settlement_entity_id)
        cult = await ctx.session.scalar(
            select(EntityRow.id).where(
                EntityRow.entity_type == EntityType.CULT, EntityRow.status == EntityStatus.CANON, EntityRow.location_id == cascade.settlement_entity_id
            )
        )
        site = await ctx.session.scalar(
            select(EntityRow.id)
            .where(EntityRow.entity_type == EntityType.STRUCTURE, EntityRow.status == EntityStatus.CANON, EntityRow.location_id == cascade.settlement_entity_id)
            .order_by(EntityRow.id)
            .limit(1)
        )
        cast = await town_with_lord(ctx, town) if town is not None else None
        if cast is not None and cult is not None and site is not None and not held(site):
            return {**cast, R.CULT: cult, R.SITE: site}
    return None


async def cast_wedding_challenge(ctx: TickContext, world_id: int) -> Cast | None:
    weddings = await ctx.session.scalars(
        select(CollectionRow.id).where(
            CollectionRow.world_id == world_id, CollectionRow.kind == CollectionKind.WEDDING, CollectionRow.start_epoch >= ctx.epoch - 1
        )
    )
    for wedding in weddings:
        guests = [
            node
            for node in await ctx.session.scalars(
                select(CollectionMemberRow.node_id).where(CollectionMemberRow.collection_id == wedding).order_by(CollectionMemberRow.node_id)
            )
            if (row := await living_entity(ctx.session, node)) is not None and row.entity_type is EntityType.MORTAL and not held(node)
        ]
        if len(guests) >= 2:
            return {R.CHALLENGER: guests[-1], R.CHALLENGED: guests[0]}
    return None


async def cast_dying_ruler(ctx: TickContext, world_id: int) -> Cast | None:
    for realm, _ in await realms_in(ctx, world_id):
        ruler_key = await ruler_id(ctx, realm.id)
        ruler = await living_entity(ctx.session, ruler_key) if ruler_key is not None else None
        if ruler is None or held(ruler.id):
            continue
        age, span = stat_or(ruler, "age", 0), stat_or(ruler, "lifespan", 0)
        if span <= 0 or age * PERCENT < span * ELDER_PCT:
            continue
        heirs = [row for child in await children_of(ctx.session, ruler.id) if (row := await living_entity(ctx.session, child)) is not None and not held(row.id)]
        if len(heirs) >= 2:
            elder, younger = sorted(heirs, key=lambda row: (-stat_or(row, "age", 0), row.id))[:2]
            return {R.RULER: ruler.id, R.REALM: realm.id, R.ELDER_HEIR: elder.id, R.YOUNGER_HEIR: younger.id}
    return None


async def cast_insulted_envoy(ctx: TickContext, world_id: int) -> Cast | None:
    realms = await realms_in(ctx, world_id)
    for host, profile in realms:
        ruler = await ruler_id(ctx, host.id)
        if ruler is None or profile.capital_entity_id is None:
            continue
        for guest in await mortals_at(ctx, profile.capital_entity_id):
            home = await ctx.session.get(MortalProfileRow, guest.id)
            if home is not None and home.polity_id not in {None, host.id} and not held(home.polity_id):
                return {R.ENVOY: guest.id, R.REALM: home.polity_id, R.HOST_REALM: host.id, R.RULER: ruler}
    return None


CASTERS: dict[StoryletId, Callable[[TickContext, int], Awaitable[Cast | None]]] = {
    StoryletId.LOST_HEIR: cast_lost_heir,
    StoryletId.HOARDED_STORE: cast_hoarded_store,
    StoryletId.BEAST_DEMAND: cast_beast_demand,
    StoryletId.FORBIDDEN_TEXT: cast_forbidden_text,
    StoryletId.DEFILED_SITE: cast_defiled_site,
    StoryletId.WEDDING_CHALLENGE: cast_wedding_challenge,
    StoryletId.DYING_RULER: cast_dying_ruler,
    StoryletId.INSULTED_ENVOY: cast_insulted_envoy,
}


async def conditions_hold(ctx: TickContext, spec: Storylet, cast: Cast) -> bool:
    for condition in spec.conditions:
        node = cast.get(condition.role)
        if node is None:
            return False
        args: Args = {condition.key: node}
        if condition.event is not None:
            args["event"] = condition.event
        if not await met(ctx, condition.predicate, args, 0):
            return False
    return True


async def names(session: AsyncSession, cast: Cast) -> dict[str, str]:
    found: dict[str, str] = {}
    for role, node in cast.items():
        row = await session.get(EntityRow, node)
        found[role.value] = row.name if row is not None else "someone"
    return found


async def situation(session: AsyncSession, run: StoryletRunRow) -> str:
    step = STORYLETS[run.storylet].steps[run.step]
    return step.text.format(**await names(session, cast_of(run)))


async def choice_texts(session: AsyncSession, run: StoryletRunRow) -> list[str]:
    known = await names(session, cast_of(run))
    return [choice.text.format(**known) for choice in STORYLETS[run.storylet].steps[run.step].choices]


def cast_of(run: StoryletRunRow) -> Cast:
    return {StoryletRole(role): node for role, node in run.cast.items()}


async def begin(
    ctx: TickContext, storylet: StoryletId, world_id: int | None, cast: Cast, *, step: int = 0, follows: int | None = None, delay: int = 0
) -> StoryletRunRow:
    spec = STORYLETS[storylet]
    table = ctx.rules.storylets
    opened = ctx.epoch + delay
    run = StoryletRunRow(
        storylet=storylet,
        world_id=world_id,
        cast={role.value: node for role, node in cast.items()},
        status=StoryletStatus.OPEN,
        chooser_node_id=cast.get(spec.chooser),
        step=step,
        follows_run_id=follows,
        due_epoch=opened + table.open_epochs,
        opened_epoch=opened,
        locked=[],
    )
    ctx.session.add(run)
    await ctx.session.flush()
    previous = await ctx.session.get(StoryletRunRow, follows) if follows is not None else None
    if previous is not None and previous.collection_id is not None:
        run.collection_id = previous.collection_id
    else:
        members = {node: CollectionRole.LEADER if role is spec.chooser else CollectionRole.MEMBER for role, node in cast.items()}
        collection = await open_collection(
            ctx, CollectionKind.STORYLET, world_id=world_id, members=members, name=spec.title, source_key=f"storylet.{storylet.value}"
        )
        run.collection_id = collection.id if collection is not None else None
    if delay == 0:
        await note(ctx, await situation(ctx.session, run), key=f"storylet.{storylet.value}", ids=sorted(set(cast.values())))
    return run


async def worlds(ctx: TickContext) -> list[int]:
    return [world for world in await ctx.session.scalars(select(WorldRow.id).order_by(WorldRow.id)) if not held(world)]


async def boost_of(ctx: TickContext, world_id: int) -> int:
    row = await ctx.session.get(StorytellerRow, world_id)
    return row.boost_pct if row is not None else 0


async def cooling(ctx: TickContext, world_id: int, storylet: StoryletId) -> bool:
    last = await ctx.session.scalar(
        select(func.max(StoryletRunRow.opened_epoch)).where(StoryletRunRow.world_id == world_id, StoryletRunRow.storylet == storylet, StoryletRunRow.step == 0)
    )
    return last is not None and ctx.epoch - last < ctx.rules.storylets.cooldown_epochs


async def open_storylets(ctx: TickContext, tally: StoryletTally) -> None:
    table = ctx.rules.storylets
    for world_id in await worlds(ctx):
        waiting = await ctx.session.scalar(
            select(func.count()).select_from(StoryletRunRow).where(StoryletRunRow.world_id == world_id, StoryletRunRow.status == StoryletStatus.OPEN)
        )
        if (waiting or 0) >= table.max_open:
            continue
        boost = await boost_of(ctx, world_id)
        for storylet in StoryletId:
            spec = STORYLETS[storylet]
            chance = pressed(ctx, table.chance_pct * spec.weight / WEIGHT_UNIT * (1 + boost / PERCENT), await world_drama(ctx, world_id, storylet))
            if await cooling(ctx, world_id, storylet) or not ctx.rng(f"storylet.{world_id}.{storylet.value}.{ctx.epoch}").chance(chance):
                continue
            cast = await CASTERS[storylet](ctx, world_id)
            if cast is None or not await conditions_hold(ctx, spec, cast):
                continue
            await begin(ctx, storylet, world_id, cast)
            tally.opened += 1
            break


def personal_score(choice: Choice, values: Mapping[ValueAxis, int]) -> float:
    return sum(values.get(axis, 0) * weight for axis, weight in choice.appeals.items()) / PERCENT


async def by_personality(ctx: TickContext, run: StoryletRunRow) -> int:
    choices = STORYLETS[run.storylet].steps[run.step].choices
    values = await stored_values(ctx.session, ValueHolder.PERSONAL, run.chooser_node_id) if run.chooser_node_id is not None else {}
    rng = ctx.rng(f"storylet_whim.{run.id}")
    scored = [(personal_score(choice, values) + rng.uniform(-5, 5), -index) for index, choice in enumerate(choices)]
    return -max(scored)[1]


async def node(ctx: TickContext, cast: Cast, role: StoryletRole | None) -> EntityRow | None:
    found = cast.get(role) if role is not None else None
    row = await living_entity(ctx.session, found) if found is not None else None
    return row if row is not None and not held(row.id) else None


async def town_profile(ctx: TickContext, cast: Cast, role: StoryletRole) -> SettlementProfileRow | None:
    found = cast.get(role)
    return await ctx.session.get(SettlementProfileRow, found) if found is not None and not held(found) else None


async def realm_profile(ctx: TickContext, cast: Cast, role: StoryletRole) -> PolityProfileRow | None:
    found = cast.get(role)
    return await ctx.session.get(PolityProfileRow, found) if found is not None and not held(found) else None


async def duel_between(ctx: TickContext, first: EntityRow, second: EntityRow) -> None:
    rng = ctx.rng(f"storylet_duel.{first.id}.{second.id}.{ctx.epoch}")
    might = stat_or(first, "strength", 50) + stat_or(first, "agility", 50)
    other = stat_or(second, "strength", 50) + stat_or(second, "agility", 50)
    loser, winner = (second, first) if rng.chance(might * PERCENT / max(1, might + other)) else (first, second)
    await apply_hits(ctx, loser, Harm(stat_or(loser, "hp", 20) / 2, HarmCause.DUEL, f"wounded in a duel with {winner.name}", killer_id=winner.id), lethal=False)
    await add_renown(ctx.session, winner.id, 5, ctx.epoch, rules=ctx.rules)
    await open_collection(ctx, CollectionKind.DUEL, world_id=first.world_id, members={winner.id: CollectionRole.WINNER, loser.id: CollectionRole.LOSER})


async def apply_effect(ctx: TickContext, effect: Effect, cast: Cast) -> None:
    kind = effect.kind
    if kind in {E.UNREST, E.ORDER}:
        town = await town_profile(ctx, cast, effect.role)
        if town is not None:
            shift(town, "unrest" if kind is E.UNREST else "public_order", effect.amount)
    elif kind is E.LEGITIMACY:
        realm = await realm_profile(ctx, cast, effect.role)
        if realm is not None:
            shift(realm, "legitimacy", effect.amount)
    elif kind is E.ANGER:
        mood = await stir(ctx, cast.get(effect.role), CollectiveTrigger.RUMOUR, force=0)
        if mood is not None:
            shift(mood, "anger", effect.amount)
    elif kind is E.FOOD:
        town_id = cast.get(effect.role)
        if town_id is not None and not held(town_id):
            flow = GoodsFlow.AID if effect.amount > 0 else GoodsFlow.LOSS
            await shift_stock(ctx.session, ctx.rules, town_id, Commodity.FOOD, effect.amount, epoch=ctx.epoch, flow=flow)
    else:
        await apply_personal(ctx, effect, cast)


async def pay(ctx: TickContext, effect: Effect, target: EntityRow, other: EntityRow | None) -> None:
    if effect.amount >= 0:
        await give_coin(ctx.session, ctx.rules, target, effect.amount)
    else:
        await take_coin(ctx.session, ctx.rules, target, -effect.amount)


async def acclaim(ctx: TickContext, effect: Effect, target: EntityRow, other: EntityRow | None) -> None:
    await add_renown(ctx.session, target.id, effect.amount, ctx.epoch, rules=ctx.rules)


async def shame(ctx: TickContext, effect: Effect, target: EntityRow, other: EntityRow | None) -> None:
    await add_infamy(ctx.session, target.id, effect.amount, ctx.epoch, rules=ctx.rules)


async def befriend(ctx: TickContext, effect: Effect, target: EntityRow, other: EntityRow | None) -> None:
    row = await ensure_relation(ctx.session, target.id, other.id, ctx.epoch) if other is not None else None
    if row is not None:
        shift_relation(ctx.rules, row, ctx.epoch, friendship=effect.amount, familiarity=5)


async def wound(ctx: TickContext, effect: Effect, target: EntityRow, other: EntityRow | None) -> None:
    await apply_hits(ctx, target, Harm(effect.amount, HarmCause.QUEST, "hurt in a hard choice"), lethal=False)


async def zeal(ctx: TickContext, effect: Effect, target: EntityRow, other: EntityRow | None) -> None:
    shift_zeal(target, effect.amount)


async def destroy(ctx: TickContext, effect: Effect, target: EntityRow, other: EntityRow | None) -> None:
    await retire_in(ctx, target, "destroyed by a hard choice", EntityStatus.DESTROYED)


async def fight(ctx: TickContext, effect: Effect, target: EntityRow, other: EntityRow | None) -> None:
    if other is not None:
        await duel_between(ctx, target, other)


PERSONAL: dict[StoryletEffect, Callable[[TickContext, Effect, EntityRow, EntityRow | None], Awaitable[None]]] = {
    E.COIN: pay,
    E.RENOWN: acclaim,
    E.INFAMY: shame,
    E.FRIENDSHIP: befriend,
    E.WOUND: wound,
    E.PIETY: zeal,
    E.DESTROY: destroy,
    E.DUEL: fight,
}


async def apply_personal(ctx: TickContext, effect: Effect, cast: Cast) -> None:
    target = await node(ctx, cast, effect.role)
    if target is None:
        return
    other = await node(ctx, cast, effect.other)
    handler = PERSONAL.get(effect.kind)
    if handler is not None:
        await handler(ctx, effect, target, other)
    else:
        await apply_bond(ctx, effect, target, other)


def shift_zeal(cult: EntityRow, amount: int) -> None:
    set_stats(cult, zeal=clamp_int((stat(cult, "zeal") or 0) + amount, 0, PERCENT))


async def apply_bond(ctx: TickContext, effect: Effect, target: EntityRow, other: EntityRow | None) -> None:
    if other is None:
        return
    try:
        if effect.kind is E.HEIR:
            await designate_heir(ctx, other.id, target.id)
        elif effect.kind is E.CLAIM:
            await grant_claim(ctx, target.id, other.id, strength=CLAIM_STRENGTH, basis=ClaimBasis.FABRICATED)
        elif effect.kind is E.WAR:
            ctx.session.add(
                CasusBelliRow(
                    holder_entity_id=target.id,
                    target_entity_id=other.id,
                    kind=CasusBelliKind.INSULT,
                    justification=PERCENT // 2,
                    since_epoch=ctx.epoch,
                    locked=[],
                )
            )
            await ctx.session.flush()
    except (NotFoundError, ValidationFailedError):
        return


async def resolve(ctx: TickContext, run: StoryletRunRow, choice_index: int, tally: StoryletTally, *, by: str) -> Choice | None:
    choices = STORYLETS[run.storylet].steps[run.step].choices
    if run.status is not StoryletStatus.OPEN or not 0 <= choice_index < len(choices):
        return None
    choice = choices[choice_index]
    cast = cast_of(run)
    for effect in choice.effects:
        await apply_effect(ctx, effect, cast)
    run.status, run.choice, run.resolved_epoch = StoryletStatus.RESOLVED, choice_index, ctx.epoch
    tally.resolved += 1
    known = await names(ctx.session, cast)
    chooser = known.get(STORYLETS[run.storylet].chooser.value, "someone")
    await note(ctx, f"{chooser} chose: {choice.text.format(**known)}.", key=f"storylet.{run.storylet.value}.{by}", ids=sorted(set(cast.values())))
    if choice.follow is not None:
        await begin(ctx, choice.follow, run.world_id, cast, step=choice.step, follows=run.id, delay=ctx.rules.storylets.follow_epochs)
        tally.followed += 1
    await ctx.session.flush()
    return choice


async def announce(ctx: TickContext, tally: StoryletTally) -> None:
    rows = await ctx.session.scalars(
        select(StoryletRunRow).where(
            StoryletRunRow.status == StoryletStatus.OPEN, StoryletRunRow.opened_epoch == ctx.epoch, StoryletRunRow.follows_run_id.is_not(None)
        )
    )
    for run in rows:
        await note(ctx, await situation(ctx.session, run), key=f"storylet.{run.storylet.value}", ids=sorted(set(cast_of(run).values())))


async def settle_due(ctx: TickContext, tally: StoryletTally) -> None:
    rows = await ctx.session.scalars(
        select(StoryletRunRow).where(StoryletRunRow.status == StoryletStatus.OPEN, StoryletRunRow.due_epoch <= ctx.epoch).order_by(StoryletRunRow.id)
    )
    for run in list(rows):
        if held(run.world_id) or "status" in run.locked:
            continue
        chooser = await living_entity(ctx.session, run.chooser_node_id) if run.chooser_node_id is not None else None
        if chooser is None:
            run.status, run.resolved_epoch = StoryletStatus.EXPIRED, ctx.epoch
            tally.expired += 1
            continue
        if await resolve(ctx, run, await by_personality(ctx, run), tally, by="personality") is not None:
            tally.by_personality += 1
