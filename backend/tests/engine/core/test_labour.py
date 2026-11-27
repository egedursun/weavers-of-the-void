from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.demography import LabourRow
from aerona.db.tables.economy import WorkshopRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.factions import FactionMembershipRow, FactionProfileRow
from aerona.db.tables.interconnect import IncidentRow
from aerona.db.tables.labour import LabourContractRow, LabourDisputeRow, WorkerBodyRow
from aerona.db.tables.society import CommunitySocietyRow
from aerona.domain.enums.demography import Job
from aerona.domain.enums.economy import WorkshopKind
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.faction import FactionKind
from aerona.domain.enums.labour import ContractStatus, DisputeAct, DisputeOutcome, LabourDemand, LegalStanding, WorkerBodyForm
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.polity import LawKind
from aerona.domain.models.entity_stats import FactionStats, MortalStats
from aerona.engine.context import TickContext
from aerona.engine.labour.bargaining import bargain
from aerona.engine.labour.bodies import LabourTally, Parties, ensure_rows, tend_body
from aerona.engine.labour.contracts import tend_contract
from aerona.engine.labour.cooperatives import tend_works
from aerona.engine.labour.disputes import open_dispute, tend_dispute
from aerona.engine.labour.founding import found_body, maybe_found
from aerona.engine.labour.legacy import apply_legacy
from aerona.engine.labour.stoppage import stoppage
from aerona.engine.labour.tend import bargain_round
from aerona.engine.polity.laws import enact
from aerona.engine.primitives.manual import manual_context
from aerona.engine.primitives.stats import set_stats
from aerona.engine.recording.record import record
from tests.engine.core.factories import CoreWorld, entity, settlement, tuned_rules
from tests.engine.warfare.factories import society

FORGE = WorkshopKind.FORGE
CRAFT = Job.CRAFTING


async def works_town(session: AsyncSession, world: CoreWorld, *, workers: int = 400, artisans: int = 20) -> EntityRow:
    town = await settlement(session, "Forgeholm", world, world.regions[0], population=6000)
    await society(session, town.id)
    row = await session.get(CommunitySocietyRow, town.id)
    assert row is not None
    row.satisfaction_artisan = artisans
    session.add(LabourRow(community_entity_id=town.id, job=CRAFT, workers=workers, output_pct=100, epoch=0, held=False))
    await session.flush()
    return town


async def owner(session: AsyncSession, world: CoreWorld, town: EntityRow, *, wealth: int) -> EntityRow:
    house = await entity(
        session, "The Forge House", EntityType.FACTION, FactionStats(strength=30, wealth=wealth, sway=20), world_id=world.world.id, location_id=town.id
    )
    session.add(
        FactionProfileRow(
            faction_entity_id=house.id, kind=FactionKind.MERCHANT_GUILD, home_entity_id=town.id, treasury=0, influence_over={}, cohort_share={}, locked=[]
        )
    )
    session.add(WorkshopRow(community_entity_id=town.id, kind=FORGE, level=2, built_epoch=0, owner_node_id=house.id))
    await session.flush()
    return house


async def test_bitter_workers_found_a_body_that_gathers_members_and_a_fund_by_law(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "found", tuned_rules(labour={"found_chance_pct": 100}))
    town = await works_town(session, world)
    tally = LabourTally()
    await maybe_found(ctx, tally)
    body = await session.scalar(select(WorkerBodyRow))
    assert tally.founded == 1 and body is not None and body.trades == [CRAFT.value] and body.form is WorkerBodyForm.CRAFT_UNION
    profile = await session.get(FactionProfileRow, body.faction_node_id)
    assert profile is not None and profile.kind is FactionKind.WORKER_BODY and profile.home_entity_id == town.id
    await tend_body(ctx, body, tally)
    assert body.members == 140 and body.fund == 140 * ctx.rules.labour.fund_per_member
    await enact(ctx, town, LawKind.LABOUR_LAW, {"unions": True, "bodies": "compulsory"})
    await tend_body(ctx, body, tally)
    assert body.standing is LegalStanding.COMPULSORY and body.members == 400


async def test_a_ban_is_told_and_the_body_is_prosecuted(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "ban", tuned_rules(labour={"banned_body_prosecution_pct": 100}))
    town = await works_town(session, world)
    body = await found_body(ctx, town, [CRAFT], WorkerBodyForm.CRAFT_UNION)
    body.fund = 100
    await enact(ctx, town, LawKind.LABOUR_LAW, {"unions": False})
    tally = LabourTally()
    await tend_body(ctx, body, tally)
    assert body.standing is LegalStanding.BANNED and tally.banned == 1 and tally.prosecuted == 1
    assert body.fund < 100 + body.members * body.dues
    kinds = list(await session.scalars(select(IncidentRow.kind).where(IncidentRow.kind == "labour.body_banned")))
    assert len(kinds) == 2


