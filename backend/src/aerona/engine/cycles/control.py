from collections.abc import Sequence

from aerona.constants.units import PERCENT
from aerona.core.errors import ValidationFailedError
from aerona.db.base import Base
from aerona.db.tables.cycles import (
    ALLIANCE_FIELDS,
    ASABIYYA_FIELDS,
    CAMP_FIELDS,
    CASTE_FIELDS,
    CHALLENGE_FIELDS,
    CIRCUIT_FIELDS,
    CONFEDERATION_FIELDS,
    DEBT_FIELDS,
    GIFT_FIELDS,
    INDENTURE_FIELDS,
    KINSHIP_FIELDS,
    LEGACY_FIELDS,
    MANUMISSION_FIELDS,
    MARKET_FIELDS,
    PLAN_FIELDS,
    READING_FIELDS,
    REPRODUCTION_FIELDS,
    STRESS_FIELDS,
    AsabiyyaRow,
    CampRow,
    ChallengeRow,
    CircuitRow,
    ConfederationRow,
    DivineDebtRow,
    GiftRow,
    IndentureRow,
    KinshipSystemRow,
    LegacyTraitRow,
    LongPlanRow,
    ManumissionRow,
    MarriageAllianceRow,
    MortalCasteRow,
    PeopleReproductionRow,
    PolityStressRow,
    SlaveMarketRow,
    StressReadingRow,
)
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.polity import PolityProfileRow
from aerona.db.tables.society import CommunitySocietyRow
from aerona.domain.enums.cycles import (
    ChallengeKind,
    GiftOccasion,
    LabourRegime,
    LegacyKind,
    LongPlanKind,
    ManumissionPath,
    ReproductiveCaste,
)
from aerona.domain.enums.entity import EntityType
from aerona.engine.collective.control import of_type, saved
from aerona.engine.context import TickContext
from aerona.engine.cycles.asabiyya import asabiyya_row
from aerona.engine.cycles.challenge import answer, response_to
from aerona.engine.cycles.gifts import GiftTally, give, pass_circuit, refuse, return_gift
from aerona.engine.cycles.indenture import freed_class, record_manumission
from aerona.engine.cycles.legacy import apply_legacy
from aerona.engine.cycles.nomads import NomadTally, circuit_for, move
from aerona.engine.cycles.plans import PlanTally, complete
from aerona.engine.cycles.stress import stress_row
from aerona.engine.demography.bound import BOUND, move_people, sync_bound_share
from aerona.engine.demography.cohorts import cohorts_of
from aerona.engine.divine.control import apply
from aerona.engine.divine.gods import divine_of
from aerona.engine.gatherings.control import Values, allowed, found
from aerona.engine.notes import note
from aerona.engine.primitives.distance import RegionAtlas

POLITIES = frozenset({EntityType.POLITY})
PEOPLES = frozenset({EntityType.PEOPLE})
TOWNS = frozenset({EntityType.SETTLEMENT})
MORTALS = frozenset({EntityType.MORTAL})
SOLIDARY = frozenset({EntityType.PEOPLE, EntityType.POLITY})
COMMUNITIES = frozenset({EntityType.SETTLEMENT, EntityType.PEOPLE})


async def node_exists(ctx: TickContext, node_id: int, label: str) -> None:
    if await ctx.session.get(EntityRow, node_id) is None and await divine_of(ctx.session, node_id) is None:
        raise ValidationFailedError(f"No such {label}.")


async def put_values[Row: Base](ctx: TickContext, row: Row, values: Values, fields: tuple[str, ...], label: str) -> Row:
    apply(row, allowed(values, fields, label), [])
    await ctx.session.flush()
    return row


async def set_stress(ctx: TickContext, polity_id: int, values: Values) -> PolityStressRow:
    await of_type(ctx, polity_id, POLITIES, "a realm")
    return await put_values(ctx, await stress_row(ctx, polity_id), values, STRESS_FIELDS, "stress reading")


async def set_asabiyya(ctx: TickContext, holder_id: int, values: Values) -> AsabiyyaRow:
    await of_type(ctx, holder_id, SOLIDARY, "a people or realm")
    return await put_values(ctx, await asabiyya_row(ctx, holder_id), values, ASABIYYA_FIELDS, "solidarity")


