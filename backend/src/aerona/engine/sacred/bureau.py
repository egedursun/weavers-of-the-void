from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass

from sqlalchemy import select

from aerona.catalog.life.sacred import COMMON_NEEDS, PETITION_GRANTS, TARGETED_PETITIONS, WRONGS
from aerona.catalog.life_traits import MISHAP_KIND_TRAITS, having
from aerona.constants.units import PERCENT
from aerona.core.total import total
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.environment import RegionEnvironmentRow
from aerona.db.tables.folkways import MishapRow
from aerona.db.tables.mind import MemoryRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.db.tables.sacred import GeniusLocusRow, PetitionRow, SpiritOfficeRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.db.write_guard import held
from aerona.domain.enums.affliction import PackageKind, Transmission
from aerona.domain.enums.economy import GoodsFlow
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.life_traits import MishapKindTrait
from aerona.domain.enums.mind import ThoughtKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.sacred import PetitionKind, PetitionStatus, SacramentProtection
from aerona.domain.enums.society import Commodity
from aerona.engine.body.afflictions import afflict
from aerona.engine.context import TickContext
from aerona.engine.divine.gods import god_of
from aerona.engine.divine.standing import present, standing_row
from aerona.engine.mind.thoughts import think
from aerona.engine.primitives.folk import present_among
from aerona.engine.primitives.maturity import of_age_query
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.primitives.queries import living_entity
from aerona.engine.primitives.society import shift_stock, stock
from aerona.engine.primitives.standing import still_standing
from aerona.engine.primitives.stats import set_stats, stat_or
from aerona.engine.recording.record import record
from aerona.engine.sacred.guards import guarded
from aerona.engine.sacred.places import region_of
from aerona.engine.sacred.spirits import rank_above, rank_below

OPEN = (PetitionStatus.FILED, PetitionStatus.DELAYED, PetitionStatus.APPEALED)
TEN = 10
HALF = 50


LOSSES = having(MISHAP_KIND_TRAITS, MishapKindTrait.LOSSES)


@dataclass
class BureauTally:
    filed: int = 0
    granted: int = 0
    denied: int = 0
    appealed: int = 0
    neglected: int = 0
    promoted: int = 0
    demoted: int = 0
    rogue: int = 0


def due_after(ctx: TickContext, office: SpiritOfficeRow, bribe: int) -> int:
    table = ctx.rules.celestial_bureaucracy
    wait = table.delay + (1 if office.corruption >= table.rogue_at else 0) - bribe // max(1, table.bribe_per_epoch)
    return ctx.epoch + max(0, wait)


async def file_petition(
    ctx: TickContext,
    petitioner_id: int,
    office: SpiritOfficeRow,
    kind: PetitionKind,
    *,
    defendant_id: int | None,
    bribe: int,
    target_id: int | None = None,
) -> PetitionRow:
    row = PetitionRow(
        petitioner_node_id=petitioner_id,
        office_spirit_id=office.spirit_entity_id,
        kind=kind,
        defendant_spirit_id=defendant_id if kind is PetitionKind.SUIT else None,
        target_node_id=target_id if kind in TARGETED_PETITIONS else None,
        bribe=max(0, bribe),
        status=PetitionStatus.FILED,
        filed_epoch=ctx.epoch,
        due_epoch=due_after(ctx, office, bribe),
        locked=[],
    )
    ctx.session.add(row)
    await ctx.session.flush()
    await record(
        ctx,
        "petition.filed",
        roles={IncidentRole.ACTOR: petitioner_id, IncidentRole.SUBJECT: office.spirit_entity_id, IncidentRole.TARGET: row.target_node_id},
        facts={"petition": kind},
    )
    return row


async def offended_under(ctx: TickContext, community_id: int) -> GeniusLocusRow | None:
    return await ctx.session.scalar(
        select(GeniusLocusRow)
        .where(GeniusLocusRow.community_entity_id == community_id, GeniusLocusRow.offended.is_not(None))
        .order_by(GeniusLocusRow.spirit_entity_id)
        .limit(1)
    )


