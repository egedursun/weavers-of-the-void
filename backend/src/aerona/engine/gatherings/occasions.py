from collections.abc import Sequence
from dataclasses import dataclass, field

from sqlalchemy import select

from aerona.catalog.life.domain import STANDING_STATES
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.culture import TraditionParticipationRow, TraditionProfileRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.interconnect import IncidentParticipantRow, IncidentRow
from aerona.db.tables.justice import CrimeCaseRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.db.tables.place import PlaceProfileRow
from aerona.db.tables.polity import OfficeRow, PolityMemberRow, PolityProfileRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.db.tables.society import CommunitySocietyRow
from aerona.db.tables.structures import StructureProfileRow
from aerona.db.tables.titles import TitleHolderRow
from aerona.db.write_guard import held
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.culture import TraditionFunction
from aerona.domain.enums.entity import EntityStatus, EntityType, MortalRole
from aerona.domain.enums.gathering import AttendanceReason, GatheringKind, GuestRole, Milestone
from aerona.domain.enums.mortal import LifeStage, PunishmentKind
from aerona.domain.enums.polity import DecisionRule, LawKind, OfficeKind
from aerona.domain.enums.society import SocialClass
from aerona.domain.enums.structure import StructureKind
from aerona.engine.context import TickContext
from aerona.engine.mortal.kin import children_of, close_kin_of, parents_of, spouses_of
from aerona.engine.polity.laws import law_param
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.folk import present_among
from aerona.engine.primitives.numbers import scaled_cap
from aerona.engine.primitives.queries import count_communities
from aerona.engine.primitives.stats import stat_or
from aerona.engine.renown.currencies import ruler_of_realm

G = GatheringKind
MARTIAL_ROLES = frozenset({MortalRole.WARRIOR, MortalRole.SWORN_WARRIOR, MortalRole.HERO, MortalRole.HUNTER, MortalRole.OFFICER})
PERFORMER_ROLES = frozenset({MortalRole.ARTISAN, MortalRole.SCRIBE, MortalRole.PRIEST, MortalRole.JOURNALIST})

TESTING_LAWS = frozenset({"registered", "licensed", "conscripted"})


@dataclass(frozen=True)
class Guest:
    node_id: int
    role: GuestRole
    reason: AttendanceReason


@dataclass
class Occasion:
    kind: GatheringKind
    host_id: int
    world_id: int | None
    place_id: int | None = None
    honoured_id: int | None = None
    milestone: Milestone | None = None
    tradition_id: int | None = None
    guests: list[Guest] = field(default_factory=list)


def chance(ctx: TickContext, key: str, pct: float) -> bool:
    return ctx.rng(f"gathering.{key}.{ctx.epoch}").chance(pct)


async def living(ctx: TickContext, node_id: int | None) -> EntityRow | None:
    if node_id is None:
        return None
    found = await ctx.session.get(EntityRow, node_id)
    return found if found is not None and found.status is EntityStatus.CANON else None


async def weddings(ctx: TickContext) -> list[Occasion]:
    found: list[Occasion] = []
    for incident in await ctx.session.scalars(select(IncidentRow).where(IncidentRow.epoch == ctx.epoch, IncidentRow.kind == "kin.marriage")):
        couple = list(
            await ctx.session.scalars(
                select(IncidentParticipantRow.node_id).where(IncidentParticipantRow.incident_id == incident.id).order_by(IncidentParticipantRow.position)
            )
        )
        first = await living(ctx, couple[0] if couple else None)
        second = await living(ctx, couple[1] if len(couple) > 1 else None)
        if first is None:
            continue
        guests = [Guest(second.id, GuestRole.WEDDED, AttendanceReason.KIN)] if second is not None else []
        found.append(Occasion(G.WEDDING, first.id, first.world_id, first.location_id, second.id if second else None, guests=guests))
    return found


async def deaths(ctx: TickContext) -> list[Occasion]:
    found: list[Occasion] = []
    rows = await ctx.session.execute(
        select(EntityRow, MortalProfileRow.renown)
        .join(MortalProfileRow, MortalProfileRow.entity_id == EntityRow.id)
        .where(EntityRow.entity_type == EntityType.MORTAL, EntityRow.status == EntityStatus.DEAD, EntityRow.end_epoch == ctx.epoch)
        .order_by(EntityRow.id)
    )
    for dead, renown in rows:
        mourners = [mourner for mourner in [await living(ctx, kin) for kin in await close_kin_of(ctx.session, dead.id)] if mourner is not None]
        host = mourners[0] if mourners else await living(ctx, dead.location_id)
        if host is None:
            continue
        kind = G.FUNERAL if renown >= ctx.rules.gatherings.funeral_renown else G.WAKE
        guests = [Guest(mourner.id, GuestRole.GUEST, AttendanceReason.KIN) for mourner in mourners[1:]]
        found.append(Occasion(kind, host.id, dead.world_id, dead.location_id, dead.id, guests=guests))
    return found