async def strike_challenge(ctx: TickContext, polity_id: int, kind: ChallengeKind, severity: int) -> ChallengeRow:
    polity = await of_type(ctx, polity_id, POLITIES, "a realm")
    profile = await found(ctx, PolityProfileRow, polity_id, "realm")
    row = await stress_row(ctx, polity_id)
    table = ctx.rules.challenge_response
    row.challenge = max(0, min(PERCENT, round(row.challenge * (PERCENT - table.fade_pct) / PERCENT + severity)))
    response = response_to(ctx, row.challenge)
    challenge = await saved(ctx, ChallengeRow(holder_entity_id=polity_id, kind=kind, severity=severity, response=response, epoch=ctx.epoch))
    await answer(ctx, polity, profile, row, response)
    await ctx.session.flush()
    return challenge


async def new_plan(
    ctx: TickContext,
    holder_id: int,
    kind: LongPlanKind,
    name: str,
    *,
    target_id: int | None,
    carrier_id: int | None,
    steps: int,
    step_cost: int,
    secrecy: int,
) -> LongPlanRow:
    await node_exists(ctx, holder_id, "holder")
    for other, label in ((target_id, "target"), (carrier_id, "carrier")):
        if other is not None:
            await node_exists(ctx, other, label)
    plan = LongPlanRow(
        holder_node_id=holder_id,
        author_node_id=carrier_id or holder_id,
        carrier_node_id=carrier_id,
        target_node_id=target_id,
        kind=kind,
        name=name,
        steps=max(1, steps),
        progress=0,
        step_cost=max(0, step_cost),
        secrecy=max(0, min(PERCENT, secrecy)),
        exposed=False,
        started_epoch=ctx.epoch,
        locked=[],
    )
    await saved(ctx, plan)
    await note(ctx, f"A long design was set in motion: {name}.", key="plans.begun", ids=[holder_id, *([target_id] if target_id else [])])
    return plan


async def advance_plan(ctx: TickContext, plan_id: int, steps: int) -> LongPlanRow:
    plan = await found(ctx, LongPlanRow, plan_id, "long plan")
    plan.progress = max(0, min(plan.steps, plan.progress + steps))
    if plan.progress >= plan.steps and plan.finished_epoch is None:
        await complete(ctx, plan, await ctx.session.get(EntityRow, plan.holder_node_id), PlanTally())
    await ctx.session.flush()
    return plan


async def expose_plan(ctx: TickContext, plan_id: int) -> LongPlanRow:
    plan = await found(ctx, LongPlanRow, plan_id, "long plan")
    plan.exposed = True
    await note(ctx, f"The long design called {plan.name} was laid bare.", key="plans.exposed", ids=[plan.holder_node_id])
    await ctx.session.flush()
    return plan


async def give_gift(ctx: TickContext, giver_id: int, receiver_id: int, value: int, *, occasion: GiftOccasion, item_id: int | None) -> GiftRow:
    await node_exists(ctx, giver_id, "giver")
    await node_exists(ctx, receiver_id, "receiver")
    if giver_id == receiver_id:
        raise ValidationFailedError("A gift needs two sides.")
    gift = await give(ctx, giver_id, receiver_id, value, occasion, item_id=item_id)
    if gift is None:
        raise ValidationFailedError("The giver cannot afford that gift.")
    await ctx.session.flush()
    return gift


async def answer_gift(ctx: TickContext, gift_id: int, value: int | None) -> GiftRow:
    gift = await found(ctx, GiftRow, gift_id, "gift")
    answer_row = await return_gift(ctx, gift, value=value)
    if answer_row is None:
        raise ValidationFailedError("The receiver cannot afford to answer that gift.")
    await ctx.session.flush()
    return answer_row


async def refuse_gift(ctx: TickContext, gift_id: int) -> GiftRow:
    gift = await found(ctx, GiftRow, gift_id, "gift")
    await refuse(ctx, gift)
    await ctx.session.flush()
    return gift


async def stops_of(ctx: TickContext, stops: Sequence[int]) -> list[int]:
    if len(stops) < 2 or len(set(stops)) != len(stops):
        raise ValidationFailedError("A circuit needs at least two different stops.")
    for stop in stops:
        await of_type(ctx, stop, COMMUNITIES | POLITIES, "a town, people or realm")
    return list(stops)


async def new_circuit(ctx: TickContext, name: str, stops: Sequence[int], item_id: int | None) -> CircuitRow:
    return await saved(
        ctx, CircuitRow(name=name, item_entity_id=item_id, stops=await stops_of(ctx, stops), position=0, passes=0, started_epoch=ctx.epoch, locked=[])
    )