async def need_of(ctx: TickContext, community: EntityRow, office: SpiritOfficeRow) -> tuple[PetitionKind, int | None]:
    offended = await offended_under(ctx, community.id)
    if offended is not None and offended.spirit_entity_id != office.spirit_entity_id:
        return PetitionKind.SUIT, offended.spirit_entity_id
    food = await stock(ctx.session, ctx.rules, community.id, Commodity.FOOD)
    if food < ctx.rules.needs.hunger_food:
        return PetitionKind.HARVEST, None
    region = await region_of(ctx.session, community)
    land = await ctx.session.get(RegionEnvironmentRow, region.id) if region is not None else None
    if land is not None and land.rainfall < ctx.rules.petitions.drought_rainfall:
        return PetitionKind.RAIN, None
    profile = await ctx.session.get(SettlementProfileRow, community.id)
    if profile is not None and profile.unrest >= ctx.rules.petitions.protection_unrest_at:
        return PetitionKind.PROTECTION, None
    lost = await ctx.session.scalar(
        select(MishapRow.id).where(MishapRow.settlement_entity_id == community.id, MishapRow.epoch == ctx.epoch, MishapRow.kind.in_(sorted(LOSSES))).limit(1)
    )
    if lost is not None:
        return PetitionKind.FINDING, None
    return ctx.rng(f"petition.need.{community.id}").pick(COMMON_NEEDS), None


async def wronged_by(ctx: TickContext, petitioner_id: int) -> int | None:
    found = await ctx.session.scalar(
        select(MemoryRow.subject_node_id)
        .where(MemoryRow.holder_node_id == petitioner_id, MemoryRow.kind.in_(WRONGS), MemoryRow.magnitude < 0, MemoryRow.subject_node_id.is_not(None))
        .order_by(MemoryRow.magnitude, MemoryRow.id)
        .limit(1)
    )
    return int(found) if found is not None and not held(int(found)) else None


async def courts_fail(ctx: TickContext, community: EntityRow) -> bool:
    profile = await ctx.session.get(SettlementProfileRow, community.id)
    return profile is not None and profile.public_order < ctx.rules.petitions.justice_order_below


async def petitioner_in(ctx: TickContext, community: EntityRow) -> int:
    mortals = list(
        await ctx.session.scalars(
            select(EntityRow.id)
            .where(
                EntityRow.entity_type == EntityType.MORTAL,
                EntityRow.status == EntityStatus.CANON,
                await present_among(ctx.session, [community.id]),
                of_age_query(),
            )
            .order_by(EntityRow.id)
        )
    )
    free = [item for item in mortals if not held(item)]
    return ctx.rng(f"petitioner.{community.id}").pick(free) if free else community.id


async def file_petitions(ctx: TickContext, tally: BureauTally) -> None:
    table = ctx.rules.celestial_bureaucracy
    offices = await ctx.session.scalars(select(SpiritOfficeRow).where(SpiritOfficeRow.dismissed.is_(False)).order_by(SpiritOfficeRow.spirit_entity_id))
    for office in list(offices):
        if table.petitions_per_epoch and tally.filed >= table.petitions_per_epoch:
            return
        community = await living_entity(ctx.session, office.jurisdiction_entity_id)
        if community is None or community.entity_type is not EntityType.SETTLEMENT or held(community.id) or held(office.spirit_entity_id):
            continue
        if not ctx.rng(f"petition.{office.spirit_entity_id}").chance(table.petition_chance):
            continue
        kind, defendant = await need_of(ctx, community, office)
        bribe = office.corruption // TEN * table.bribe_share
        if bribe:
            food = await stock(ctx.session, ctx.rules, community.id, Commodity.FOOD)
            bribe = min(bribe, food)
            await shift_stock(ctx.session, ctx.rules, community.id, Commodity.FOOD, -bribe, epoch=ctx.epoch, flow=GoodsFlow.OFFERING)
        petitioner = await petitioner_in(ctx, community)
        wrongdoer = await wronged_by(ctx, petitioner) if kind in COMMON_NEEDS else None
        if wrongdoer is not None:
            kind = PetitionKind.JUSTICE if await courts_fail(ctx, community) else PetitionKind.VENGEANCE
        await file_petition(ctx, petitioner, office, kind, defendant_id=defendant, bribe=bribe, target_id=wrongdoer)
        tally.filed += 1