async def test_a_strong_body_wins_good_terms_capped_by_the_law(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "bargain", tuned_rules())
    town = await works_town(session, world)
    hirer = await owner(session, world, town, wealth=0)
    body = await found_body(ctx, town, [CRAFT], WorkerBodyForm.INDUSTRIAL_UNION)
    body.members, body.fund, body.solidarity = 400, 5000, 90
    await enact(ctx, town, LawKind.LABOUR_LAW, {"max_hours": 40})
    outcome = await bargain(ctx, Parties(body, hirer, town, CRAFT), [LabourDemand.SAFETY], LabourTally())
    contract = outcome.contract
    assert outcome.dispute is None and contract.status is ContractStatus.AGREED
    assert contract.wage > 100 and contract.hours <= 40 and contract.safety > contract.rest


async def test_a_weak_body_against_a_rich_hirer_strikes_and_the_strike_stops_output(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "strike", tuned_rules(labour={"lockout_chance_pct": 0}))
    town = await works_town(session, world)
    hirer = await owner(session, world, town, wealth=100)
    body = await found_body(ctx, town, [CRAFT], WorkerBodyForm.MUTUAL_AID)
    body.members, body.fund, body.solidarity = 100, 0, 60
    outcome = await bargain(ctx, Parties(body, hirer, town, CRAFT), [LabourDemand.WAGE], LabourTally())
    assert outcome.dispute is not None and outcome.dispute.act is DisputeAct.STRIKE
    assert outcome.contract.status is ContractStatus.BARGAINING
    stopped = await stoppage(session, ctx.rules.labour.strike_output_loss_pct, town.id)
    assert stopped[CRAFT] == 1 - 0.25 * ctx.rules.labour.strike_output_loss_pct / 100


async def test_a_strike_with_an_empty_fund_is_lost_and_one_against_an_empty_purse_is_won(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "outcome", tuned_rules())
    town = await works_town(session, world)
    poor = await owner(session, world, town, wealth=0)
    body = await found_body(ctx, town, [CRAFT], WorkerBodyForm.CRAFT_UNION)
    body.members, body.fund = 100, 0
    tally = LabourTally()
    lost = await open_dispute(ctx, Parties(body, poor, town, CRAFT), DisputeAct.STRIKE, LabourDemand.WAGE, tally)
    assert await tend_dispute(ctx, lost, tally) is DisputeOutcome.LOST
    body.fund = 10000
    won = await open_dispute(ctx, Parties(body, poor, town, CRAFT), DisputeAct.GO_SLOW, LabourDemand.HOURS, tally)
    assert await tend_dispute(ctx, won, tally) is DisputeOutcome.WON
    assert won.ended_epoch == ctx.epoch and tally.ended == 2


async def test_strikebreakers_come_where_bound_workers_could_do_the_work_and_hurt_members(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "breakers", tuned_rules(labour={"strikebreaker_substitutes_pct": 10}))
    town = await works_town(session, world)
    row = await session.get(CommunitySocietyRow, town.id)
    assert row is not None
    row.share_serf_or_slave = 30.0
    hirer = await owner(session, world, town, wealth=100)
    body = await found_body(ctx, town, [CRAFT], WorkerBodyForm.CRAFT_UNION)
    body.members, body.fund = 100, 10000
    member = await entity(session, "Tamsin", EntityType.MORTAL, MortalStats(), world_id=world.world.id, location_id=town.id)
    session.add(FactionMembershipRow(faction_entity_id=body.faction_node_id, mortal_entity_id=member.id, locked=[]))
    await session.flush()
    tally = LabourTally()
    dispute = await open_dispute(ctx, Parties(body, hirer, town, CRAFT), DisputeAct.STRIKE, LabourDemand.WAGE, tally)
    await tend_dispute(ctx, dispute, tally)
    assert dispute.strikebreakers and dispute.workers_out == 50
    assert await session.scalar(select(IncidentRow.id).where(IncidentRow.kind == "labour.strikebreakers_used")) is not None