async def route_circuit(ctx: TickContext, circuit_id: int, stops: Sequence[int]) -> CircuitRow:
    circuit = await found(ctx, CircuitRow, circuit_id, "circuit")
    circuit.stops = await stops_of(ctx, stops)
    circuit.position = 0
    await ctx.session.flush()
    return circuit


async def turn_circuit(ctx: TickContext, circuit_id: int) -> CircuitRow:
    circuit = await found(ctx, CircuitRow, circuit_id, "circuit")
    if not await pass_circuit(ctx, circuit, GiftTally()):
        raise ValidationFailedError("The circuit has fewer than two living stops, or one of them is held.")
    await ctx.session.flush()
    return circuit


async def set_debt(ctx: TickContext, god_id: int, community_id: int, values: Values) -> DivineDebtRow:
    if await divine_of(ctx.session, god_id) is None:
        raise ValidationFailedError("No such god.")
    await of_type(ctx, community_id, COMMUNITIES | {EntityType.FACTION, EntityType.CULT}, "a community")
    row = await ctx.session.get(DivineDebtRow, (god_id, community_id))
    if row is None:
        row = await saved(ctx, DivineDebtRow(god_node_id=god_id, community_entity_id=community_id, offered=0, answered=0, locked=[]))
    return await put_values(ctx, row, values, DEBT_FIELDS, "gift debt")


async def set_kinship(ctx: TickContext, people_id: int, values: Values) -> KinshipSystemRow:
    await of_type(ctx, people_id, PEOPLES, "a people")
    row = await ctx.session.get(KinshipSystemRow, people_id)
    if row is None:
        row = await saved(ctx, KinshipSystemRow(people_entity_id=people_id, locked=[]))
    return await put_values(ctx, row, values, KINSHIP_FIELDS, "kinship system")


async def set_alliance(ctx: TickContext, giver_id: int, taker_id: int, values: Values) -> MarriageAllianceRow:
    if giver_id == taker_id:
        raise ValidationFailedError("An alliance needs two lines.")
    for line in (giver_id, taker_id):
        await of_type(ctx, line, frozenset({EntityType.HOUSE, EntityType.MORTAL}), "a house or a mortal")
    row = await ctx.session.get(MarriageAllianceRow, (giver_id, taker_id))
    if row is None:
        row = await saved(
            ctx, MarriageAllianceRow(giver_entity_id=giver_id, taker_entity_id=taker_id, marriages=0, since_epoch=ctx.epoch, last_epoch=ctx.epoch, locked=[])
        )
    return await put_values(ctx, row, values, ALLIANCE_FIELDS, "marriage alliance")


async def set_reproduction(ctx: TickContext, people_id: int, values: Values) -> PeopleReproductionRow:
    await of_type(ctx, people_id, PEOPLES, "a people")
    row = await ctx.session.get(PeopleReproductionRow, people_id)
    if row is None:
        row = await saved(ctx, PeopleReproductionRow(people_entity_id=people_id, locked=[]))
    return await put_values(ctx, row, values, REPRODUCTION_FIELDS, "reproductive system")


async def set_caste(ctx: TickContext, mortal_id: int, caste: ReproductiveCaste) -> MortalCasteRow:
    await of_type(ctx, mortal_id, MORTALS, "a mortal")
    row = await ctx.session.get(MortalCasteRow, mortal_id)
    if row is None:
        row = await saved(ctx, MortalCasteRow(mortal_entity_id=mortal_id, caste=caste, since_epoch=ctx.epoch, locked=[]))
    return await put_values(ctx, row, {"caste": caste.value}, CASTE_FIELDS, "caste")


async def regions_of(ctx: TickContext, regions: Sequence[int]) -> list[int]:
    if not regions:
        raise ValidationFailedError("A camp's circuit needs at least one pasture.")
    for region in regions:
        if await ctx.session.get(RegionEnvironmentRow, region) is None:
            raise ValidationFailedError("Each stop of a camp's circuit must be a land.")
    return list(regions)


