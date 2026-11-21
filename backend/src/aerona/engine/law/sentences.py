from collections.abc import Awaitable, Callable, Mapping

from sqlalchemy import select

from aerona.catalog.crimes import PUNISHMENTS, TRIALS
from aerona.constants.units import PERCENT
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.db.tables.polity import OfficeRow, PolityProfileRow
from aerona.db.tables.powers import PowerRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.entity import EntityFlag, EntityStatus, EntityType
from aerona.domain.enums.justice import TrialKind
from aerona.domain.enums.mind import ValueAxis
from aerona.domain.enums.mortal import PunishmentKind
from aerona.domain.enums.powers import PowerState
from aerona.domain.enums.society import SocialClass
from aerona.engine.context import TickContext
from aerona.engine.economy.purse import take_coin
from aerona.engine.law.prisons import imprison
from aerona.engine.mind.book import values_for
from aerona.engine.mortal.standing import add_infamy, add_stress, add_wealth, shift_standing
from aerona.engine.primitives.numbers import clamp_int, clamp_percent
from aerona.engine.primitives.queries import add_flag

Bear = Callable[[TickContext, EntityRow, int | None], Awaitable[None]]
RANKED = frozenset({SocialClass.NOBLE, SocialClass.OFFICIAL, SocialClass.PRIEST, SocialClass.SCRIBE, SocialClass.PROFESSIONAL})
LEGITIMACY_SPAN = 10


async def restore(ctx: TickContext, culprit: EntityRow, _case: int | None) -> None:
    await add_wealth(ctx.session, culprit.id, -ctx.rules.sentences.restitution_wealth, ctx.epoch)


async def compensate(ctx: TickContext, culprit: EntityRow, _case: int | None) -> None:
    await add_wealth(ctx.session, culprit.id, -ctx.rules.sentences.compensation_wealth, ctx.epoch)


async def labour(ctx: TickContext, culprit: EntityRow, case: int | None) -> None:
    if await imprison(ctx, culprit, case_id=case, term=ctx.rules.sentences.labour_term) is None:
        await add_stress(ctx.session, culprit.id, ctx.rules.sentences.work_stress * 2, ctx.epoch)


async def bind(ctx: TickContext, culprit: EntityRow, _case: int | None) -> None:
    culprit.social_class = SocialClass.SERF_OR_SLAVE


async def outlaw(ctx: TickContext, culprit: EntityRow, _case: int | None) -> None:
    culprit.social_class = SocialClass.OUTCAST
    await add_infamy(ctx.session, culprit.id, ctx.rules.sentences.outlawry_infamy, ctx.epoch, rules=ctx.rules)


async def confiscate(ctx: TickContext, culprit: EntityRow, _case: int | None) -> None:
    await add_wealth(ctx.session, culprit.id, -PERCENT, ctx.epoch)


async def unrank(ctx: TickContext, culprit: EntityRow, _case: int | None) -> None:
    if culprit.social_class in RANKED:
        culprit.social_class = SocialClass.CITIZEN
    for office in list(await ctx.session.scalars(select(OfficeRow).where(OfficeRow.holder_entity_id == culprit.id))):
        if not held(office.polity_entity_id):
            office.holder_entity_id = None


async def cast_out(ctx: TickContext, culprit: EntityRow, _case: int | None) -> None:
    for bond in list(
        await ctx.session.scalars(
            select(BondRow).where(BondRow.source_node_id == culprit.id, BondRow.kind == BondKind.WORSHIPS, BondRow.state == BondState.ACTIVE)
        )
    ):
        bond.state, bond.closed_epoch, bond.closed_reason = BondState.PAST, ctx.epoch, "cast out by the law"
    await shift_standing(ctx.session, culprit, "piety", -ctx.rules.sentences.excommunication_piety, ctx.epoch, default=0)


async def atone(ctx: TickContext, culprit: EntityRow, _case: int | None) -> None:
    await add_stress(ctx.session, culprit.id, ctx.rules.sentences.work_stress, ctx.epoch)
    await shift_standing(ctx.session, culprit, "piety", ctx.rules.sentences.penance_piety, ctx.epoch, default=0)


async def elsewhere(ctx: TickContext, culprit: EntityRow, *, far: bool) -> EntityRow | None:
    query = select(EntityRow).where(
        EntityRow.entity_type == EntityType.SETTLEMENT, EntityRow.status == EntityStatus.CANON, EntityRow.id != (culprit.location_id or 0)
    )
    here = await ctx.session.get(EntityRow, culprit.location_id) if culprit.location_id is not None else None
    if far:
        query = query.where(EntityRow.world_id != (here.world_id if here is not None else culprit.world_id))
    elif here is not None and here.affiliated_entity_id is not None:
        query = query.where(EntityRow.affiliated_entity_id == here.affiliated_entity_id)
    places = list(await ctx.session.scalars(query.order_by(EntityRow.id)))
    return ctx.rng(f"exile.{culprit.id}.{far}").pick(places) if places else None


async def banish(ctx: TickContext, culprit: EntityRow, _case: int | None) -> None:
    place = await elsewhere(ctx, culprit, far=False)
    culprit.location_id = place.id if place is not None else None
    if place is None:
        await add_flag(ctx.session, culprit.id, EntityFlag.EXILE, ctx.epoch)