async def test_a_cooperative_takes_its_unowned_works_and_owns_them(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "coop", tuned_rules())
    town = await works_town(session, world)
    session.add(WorkshopRow(community_entity_id=town.id, kind=FORGE, level=1, built_epoch=0))
    await session.flush()
    body = await found_body(ctx, town, [CRAFT], WorkerBodyForm.WORKER_COOPERATIVE)
    tally = LabourTally()
    await tend_works(ctx, body, tally)
    work = await session.scalar(select(WorkshopRow))
    assert work is not None and work.owner_node_id == body.faction_node_id and body.works == [work.id] and tally.claimed == 1


async def test_old_unions_get_bodies_and_old_guild_strikes_become_journeyman_disputes(session: AsyncSession, world: CoreWorld, ctx: TickContext) -> None:
    town = await works_town(session, world)
    union = await entity(session, "Old Union", EntityType.FACTION, FactionStats(), world_id=world.world.id, location_id=town.id)
    session.add(
        FactionProfileRow(
            faction_entity_id=union.id, kind=FactionKind.WORKERS_UNION, home_entity_id=town.id, treasury=0, influence_over={}, cohort_share={}, locked=[]
        )
    )
    guild = await entity(session, "Old Guild", EntityType.FACTION, FactionStats(), world_id=world.world.id, location_id=town.id)
    session.add(
        FactionProfileRow(
            faction_entity_id=guild.id, kind=FactionKind.CRAFT_GUILD, home_entity_id=town.id, treasury=0, influence_over={}, cohort_share={}, locked=[]
        )
    )
    await session.flush()
    await record(
        ctx, "faction.strike", roles={IncidentRole.ACTOR: guild.id, IncidentRole.PLACE: town.id}, facts={"unrest": 5, "prosperity_lost": 3}, place=town.id
    )
    result = await apply_legacy(ctx)
    assert result == {"societies": 1, "disputes": 1}
    assert await ensure_rows(ctx) == 1
    dispute = await session.scalar(select(LabourDisputeRow))
    society_body = await session.scalar(select(WorkerBodyRow).where(WorkerBodyRow.form == WorkerBodyForm.COMPANION_SOCIETY))
    assert dispute is not None and society_body is not None and dispute.body_node_id == society_body.faction_node_id
    assert dispute.outcome is DisputeOutcome.SETTLED and dispute.ended_epoch == dispute.started_epoch
    assert await apply_legacy(ctx) == {}


async def test_an_agreed_contract_that_the_hirer_cannot_pay_is_broken(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "broken", tuned_rules())
    town = await works_town(session, world)
    hirer = await owner(session, world, town, wealth=0)
    body = await found_body(ctx, town, [CRAFT], WorkerBodyForm.CRAFT_UNION)
    body.members = 200
    set_stats(hirer, wealth=0)
    contract = LabourContractRow(
        hirer_node_id=hirer.id,
        body_node_id=body.faction_node_id,
        settlement_entity_id=town.id,
        trade=CRAFT,
        wage=200,
        status=ContractStatus.AGREED,
        started_epoch=ctx.epoch,
        term_epochs=5,
        locked=[],
    )
    session.add(contract)
    await session.flush()
    tally = LabourTally()
    await tend_contract(ctx, contract, tally)
    assert contract.status is ContractStatus.BROKEN and tally.broken == 1


async def test_a_bitter_trade_draws_its_body_together_and_a_content_one_lets_it_slacken(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "solidarity", tuned_rules(labour={"solidarity_drift_pct": 50}))
    town = await works_town(session, world, artisans=10)
    row = await session.get(CommunitySocietyRow, town.id)
    assert row is not None
    row.satisfaction_worker = 10
    body = await found_body(ctx, town, [CRAFT], WorkerBodyForm.CRAFT_UNION)
    tally = LabourTally()
    await tend_body(ctx, body, tally)
    assert body.solidarity == 70
    row.satisfaction_artisan, row.satisfaction_worker = 90, 90
    await tend_body(ctx, body, tally)
    await tend_body(ctx, body, tally)
    assert body.solidarity < 50


async def test_a_body_never_bargains_with_a_hirer_who_heads_it(session: AsyncSession, world: CoreWorld) -> None:
    ctx = await manual_context(session, "self", tuned_rules())
    town = await works_town(session, world)
    hirer = await owner(session, world, town, wealth=0)
    body = await found_body(ctx, town, [CRAFT], WorkerBodyForm.CRAFT_UNION)
    body.members = 200
    profile = await session.get(FactionProfileRow, body.faction_node_id)
    assert profile is not None
    profile.leader_entity_id = hirer.id
    await session.flush()
    await bargain_round(ctx, body, LabourTally())
    assert await session.scalar(select(LabourContractRow).where(LabourContractRow.body_node_id == body.faction_node_id)) is None