async def set_camp(ctx: TickContext, town_id: int, values: Values) -> CampRow:
    town = await of_type(ctx, town_id, TOWNS, "a settlement")
    row = await ctx.session.get(CampRow, town_id)
    if row is None:
        atlas = await RegionAtlas.load(ctx.session)
        region = atlas.top_region(town.id)
        row = CampRow(settlement_entity_id=town.id, season_index=0, locked=[])
        row.circuit = await circuit_for(ctx, atlas, region, row.mode) if region is not None else []
        await saved(ctx, row)
    return await put_values(ctx, row, values, CAMP_FIELDS, "camp")


async def route_camp(ctx: TickContext, town_id: int, regions: Sequence[int]) -> CampRow:
    camp = await found(ctx, CampRow, town_id, "camp")
    camp.circuit = await regions_of(ctx, regions)
    camp.season_index = 0
    await ctx.session.flush()
    return camp


async def move_camp(ctx: TickContext, town_id: int) -> CampRow:
    camp = await found(ctx, CampRow, town_id, "camp")
    town = await of_type(ctx, town_id, TOWNS, "a settlement")
    await move(ctx, town, camp, NomadTally())
    await ctx.session.flush()
    return camp


async def members_of(ctx: TickContext, members: Sequence[int]) -> list[int]:
    if len(set(members)) < 2:
        raise ValidationFailedError("A confederation joins at least two camps.")
    for member in members:
        await found(ctx, CampRow, member, "camp")
    return sorted(set(members))


async def new_confederation(ctx: TickContext, name: str, leader_id: int | None, members: Sequence[int]) -> ConfederationRow:
    if leader_id is not None:
        await of_type(ctx, leader_id, MORTALS, "a mortal")
    row = await saved(ctx, ConfederationRow(name=name, leader_entity_id=leader_id, members=await members_of(ctx, members), formed_epoch=ctx.epoch, locked=[]))
    await note(ctx, f"{name} was formed from {len(row.members)} camps.", key="nomads.confederation", ids=list(row.members))
    return row


async def join_confederation(ctx: TickContext, confederation_id: int, members: Sequence[int]) -> ConfederationRow:
    row = await found(ctx, ConfederationRow, confederation_id, "confederation")
    row.members = await members_of(ctx, members)
    await ctx.session.flush()
    return row


async def dissolve_confederation(ctx: TickContext, confederation_id: int) -> ConfederationRow:
    row = await found(ctx, ConfederationRow, confederation_id, "confederation")
    row.dissolved_epoch = ctx.epoch
    await note(ctx, f"{row.name} broke apart into its camps.", key="nomads.fragmented", ids=list(row.members))
    await ctx.session.flush()
    return row


async def set_legacy(ctx: TickContext, people_id: int, kind: LegacyKind, key: str, predecessor_id: int | None) -> LegacyTraitRow:
    people = await of_type(ctx, people_id, PEOPLES, "a people")
    predecessor = await of_type(ctx, predecessor_id, PEOPLES, "a people") if predecessor_id is not None else people
    row = await ctx.session.get(LegacyTraitRow, (people_id, kind, key))
    try:
        await apply_legacy(ctx, kind, people, predecessor, key)
    except (ValueError, KeyError) as error:
        raise ValidationFailedError(f"{key} is not a legacy of that kind.") from error
    if row is None:
        row = await saved(
            ctx, LegacyTraitRow(people_entity_id=people_id, kind=kind, key=key, predecessor_entity_id=predecessor_id, since_epoch=ctx.epoch, locked=[])
        )
    await ctx.session.flush()
    return row


async def new_indenture(
    ctx: TickContext,
    community_id: int,
    regime: LabourRegime,
    *,
    count: int,
    term_epochs: int,
    debt: int,
    exploitation: int,
    employer_id: int | None,
    origin_id: int | None = None,
) -> IndentureRow:
    await of_type(ctx, community_id, COMMUNITIES, "a town or people")
    if employer_id is not None:
        await node_exists(ctx, employer_id, "employer")
    if origin_id is not None:
        await of_type(ctx, origin_id, PEOPLES, "a people")
    row = IndentureRow(
        community_entity_id=community_id,
        employer_node_id=employer_id,
        regime=regime,
        count=max(0, count),
        term_epochs=max(0, term_epochs),
        debt=max(0, debt),
        exploitation=max(0, min(PERCENT, exploitation)),
        origin_entity_id=origin_id,
        since_epoch=ctx.epoch,
        locked=[],
    )
    return await saved(ctx, row)