async def milestones(ctx: TickContext) -> list[Occasion]:
    table = ctx.rules.gatherings
    found: list[Occasion] = []
    born = await ctx.session.scalars(
        select(EntityRow).where(EntityRow.entity_type == EntityType.MORTAL, EntityRow.status == EntityStatus.CANON, EntityRow.birth_epoch == ctx.epoch)
    )
    for child in born:
        parents = await parents_of(ctx.session, child.id)
        host = await living(ctx, parents[0] if parents else None)
        if host is not None and chance(ctx, f"birth.{child.id}", table.birth_pct):
            found.append(Occasion(G.MILESTONE, host.id, child.world_id, host.location_id, child.id, Milestone.BIRTH))
    grown = await ctx.session.scalars(
        select(EntityRow)
        .join(MortalProfileRow, MortalProfileRow.entity_id == EntityRow.id)
        .where(EntityRow.status == EntityStatus.CANON, EntityRow.birth_epoch == ctx.epoch - 1, MortalProfileRow.life_stage == LifeStage.ADULT)
    )
    for youth in grown:
        parents = await parents_of(ctx.session, youth.id)
        host = await living(ctx, parents[0] if parents else youth.id)
        if host is not None and chance(ctx, f"age.{youth.id}", table.birth_pct):
            found.append(Occasion(G.MILESTONE, host.id, youth.world_id, host.location_id, youth.id, Milestone.COMING_OF_AGE))
    marriages = await ctx.session.scalars(
        select(BondRow).where(BondRow.kind == BondKind.SPOUSE_OF, BondRow.state == BondState.ACTIVE, BondRow.epoch < ctx.epoch).order_by(BondRow.id)
    )
    for bond in marriages:
        first, second = await living(ctx, bond.source_node_id), await living(ctx, bond.target_node_id)
        if first is not None and second is not None and chance(ctx, f"anniversary.{bond.id}", table.anniversary_pct):
            found.append(Occasion(G.MILESTONE, first.id, first.world_id, first.location_id, second.id, Milestone.ANNIVERSARY))
    return found


async def coronations(ctx: TickContext) -> list[Occasion]:
    found: list[Occasion] = []
    for holder in await ctx.session.scalars(select(TitleHolderRow).where(TitleHolderRow.since_epoch == ctx.epoch, TitleHolderRow.until_epoch.is_(None))):
        crowned = await living(ctx, holder.holder_node_id)
        if crowned is not None and crowned.entity_type is EntityType.MORTAL:
            found.append(Occasion(G.CORONATION, crowned.id, crowned.world_id, crowned.location_id, crowned.id, tradition_id=None))
    return found


async def festivals(ctx: TickContext) -> list[Occasion]:
    found: list[Occasion] = []
    rows = await ctx.session.execute(
        select(TraditionParticipationRow.tradition_entity_id, TraditionParticipationRow.community_entity_id)
        .join(TraditionProfileRow, TraditionProfileRow.tradition_entity_id == TraditionParticipationRow.tradition_entity_id)
        .where(TraditionProfileRow.kind == TraditionFunction.FESTIVAL)
        .order_by(TraditionParticipationRow.tradition_entity_id, TraditionParticipationRow.community_entity_id)
    )
    for tradition_id, community_id in rows:
        community = await living(ctx, community_id)
        if community is not None and chance(ctx, f"festival.{tradition_id}.{community_id}", ctx.rules.gatherings.over_epoch(ctx.rules.gatherings.festival_pct)):
            found.append(Occasion(G.FESTIVAL, community.id, community.world_id, community.id, tradition_id=tradition_id))
    return found


