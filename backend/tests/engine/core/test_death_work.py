from dataclasses import replace

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.db.tables.death_work import DeathWorkRow
from aerona.db.tables.demography import PeopleCultureRow
from aerona.db.tables.disease import OutbreakRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.interconnect import IncidentRow
from aerona.db.tables.mind import SkillRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.db.tables.records import IncidentFactRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.death_work import DeathRole, DeathStanding, RemainsTreatment
from aerona.domain.enums.demography import FuneralCustom, InheritanceCustom, MartialStyle
from aerona.domain.enums.disease import SpreadPath
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.mind import Profession, SkillKind, SkillSource
from aerona.domain.enums.settlement import SizeTier
from aerona.domain.models.entity_stats import DiseaseStats
from aerona.engine.context import TickContext
from aerona.engine.death_work.handling import DeathTally, death_match, keep_death_work, uses_grounds
from aerona.engine.death_work.seed import seed_death_work
from aerona.engine.faith.works import keeps_remains
from aerona.engine.mortal.learning import refresh_profession
from aerona.engine.primitives.stats import set_stats
from aerona.services.integrity.life_links import fit_remains_to_rite, misfit_remains
from tests.engine.core.factories import CoreWorld, bond, entity, mortal, settlement, tuned_rules
from tests.tools.every_setup_minds import made_profile


def tuned(ctx: TickContext, scale: dict[str, int] | None = None, **values: int) -> TickContext:
    return replace(ctx, environment=replace(ctx.environment, rules=tuned_rules(death_work=values, scale=scale or {})))


async def folk_town(session: AsyncSession, world: CoreWorld, treatment: RemainsTreatment, rite: FuneralCustom) -> tuple[EntityRow, PeopleCultureRow]:
    town = await settlement(session, "Ardun", world, world.regions[0])
    await bond(session, town.id, world.people.id, BondKind.DESCENDS_FROM)
    session.add(SettlementProfileRow(settlement_entity_id=town.id, size_tier=SizeTier.TOWN, sanitation=50, unrest=10, locked=[], foreigners={}))
    culture = await session.get(PeopleCultureRow, world.people.id)
    if culture is None:
        culture = PeopleCultureRow(
            people_entity_id=world.people.id,
            cohesion=50,
            literacy=10,
            urbanisation=10,
            martial_style=MartialStyle.SHIELDWALL,
            inheritance=InheritanceCustom.PRIMOGENITURE,
            locked=[],
        )
        session.add(culture)
    culture.funeral_rite = rite
    culture.remains_treatment = treatment
    await session.flush()
    return town, culture


async def died(session: AsyncSession, world: CoreWorld, town: EntityRow, name: str, epoch: int) -> EntityRow:
    being = await mortal(session, name, world, town.id)
    session.add(MortalProfileRow(entity_id=being.id, wealth=40, locked=[]))
    being.status = EntityStatus.DEAD
    being.end_epoch = epoch
    await session.flush()
    return being


def role(people_id: int, kind: DeathRole, purity: int, workers: int) -> DeathWorkRow:
    return DeathWorkRow(people_entity_id=people_id, role=kind, purity=purity, workers=workers, locked=[])


async def kinds_of(session: AsyncSession) -> list[str]:
    return list(await session.scalars(select(IncidentRow.kind).where(IncidentRow.kind.startswith("death_work.")).order_by(IncidentRow.id)))


async def test_a_people_treats_its_dead_by_its_custom_at_a_cost_and_it_cleans_or_fouls_the_town(
    session: AsyncSession, world: CoreWorld, ctx: TickContext
) -> None:
    town, _culture = await folk_town(session, world, RemainsTreatment.EXPOSURE, FuneralCustom.SKY_BURIAL)
    dead = [await died(session, world, town, f"Elder {index}", ctx.epoch) for index in range(5)]
    tally = DeathTally()
    await keep_death_work(tuned(ctx, treatment_cost=10, sanitation_per_ten_dead=10), tally)
    profile = await session.get(SettlementProfileRow, town.id)
    estate = await session.get(MortalProfileRow, dead[0].id)
    assert tally.treated == 5 and tally.exceptions == 0
    assert estate is not None and estate.wealth == 37
    assert profile is not None and profile.sanitation == 40
    assert "death_work.remains_treated" in await kinds_of(session)


async def test_the_funeral_count_leaves_out_the_dead_given_their_own_treatment(session: AsyncSession, world: CoreWorld, ctx: TickContext) -> None:
    town, _culture = await folk_town(session, world, RemainsTreatment.EXPOSURE, FuneralCustom.SKY_BURIAL)
    for index in range(3):
        await died(session, world, town, f"Elder {index}", ctx.epoch)
    made = await died(session, world, town, "Made Hand", ctx.epoch)
    session.add(made_profile(made.id, made.id))
    await session.flush()
    tally = DeathTally()
    await keep_death_work(tuned(ctx, treatment_cost=10), tally)
    told = await session.scalar(
        select(IncidentFactRow.number)
        .join(IncidentRow, IncidentRow.id == IncidentFactRow.incident_id)
        .where(IncidentRow.kind.startswith("death.funeral"), IncidentFactRow.key == "dead")
    )
    assert tally.exceptions == 1 and told == 3