async def release_indenture(ctx: TickContext, indenture_id: int) -> int:
    row = await found(ctx, IndentureRow, indenture_id, "bond of labour")
    community_id, count = row.community_entity_id, row.count
    await ctx.session.delete(row)
    await note(ctx, f"{count} bound labourers were released from their bond.", key="indenture.released", ids=[community_id])
    await ctx.session.flush()
    return community_id


async def set_market(ctx: TickContext, town_id: int, values: Values) -> SlaveMarketRow:
    await of_type(ctx, town_id, TOWNS, "a settlement")
    row = await ctx.session.get(SlaveMarketRow, town_id)
    if row is None:
        row = await saved(
            ctx,
            SlaveMarketRow(
                settlement_entity_id=town_id, price=ctx.rules.slave_markets.base_price, stock=0, sold=0, open=True, updated_epoch=ctx.epoch, locked=[]
            ),
        )
    return await put_values(ctx, row, values, MARKET_FIELDS, "market")


async def free_bound(ctx: TickContext, community_id: int, share_pct: int, path: ManumissionPath) -> ManumissionRow | None:
    community = await of_type(ctx, community_id, COMMUNITIES, "a town or people")
    rows = await cohorts_of(ctx.session, community.id)
    freed = await move_people(ctx, community, rows, source=BOUND, target=freed_class(path), share=max(0, min(PERCENT, share_pct)) / PERCENT)
    sync_bound_share(await ctx.session.get(CommunitySocietyRow, community.id), rows)
    row = await record_manumission(ctx, community, freed, path)
    if freed:
        await note(
            ctx, f"In {community.name}, {freed} of the bound were set free by {path.value.replace('_', ' ')}.", key="manumission.freed", ids=[community.id]
        )
    await ctx.session.flush()
    return row


async def set_reading(ctx: TickContext, polity_id: int, epoch: int, values: Values) -> StressReadingRow:
    await of_type(ctx, polity_id, POLITIES, "a realm")
    if epoch < 0:
        raise ValidationFailedError("That is not an epoch.")
    row = await ctx.session.get(StressReadingRow, (polity_id, epoch))
    if row is None:
        row = await saved(ctx, StressReadingRow(polity_entity_id=polity_id, epoch=epoch))
    return await put_values(ctx, row, values, READING_FIELDS, "stress reading")


EDITABLE: dict[str, tuple[type[Base], tuple[str, ...], str]] = {
    "stress": (PolityStressRow, STRESS_FIELDS, "stress reading"),
    "stress_reading": (StressReadingRow, READING_FIELDS, "past stress reading"),
    "asabiyya": (AsabiyyaRow, ASABIYYA_FIELDS, "solidarity"),
    "challenge": (ChallengeRow, CHALLENGE_FIELDS, "challenge"),
    "plan": (LongPlanRow, PLAN_FIELDS, "long plan"),
    "gift": (GiftRow, GIFT_FIELDS, "gift"),
    "circuit": (CircuitRow, CIRCUIT_FIELDS, "circuit"),
    "debt": (DivineDebtRow, DEBT_FIELDS, "gift debt"),
    "kinship": (KinshipSystemRow, KINSHIP_FIELDS, "kinship system"),
    "alliance": (MarriageAllianceRow, ALLIANCE_FIELDS, "marriage alliance"),
    "reproduction": (PeopleReproductionRow, REPRODUCTION_FIELDS, "reproductive system"),
    "caste": (MortalCasteRow, CASTE_FIELDS, "caste"),
    "camp": (CampRow, CAMP_FIELDS, "camp"),
    "confederation": (ConfederationRow, CONFEDERATION_FIELDS, "confederation"),
    "legacy": (LegacyTraitRow, LEGACY_FIELDS, "legacy"),
    "indenture": (IndentureRow, INDENTURE_FIELDS, "bond of labour"),
    "slave_market": (SlaveMarketRow, MARKET_FIELDS, "market"),
    "manumission": (ManumissionRow, MANUMISSION_FIELDS, "freeing"),
}


async def edit_record(ctx: TickContext, kind: str, key: object, values: Values, release: list[str]) -> Base:
    table, fields, label = EDITABLE[kind]
    row = apply(await found(ctx, table, key, label), allowed(values, fields, label), release)
    await ctx.session.flush()
    return row


async def delete_record(ctx: TickContext, kind: str, key: object) -> None:
    table, _, label = EDITABLE[kind]
    await ctx.session.delete(await found(ctx, table, key, label))
    await ctx.session.flush()