async def testings(ctx: TickContext) -> list[Occasion]:
    found: list[Occasion] = []
    for polity in list(await ctx.session.scalars(select(EntityRow).where(EntityRow.entity_type == EntityType.POLITY, EntityRow.status == EntityStatus.CANON))):
        level = str(await law_param(ctx.session, polity.id, LawKind.POWER_LAW, "level") or "free")
        town = await ctx.session.scalar(select(PolityMemberRow.member_entity_id).where(PolityMemberRow.polity_entity_id == polity.id).limit(1))
        if level in TESTING_LAWS and town is not None and chance(ctx, f"testing.{polity.id}", ctx.rules.powered_society.testing_finds):
            found.append(Occasion(G.TESTING, town, polity.world_id, town))
    return found


async def structured(ctx: TickContext, kind: StructureKind, gathering: GatheringKind, pct: float) -> list[Occasion]:
    found: list[Occasion] = []
    hosts = await ctx.session.scalars(
        select(StructureProfileRow.host_entity_id)
        .where(
            StructureProfileRow.kind == kind, StructureProfileRow.construction_state.in_(list(STANDING_STATES)), StructureProfileRow.host_entity_id.is_not(None)
        )
        .distinct()
    )
    for host_id in sorted(int(host) for host in hosts if host is not None):
        host = await living(ctx, host_id)
        if host is not None and chance(ctx, f"{gathering.value}.{host_id}", pct):
            found.append(Occasion(gathering, host.id, host.world_id, host.id))
    return found


async def realms(ctx: TickContext) -> list[tuple[EntityRow, EntityRow, PolityProfileRow]]:
    found: list[tuple[EntityRow, EntityRow, PolityProfileRow]] = []
    for profile in await ctx.session.scalars(select(PolityProfileRow).order_by(PolityProfileRow.polity_entity_id)):
        polity = await living(ctx, profile.polity_entity_id)
        ruler = await living(ctx, await ruler_of_realm(ctx.session, profile.polity_entity_id))
        if polity is not None and ruler is not None:
            found.append((polity, ruler, profile))
    return found


async def martial_folk(ctx: TickContext, polity: EntityRow) -> list[int]:
    rows = await ctx.session.scalars(
        select(EntityRow.id)
        .where(
            EntityRow.entity_type == EntityType.MORTAL,
            EntityRow.status == EntityStatus.CANON,
            EntityRow.world_id == polity.world_id,
            EntityRow.mortal_role.in_(list(MARTIAL_ROLES)),
        )
        .order_by(EntityRow.id)
    )
    return list(rows)


async def councils(ctx: TickContext, ruled: Sequence[tuple[EntityRow, EntityRow, PolityProfileRow]]) -> list[Occasion]:
    found: list[Occasion] = []
    for polity, ruler, _ in ruled:
        if not chance(ctx, f"council.{polity.id}", ctx.rules.gatherings.over_epoch(ctx.rules.gatherings.council_pct)):
            continue
        officers = await ctx.session.scalars(
            select(OfficeRow.holder_entity_id).where(
                OfficeRow.polity_entity_id == polity.id, OfficeRow.kind != OfficeKind.RULER, OfficeRow.holder_entity_id.is_not(None)
            )
        )
        guests = [Guest(int(officer), GuestRole.GUEST, AttendanceReason.OBLIGATION) for officer in officers if officer is not None]
        found.append(Occasion(G.COUNCIL, ruler.id, polity.world_id, polity.id, guests=guests))
    return found


async def summits(ctx: TickContext, ruled: Sequence[tuple[EntityRow, EntityRow, PolityProfileRow]], atlas: RegionAtlas) -> list[Occasion]:
    table = ctx.rules.gatherings
    by_world: dict[int | None, list[tuple[EntityRow, EntityRow, PolityProfileRow]]] = {}
    for item in ruled:
        by_world.setdefault(item[0].world_id, []).append(item)
    found: list[Occasion] = []
    for world_id, items in sorted(by_world.items(), key=lambda pair: pair[0] or 0):
        if len(items) < table.summit_parties or not chance(ctx, f"summit.{world_id}", table.summit_pct):
            continue
        items.sort(key=lambda item: (-item[2].tier, item[0].id))
        polity, ruler, profile = items[0]
        seat = profile.capital_entity_id or polity.id
        envoys = [
            Guest(other_ruler.id, GuestRole.ENVOY, AttendanceReason.OBLIGATION)
            for other, other_ruler, other_profile in items[1:]
            if atlas.distance(seat, other_profile.capital_entity_id or other.id) <= table.summit_hops
        ]
        if len(envoys) + 1 >= table.summit_parties:
            found.append(Occasion(G.SUMMIT, ruler.id, world_id, seat, guests=envoys))
    return found