async def test_without_tenders_a_plague_worsens_and_honoured_work_calls_a_skilled_mortal(session: AsyncSession, world: CoreWorld, ctx: TickContext) -> None:
    town, _culture = await folk_town(session, world, RemainsTreatment.BURIAL, FuneralCustom.BURIAL)
    plague = await entity(session, "The Grey Cough", EntityType.DISEASE, DiseaseStats(), world_id=world.world.id)
    outbreak = OutbreakRow(
        disease_entity_id=plague.id, region_entity_id=world.regions[0].id, path=next(iter(SpreadPath)), severity=50, started_epoch=ctx.epoch, locked=[]
    )
    session.add(outbreak)
    session.add_all(
        [role(world.people.id, DeathRole.PREPARER, 90, 0), role(world.people.id, DeathRole.CARRIER, 90, 0), role(world.people.id, DeathRole.MOURNER, 90, 2)]
    )
    apt = ctx.rules.skills.profession_level // 2
    healer = await mortal(session, "Wren", world, town.id)
    session.add(MortalProfileRow(entity_id=healer.id, locked=[]))
    session.add(SkillRow(holder_node_id=healer.id, skill=SkillKind.RITUAL, level=apt, peak=apt, last_used_epoch=ctx.epoch, source=SkillSource.PRACTICE))
    await session.flush()
    tally = DeathTally()
    await keep_death_work(tuned(ctx, {"death_recruit_gap_pct": 0}, untended_disease_pct=100, role_standing=50, recruit_step=0, called_per_epoch=1), tally)
    called = await session.get(MortalProfileRow, healer.id)
    assert tally.untended == 1 and outbreak.severity == 55
    assert tally.called == 1 and called is not None and called.profession is Profession.DEATH_WORKER
    assert await refresh_profession(session, ctx.rules, healer, called) is Profession.DEATH_WORKER
    assert {"death_work.untended", "death_work.called"} <= set(await kinds_of(session))


async def test_avoided_work_loses_hands_and_drives_its_worker_out_and_weighs_marriages(session: AsyncSession, world: CoreWorld, ctx: TickContext) -> None:
    town, _culture = await folk_town(session, world, RemainsTreatment.BURIAL, FuneralCustom.BURIAL)
    washers = role(world.people.id, DeathRole.WASHER, 10, 1)
    session.add(washers)
    worker = await mortal(session, "Ash", world, town.id)
    session.add(MortalProfileRow(entity_id=worker.id, profession=Profession.DEATH_WORKER, locked=[]))
    await session.flush()
    rules = tuned(ctx, role_standing=50, recruit_step=1, standing_match=10).rules
    assert await death_match(session, rules, worker) == -10
    tally = DeathTally()
    await keep_death_work(tuned(ctx, role_standing=50, recruit_step=1, standing_match=10), tally)
    left = await session.get(MortalProfileRow, worker.id)
    assert washers.standing is DeathStanding.AVOIDED and washers.workers == 0 and tally.shunned == 1
    assert tally.left == 1 and left is not None and left.profession is None
    assert {"death_work.role_shunned", "death_work.calling_left"} <= set(await kinds_of(session))


async def test_remains_decide_relics_grounds_and_the_rite_holds_the_treatment(session: AsyncSession, world: CoreWorld, ctx: TickContext) -> None:
    town, culture = await folk_town(session, world, RemainsTreatment.CREMATION, FuneralCustom.CREMATION)
    saint = await mortal(session, "Ilse", world, town.id)
    assert not await keeps_remains(ctx, saint)
    assert not uses_grounds(culture.remains_treatment) and uses_grounds(RemainsTreatment.STORAGE)
    culture.remains_treatment = RemainsTreatment.EXPOSURE
    await session.flush()
    assert await misfit_remains(session) == [world.people.id]
    await fit_remains_to_rite(session, world.people.id)
    assert culture.remains_treatment is RemainsTreatment.CREMATION
    culture.funeral_rite = FuneralCustom.ENTOMBMENT
    culture.remains_treatment = RemainsTreatment.WATER
    assert await seed_death_work(ctx) == 1
    assert culture.remains_treatment is RemainsTreatment.PRESERVATION
    assert await keeps_remains(ctx, saint)
    culture.locked = ["remains_treatment"]
    culture.remains_treatment = RemainsTreatment.WATER
    await session.flush()
    assert await misfit_remains(session) == []


async def test_death_workers_follow_the_numbers_of_the_people(session: AsyncSession, world: CoreWorld, ctx: TickContext) -> None:
    await folk_town(session, world, RemainsTreatment.BURIAL, FuneralCustom.BURIAL)
    set_stats(world.people, population=40000)
    await session.flush()
    assert await seed_death_work(ctx) == 1
    seeded = list(await session.scalars(select(DeathWorkRow).where(DeathWorkRow.people_entity_id == world.people.id)))
    need = 40000 * ctx.rules.scale.death_workers_per_mille // 1000
    assert seeded and all(row.workers == need for row in seeded)
    for row in seeded:
        await session.delete(row)
    await session.flush()
    honoured, avoided = role(world.people.id, DeathRole.CARRIER, 90, 0), role(world.people.id, DeathRole.WASHER, 10, need)
    session.add_all([honoured, avoided])
    await session.flush()
    await keep_death_work(tuned(ctx, role_standing=50, recruit_step=1), DeathTally())
    assert 0 < honoured.workers <= need and honoured.workers > 1
    assert avoided.workers < need - 1