def grant_chance(ctx: TickContext, office: SpiritOfficeRow, petition: PetitionRow) -> int:
    table = ctx.rules.celestial_bureaucracy
    merit = table.merit_grant_pct * min(office.merit, table.promote_merit) // max(1, table.promote_merit)
    chance = table.grant_base + merit - office.corruption // TEN * table.corruption_deny_pct + petition.bribe * table.bribe_grant
    return clamp_int(round(chance * PETITION_GRANTS[petition.kind](ctx.rules) / HALF), 0, PERCENT)


async def community_of(ctx: TickContext, petition: PetitionRow, office: SpiritOfficeRow) -> EntityRow | None:
    petitioner = await living_entity(ctx.session, petition.petitioner_node_id)
    if petitioner is not None and petitioner.entity_type is EntityType.SETTLEMENT:
        return petitioner
    return await living_entity(ctx.session, office.jurisdiction_entity_id)


@dataclass(frozen=True)
class Plea:
    ctx: TickContext
    petition: PetitionRow
    office: SpiritOfficeRow
    community: EntityRow | None
    profile: MortalProfileRow | None

    @property
    def town(self) -> EntityRow | None:
        return self.community if self.community is not None and not held(self.community.id) else None


async def heal(plea: Plea) -> None:
    if plea.profile is not None and "health" not in plea.profile.locked:
        plea.profile.health = clamp_int(plea.profile.health + plea.ctx.rules.celestial_bureaucracy.healing, 0, PERCENT)


async def bear(plea: Plea) -> None:
    if plea.profile is not None and "fertility" not in plea.profile.locked:
        plea.profile.fertility = clamp_int(plea.profile.fertility + plea.ctx.rules.celestial_bureaucracy.fertility, 0, PERCENT)


async def pass_safely(plea: Plea) -> None:
    if plea.profile is not None and "stress" not in plea.profile.locked:
        plea.profile.stress = max(0, plea.profile.stress - plea.ctx.rules.celestial_bureaucracy.passage_safety)


async def reap(plea: Plea) -> None:
    if plea.town is not None:
        table = plea.ctx.rules.celestial_bureaucracy
        await shift_stock(plea.ctx.session, plea.ctx.rules, plea.town.id, Commodity.FOOD, table.harvest_food, epoch=plea.ctx.epoch, flow=GoodsFlow.OFFERING)


async def prosper(plea: Plea) -> None:
    if plea.town is not None:
        set_stats(plea.town, prosperity=clamp_int(stat_or(plea.town, "prosperity", 0) + plea.ctx.rules.celestial_bureaucracy.prosperity, 0, PERCENT))


async def try_suit(plea: Plea) -> None:
    if plea.petition.defendant_spirit_id is not None:
        await uphold_suit(plea.ctx, plea.petition.defendant_spirit_id)


async def bring_rain(plea: Plea) -> None:
    region = await region_of(plea.ctx.session, plea.town) if plea.town is not None else None
    land = await plea.ctx.session.get(RegionEnvironmentRow, region.id) if region is not None and not held(region.id) else None
    if land is not None and "rainfall" not in land.locked:
        land.rainfall = clamp_int(land.rainfall + plea.ctx.rules.petitions.rain_shift, 0, PERCENT)


async def ward(plea: Plea) -> None:
    if plea.town is not None:
        set_stats(plea.town, defense=clamp_int(stat_or(plea.town, "defense", 0) + plea.ctx.rules.petitions.protection_defence, 0, PERCENT))


async def avenge(plea: Plea) -> None:
    target = await living_entity(plea.ctx.session, plea.petition.target_node_id)
    if target is None or held(target.id):
        return
    strength, _ = await guarded(plea.ctx, target.id, SacramentProtection.FORTUNE)
    if plea.ctx.rng(f"fortune_ward.{plea.petition.id}.{target.id}").chance(plea.ctx.rules.sacraments.fortune_ward_pct * strength / PERCENT):
        return
    await afflict(plea.ctx, target, PackageKind.FORTUNE, Transmission.CURSE, source_node_id=plea.office.spirit_entity_id)


async def find_lost(plea: Plea) -> None:
    if plea.town is not None and not held(plea.town.id):
        table = plea.ctx.rules.petitions
        await shift_stock(plea.ctx.session, plea.ctx.rules, plea.town.id, Commodity.GOODS, table.finding_goods, epoch=plea.ctx.epoch, flow=GoodsFlow.AID)