async def tournaments(ctx: TickContext, ruled: Sequence[tuple[EntityRow, EntityRow, PolityProfileRow]]) -> list[Occasion]:
    found: list[Occasion] = []
    for polity, ruler, profile in ruled:
        if not chance(ctx, f"tournament.{polity.id}", ctx.rules.gatherings.tournament_pct):
            continue
        fighters = [Guest(node, GuestRole.CONTESTANT, AttendanceReason.RENOWN) for node in await martial_folk(ctx, polity) if node != ruler.id]
        if len(fighters) >= 2:
            found.append(Occasion(G.TOURNAMENT, ruler.id, polity.world_id, profile.capital_entity_id or polity.id, guests=fighters))
    return found


async def hunts(ctx: TickContext) -> list[Occasion]:
    found: list[Occasion] = []
    nobles = await ctx.session.scalars(
        select(EntityRow).where(EntityRow.entity_type == EntityType.MORTAL, EntityRow.status == EntityStatus.CANON, EntityRow.social_class == SocialClass.NOBLE)
    )
    for noble in nobles:
        if chance(ctx, f"hunt.{noble.id}", ctx.rules.gatherings.hunt_pct):
            found.append(Occasion(G.HUNT, noble.id, noble.world_id, noble.location_id))
    return found


async def performances(ctx: TickContext) -> list[Occasion]:
    found = await structured(ctx, StructureKind.THEATRE, G.PERFORMANCE, ctx.rules.gatherings.performance_pct)
    for occasion in found:
        artists = await ctx.session.scalars(
            select(EntityRow.id)
            .where(
                await present_among(ctx.session, [occasion.host_id]), EntityRow.status == EntityStatus.CANON, EntityRow.mortal_role.in_(list(PERFORMER_ROLES))
            )
            .order_by(EntityRow.id)
        )
        occasion.guests = [Guest(int(artist), GuestRole.PERFORMER, AttendanceReason.RENOWN) for artist in artists]
    return found


async def trials(ctx: TickContext) -> list[Occasion]:
    found: list[Occasion] = []
    for case in await ctx.session.scalars(
        select(CrimeCaseRow).where(CrimeCaseRow.closed_epoch == ctx.epoch, CrimeCaseRow.verdict.is_not(None)).order_by(CrimeCaseRow.id)
    ):
        host = await living(ctx, case.judge_entity_id or case.polity_entity_id or case.settlement_entity_id)
        if host is None:
            continue
        kind = G.EXECUTION if case.penalty is PunishmentKind.DEATH else G.TRIAL
        accused = case.accused_entity_id
        guests = [Guest(accused, GuestRole.ACCUSED, AttendanceReason.SUMMONED)] if accused is not None and kind is G.TRIAL else []
        found.append(Occasion(kind, host.id, host.world_id, case.settlement_entity_id or host.location_id, accused, guests=guests))
    return found


async def pilgrimages(ctx: TickContext) -> list[Occasion]:
    table = ctx.rules.gatherings
    found: list[Occasion] = []
    for profile in await ctx.session.scalars(select(PlaceProfileRow).where(PlaceProfileRow.sacredness >= table.pilgrimage_sacredness)):
        place = await living(ctx, profile.entity_id)
        if place is not None and chance(ctx, f"pilgrimage.{place.id}", table.pilgrimage_pct):
            found.append(Occasion(G.PILGRIMAGE, place.id, place.world_id, place.id))
    return found


async def processions(ctx: TickContext) -> list[Occasion]:
    table = ctx.rules.gatherings
    found: list[Occasion] = []
    for cult in await ctx.session.scalars(
        select(EntityRow).where(EntityRow.entity_type == EntityType.CULT, EntityRow.status == EntityStatus.CANON).order_by(EntityRow.id)
    ):
        if stat_or(cult, "zeal", 0) >= table.procession_zeal and chance(ctx, f"procession.{cult.id}", table.procession_pct):
            found.append(Occasion(G.PROCESSION, cult.id, cult.world_id, cult.location_id))
    return found