async def transport(ctx: TickContext, culprit: EntityRow, _case: int | None) -> None:
    place = await elsewhere(ctx, culprit, far=True) or await elsewhere(ctx, culprit, far=False)
    if place is None:
        culprit.location_id = None
        await add_flag(ctx.session, culprit.id, EntityFlag.EXILE, ctx.epoch)
        return
    culprit.location_id, culprit.world_id = place.id, place.world_id


async def confine(ctx: TickContext, culprit: EntityRow, _case: int | None) -> None:
    await add_stress(ctx.session, culprit.id, ctx.rules.sentences.work_stress, ctx.epoch)
    await shift_standing(ctx.session, culprit, "renown", -ctx.rules.sentences.arrest_renown, ctx.epoch, default=0)


async def watch(ctx: TickContext, culprit: EntityRow, _case: int | None) -> None:
    await add_infamy(ctx.session, culprit.id, ctx.rules.sentences.probation_infamy, ctx.epoch, rules=ctx.rules)


async def reeducate(ctx: TickContext, culprit: EntityRow, case: int | None) -> None:
    await imprison(ctx, culprit, case_id=case, term=ctx.rules.sentences.reeducation_term)
    profile = await ctx.session.get(MortalProfileRow, culprit.id)
    if profile is not None and "loyalty_liege" not in profile.locked:
        profile.loyalty_liege = clamp_percent(profile.loyalty_liege + ctx.rules.sentences.reeducation_loyalty)


async def serve(ctx: TickContext, culprit: EntityRow, _case: int | None) -> None:
    await add_stress(ctx.session, culprit.id, ctx.rules.sentences.work_stress, ctx.epoch)
    town = await ctx.session.get(SettlementProfileRow, culprit.location_id) if culprit.location_id is not None else None
    if town is not None and not held(town.settlement_entity_id) and "sanitation" not in town.locked:
        town.sanitation = clamp_percent(town.sanitation + ctx.rules.sentences.work_gain)


async def dampen(ctx: TickContext, culprit: EntityRow, _case: int | None) -> None:
    for power in list(await ctx.session.scalars(select(PowerRow).where(PowerRow.holder_node_id == culprit.id, PowerRow.state == PowerState.ACTIVE))):
        if "state" not in power.locked:
            power.state = PowerState.SUPPRESSED


SENTENCES: Mapping[PunishmentKind, Bear] = {
    PunishmentKind.RESTITUTION: restore,
    PunishmentKind.COMPENSATION: compensate,
    PunishmentKind.PENAL_LABOUR: labour,
    PunishmentKind.SERVITUDE: bind,
    PunishmentKind.OUTLAWRY: outlaw,
    PunishmentKind.CONFISCATION: confiscate,
    PunishmentKind.LOSS_OF_RANK: unrank,
    PunishmentKind.EXCOMMUNICATION: cast_out,
    PunishmentKind.PENANCE: atone,
    PunishmentKind.BANISHMENT_FROM_PLACE: banish,
    PunishmentKind.HOUSE_ARREST: confine,
    PunishmentKind.PROBATION: watch,
    PunishmentKind.REEDUCATION: reeducate,
    PunishmentKind.TRANSPORTATION: transport,
    PunishmentKind.COMMUNITY_WORK: serve,
    PunishmentKind.DAMPENING: dampen,
}


async def answer(ctx: TickContext, polity_id: int | None, town_id: int | None, *, cost: int, leans: tuple[int, int, int], fairness: int) -> None:
    polity = await ctx.session.get(EntityRow, polity_id) if polity_id is not None else None
    if polity is None or held(polity.id):
        return
    table = ctx.rules.sentences
    if cost:
        await take_coin(ctx.session, ctx.rules, polity, cost * table.cost_coin)
    profile = await ctx.session.get(PolityProfileRow, polity.id)
    if profile is None or "legitimacy" in profile.locked or town_id is None:
        return
    values = await values_for(ctx.session, town_id)
    mercy, tradition, order = leans
    weights = ((ValueAxis.MERCY, mercy), (ValueAxis.TRADITION, tradition), (ValueAxis.LAW, order))
    lean = sum(values.get(axis, 0) * weight for axis, weight in weights) // PERCENT + fairness - PERCENT // 2
    profile.legitimacy = clamp_percent(profile.legitimacy + clamp_int(lean * table.legitimacy_step // PERCENT, -LEGITIMACY_SPAN, LEGITIMACY_SPAN))


async def weigh(ctx: TickContext, punishment: PunishmentKind, town_id: int | None, polity_id: int | None) -> None:
    spec = PUNISHMENTS[punishment]
    town = await ctx.session.get(SettlementProfileRow, town_id) if town_id is not None else None
    if town is not None and not held(town.settlement_entity_id) and "crime" not in town.locked:
        town.crime = clamp_percent(town.crime - (spec.deterrence - spec.recidivism) * ctx.rules.sentences.deterrence_pct // PERCENT)
    await answer(ctx, polity_id, town_id, cost=spec.cost, leans=(spec.mercy, spec.tradition, spec.order), fairness=PERCENT // 2)


async def weigh_trial(ctx: TickContext, trial: TrialKind, town_id: int | None, polity_id: int | None) -> None:
    spec = TRIALS[trial]
    await answer(ctx, polity_id, town_id, cost=spec.cost, leans=(spec.mercy, spec.tradition, spec.order), fairness=spec.fairness)