async def do_justice(plea: Plea) -> None:
    wrongdoer = await living_entity(plea.ctx.session, plea.petition.target_node_id)
    profile = await plea.ctx.session.get(MortalProfileRow, wrongdoer.id) if wrongdoer is not None else None
    if profile is not None and not held(profile.entity_id) and "renown" not in profile.locked:
        profile.renown = clamp_int(profile.renown - plea.ctx.rules.petitions.justice_renown, 0, PERCENT)
    if plea.profile is not None and "stress" not in plea.profile.locked:
        plea.profile.stress = max(0, plea.profile.stress - plea.ctx.rules.petitions.justice_calm)


ANSWERS: Mapping[PetitionKind, Callable[[Plea], Awaitable[None]]] = total(
    PetitionKind,
    {
        PetitionKind.HEALING: heal,
        PetitionKind.HARVEST: reap,
        PetitionKind.FERTILITY: bear,
        PetitionKind.SAFE_PASSAGE: pass_safely,
        PetitionKind.PROSPERITY: prosper,
        PetitionKind.SUIT: try_suit,
        PetitionKind.RAIN: bring_rain,
        PetitionKind.PROTECTION: ward,
        PetitionKind.VENGEANCE: avenge,
        PetitionKind.FINDING: find_lost,
        PetitionKind.JUSTICE: do_justice,
    },
)


async def answer(ctx: TickContext, petition: PetitionRow, office: SpiritOfficeRow) -> None:
    table = ctx.rules.celestial_bureaucracy
    community = await community_of(ctx, petition, office)
    profile = await ctx.session.get(MortalProfileRow, petition.petitioner_node_id)
    if profile is not None and held(profile.entity_id):
        profile = None
    await ANSWERS[petition.kind](Plea(ctx, petition, office, community, profile))
    if office.overseer_node_id is not None and community is not None and not held(community.id):
        standing = await standing_row(ctx, community.id, office.overseer_node_id)
        if "love" not in standing.locked:
            standing.love = clamp_int(standing.love + table.grant_love, 0, PERCENT)


async def uphold_suit(ctx: TickContext, defendant_id: int) -> None:
    table = ctx.rules.celestial_bureaucracy
    if held(defendant_id):
        return
    office = await ctx.session.get(SpiritOfficeRow, defendant_id)
    if office is not None and "merit" not in office.locked:
        office.merit = max(0, office.merit - table.suit_merit)
    spirit = await ctx.session.get(GeniusLocusRow, defendant_id)
    if spirit is not None and "offended" not in spirit.locked:
        spirit.offended = None
        spirit.contentment = max(spirit.contentment, ctx.rules.genius_loci.content_at)


async def settle(ctx: TickContext, petition: PetitionRow, office: SpiritOfficeRow, *, granted: bool, tally: BureauTally) -> None:
    table = ctx.rules.celestial_bureaucracy
    if granted:
        await answer(ctx, petition, office)
        petition.status = PetitionStatus.GRANTED
        petition.resolved_epoch = ctx.epoch
        if "merit" not in office.locked:
            office.merit += table.merit_per_grant
        office.resolved += 1
        tally.granted += 1
        await think(ctx.session, ctx.rules, petition.petitioner_node_id, ThoughtKind.PRAYED_ANSWERED, ctx.epoch, subject_id=office.spirit_entity_id)
        return
    superior = office.superior_spirit_id
    if superior is not None and ctx.rng(f"petition.appeal.{petition.id}").chance(table.appeal_chance):
        above = await ctx.session.get(SpiritOfficeRow, superior)
        if above is not None and not above.dismissed:
            petition.status = PetitionStatus.APPEALED
            petition.office_spirit_id = above.spirit_entity_id
            petition.appealed_to_id = above.spirit_entity_id
            petition.due_epoch = due_after(ctx, above, petition.bribe)
            tally.appealed += 1
            return
    petition.status = PetitionStatus.DENIED
    petition.resolved_epoch = ctx.epoch
    tally.denied += 1
    await think(ctx.session, ctx.rules, petition.petitioner_node_id, ThoughtKind.PRAYER_IGNORED, ctx.epoch, subject_id=office.spirit_entity_id)