async def feasts(ctx: TickContext) -> list[Occasion]:
    table = ctx.rules.gatherings
    found: list[Occasion] = []
    rows = await ctx.session.execute(
        select(EntityRow, MortalProfileRow.wealth)
        .join(MortalProfileRow, MortalProfileRow.entity_id == EntityRow.id)
        .where(EntityRow.entity_type == EntityType.MORTAL, EntityRow.status == EntityStatus.CANON)
        .order_by(EntityRow.id)
    )
    for mortal, wealth in rows:
        able = mortal.social_class is SocialClass.NOBLE or wealth >= table.feast_wealth
        if able and chance(ctx, f"feast.{mortal.id}", table.feast_pct):
            found.append(Occasion(G.FEAST, mortal.id, mortal.world_id, mortal.location_id))
    return found


async def elections(ctx: TickContext, ruled: Sequence[tuple[EntityRow, EntityRow, PolityProfileRow]]) -> list[Occasion]:
    found: list[Occasion] = []
    for polity, ruler, profile in ruled:
        if profile.decision_rule is DecisionRule.ASSEMBLY and chance(
            ctx, f"election.{polity.id}", ctx.rules.gatherings.over_epoch(ctx.rules.gatherings.election_pct)
        ):
            found.append(Occasion(G.ELECTION, ruler.id, polity.world_id, profile.capital_entity_id or polity.id))
    return found


async def unrest_gatherings(ctx: TickContext) -> list[Occasion]:
    table = ctx.rules.gatherings
    found: list[Occasion] = []
    for town, profile in await ctx.session.execute(
        select(EntityRow, SettlementProfileRow)
        .join(SettlementProfileRow, SettlementProfileRow.settlement_entity_id == EntityRow.id)
        .where(EntityRow.status == EntityStatus.CANON)
        .order_by(EntityRow.id)
    ):
        society = await ctx.session.get(CommunitySocietyRow, town.id)
        workers = society.share(SocialClass.WORKER) if society is not None else 0.0
        sour = society is not None and society.satisfaction(SocialClass.WORKER) <= table.strike_satisfaction
        if workers >= table.strike_worker_pct and sour and chance(ctx, f"strike.{town.id}", table.strike_pct):
            found.append(Occasion(G.STRIKE, town.id, town.world_id, town.id))
        elif profile.unrest >= table.rally_unrest and chance(ctx, f"rally.{town.id}", table.rally_pct):
            found.append(Occasion(G.RALLY, town.id, town.world_id, town.id))
    return found


async def occasions(ctx: TickContext, atlas: RegionAtlas) -> list[Occasion]:
    table = ctx.rules.gatherings
    ruled = await realms(ctx)
    found = [
        *await deaths(ctx),
        *await weddings(ctx),
        *await coronations(ctx),
        *await trials(ctx),
        *await milestones(ctx),
        *await summits(ctx, ruled, atlas),
        *await councils(ctx, ruled),
        *await festivals(ctx),
        *await pilgrimages(ctx),
        *await processions(ctx),
        *await tournaments(ctx, ruled),
        *await structured(ctx, StructureKind.ARENA, G.GAMES, table.games_pct),
        *await performances(ctx),
        *await structured(ctx, StructureKind.MARKET, G.FAIR, table.over_epoch(table.fair_pct)),
        *await hunts(ctx),
        *await feasts(ctx),
        *await elections(ctx, ruled),
        *await unrest_gatherings(ctx),
        *await structured(ctx, StructureKind.OFFICE_TOWER, G.CONVENTION, table.convention_pct),
        *await structured(ctx, StructureKind.SPACEPORT, G.LAUNCH, table.launch_pct),
        *await structured(ctx, StructureKind.BROADCAST_TOWER, G.BROADCAST, table.broadcast_pct),
        *await testings(ctx),
    ]
    kept: list[Occasion] = []
    per_world: dict[int | None, int] = {}
    caps: dict[int | None, int] = {}
    for occasion in ctx.rng(f"gathering.order.{ctx.epoch}").shuffled(found):
        if occasion.world_id not in caps:
            communities = await count_communities(ctx.session, occasion.world_id) if occasion.world_id is not None else 0
            caps[occasion.world_id] = scaled_cap(table.per_world_max, table.per_world_communities, communities)
        if held(occasion.host_id) or per_world.get(occasion.world_id, 0) >= caps[occasion.world_id]:
            continue
        per_world[occasion.world_id] = per_world.get(occasion.world_id, 0) + 1
        kept.append(occasion)
    return kept


async def household_of(ctx: TickContext, mortal: EntityRow) -> list[int]:
    return [*await spouses_of(ctx.session, mortal.id), *await children_of(ctx.session, mortal.id), *await parents_of(ctx.session, mortal.id)]