async def decide(ctx: TickContext, petition: PetitionRow, tally: BureauTally) -> None:
    table = ctx.rules.celestial_bureaucracy
    office = await ctx.session.get(SpiritOfficeRow, petition.office_spirit_id)
    if office is None or office.dismissed or held(office.spirit_entity_id):
        if ctx.epoch - petition.due_epoch >= table.neglect_epochs:
            petition.status = PetitionStatus.DISMISSED
            petition.resolved_epoch = ctx.epoch
        return
    if office.corruption >= table.rogue_at and petition.bribe == 0:
        petition.status = PetitionStatus.DELAYED
        if ctx.epoch - petition.filed_epoch >= table.neglect_epochs:
            office.neglected += 1
            tally.neglected += 1
            petition.status = PetitionStatus.DISMISSED
            petition.resolved_epoch = ctx.epoch
        else:
            petition.due_epoch = ctx.epoch + max(1, table.delay)
        return
    await settle(ctx, petition, office, granted=ctx.rng(f"petition.grant.{petition.id}").chance(grant_chance(ctx, office, petition)), tally=tally)


async def read_petitions(ctx: TickContext, tally: BureauTally) -> None:
    rows = await ctx.session.scalars(
        select(PetitionRow).where(PetitionRow.status.in_(OPEN), PetitionRow.due_epoch <= ctx.epoch).order_by(PetitionRow.due_epoch, PetitionRow.id)
    )
    for petition in list(rows):
        if held(petition.petitioner_node_id) or "status" in petition.locked:
            continue
        if not await still_standing(ctx.session, petition.petitioner_node_id):
            petition.status = PetitionStatus.DISMISSED
            continue
        await decide(ctx, petition, tally)


async def watched(ctx: TickContext, office: SpiritOfficeRow) -> bool:
    if office.overseer_node_id is None:
        return False
    god = await god_of(ctx.session, office.overseer_node_id)
    community = await living_entity(ctx.session, office.jurisdiction_entity_id)
    return god is not None and community is not None and await present(ctx, god, community)


async def tend_office(ctx: TickContext, office: SpiritOfficeRow, tally: BureauTally) -> None:
    table = ctx.rules.celestial_bureaucracy
    if "corruption" not in office.locked:
        step = -table.corruption_mend if await watched(ctx, office) else table.corruption_rate
        office.corruption = clamp_int(office.corruption + step, 0, PERCENT)
    if office.corruption >= table.rogue_at:
        if office.superior_spirit_id is not None and "superior_spirit_id" not in office.locked:
            office.superior_spirit_id = None
            tally.rogue += 1
            spirit = await ctx.session.get(EntityRow, office.spirit_entity_id)
            await record(
                ctx, "sacred.office_rogue", roles={IncidentRole.SUBJECT: office.spirit_entity_id}, facts={"detail": str(spirit.name if spirit else "A spirit")}
            )
        community = await living_entity(ctx.session, office.jurisdiction_entity_id)
        if office.overseer_node_id is not None and community is not None and not held(community.id):
            standing = await standing_row(ctx, community.id, office.overseer_node_id)
            if "neglect" not in standing.locked:
                standing.neglect = clamp_int(standing.neglect + table.rogue_neglect, 0, PERCENT)
    if office.merit >= table.promote_merit and "rank" not in office.locked:
        above = rank_above(office.rank)
        if above is not None:
            office.rank = above
            office.merit -= table.promote_merit
            tally.promoted += 1
    if office.neglected >= table.demote_neglect and "rank" not in office.locked:
        below = rank_below(office.rank)
        if below is None:
            office.dismissed = True
        else:
            office.rank = below
        office.neglected = 0
        tally.demoted += 1


async def keep_bureau(ctx: TickContext, tally: BureauTally) -> None:
    await file_petitions(ctx, tally)
    await read_petitions(ctx, tally)
    for office in list(
        await ctx.session.scalars(select(SpiritOfficeRow).where(SpiritOfficeRow.dismissed.is_(False)).order_by(SpiritOfficeRow.spirit_entity_id))
    ):
        if held(office.spirit_entity_id):
            continue
        await tend_office(ctx, office, tally)
    await ctx.session.flush()
