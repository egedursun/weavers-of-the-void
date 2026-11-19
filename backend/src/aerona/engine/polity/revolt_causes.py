from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from sqlalchemy import func, select

from aerona.constants.units import PERCENT
from aerona.db.tables.affairs import TaxPolicyRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.minds import MindProfileRow
from aerona.db.tables.polity import ClaimRow, PolityMemberRow, PolityProfileRow
from aerona.db.tables.powers import PowerRegistryRow
from aerona.db.tables.settlement import SettlementProfileRow
from aerona.db.tables.society import CommunitySocietyRow
from aerona.domain.enums.entity import EntityFlag, EntityStatus
from aerona.domain.enums.minds import MindOrigin
from aerona.domain.enums.polity import RevoltKind
from aerona.domain.enums.society import SocialClass
from aerona.engine.body.customs import people_of
from aerona.engine.context import TickContext
from aerona.engine.primitives.faith import living_patron
from aerona.engine.primitives.numbers import round_half_up
from aerona.engine.primitives.queries import has_flag
from aerona.engine.primitives.stats import stat_or

TEN_THOUSAND = 10000
MADE_ORIGINS = frozenset({MindOrigin.MADE, MindOrigin.GROWN, MindOrigin.TRAINED, MindOrigin.COPIED})


@dataclass(frozen=True)
class Unrest:
    town: EntityRow
    society: CommunitySocietyRow | None
    member: PolityMemberRow | None
    polity: PolityProfileRow | None


Cause = Callable[[TickContext, Unrest], Awaitable[bool]]


def bitter(case: Unrest, social_class: SocialClass, share: int, below: int) -> bool:
    return case.society is not None and case.society.share(social_class) >= share and case.society.satisfaction(social_class) < below


async def enslaved(ctx: TickContext, case: Unrest) -> bool:
    return case.society is not None and case.society.share(SocialClass.SERF_OR_SLAVE) >= ctx.rules.revolts.slave_share_pct


async def seceding(ctx: TickContext, case: Unrest) -> bool:
    return case.member is not None and case.member.autonomy >= ctx.rules.revolts.secession_autonomy


async def colonial(ctx: TickContext, case: Unrest) -> bool:
    if case.polity is None or case.polity.capital_entity_id is None:
        return await has_flag(ctx.session, case.town.id, EntityFlag.COLONY)
    capital = await ctx.session.get(EntityRow, case.polity.capital_entity_id)
    far = capital is not None and capital.world_id != case.town.world_id
    return far or await has_flag(ctx.session, case.town.id, EntityFlag.COLONY)


def contentment(society: CommunitySocietyRow | None) -> int:
    if society is None:
        return PERCENT // 2
    shares = [
        int(getattr(society, f"satisfaction_{social_class.value}")) for social_class in SocialClass if hasattr(society, f"satisfaction_{social_class.value}")
    ]
    return sum(shares) // len(shares) if shares else PERCENT // 2


async def minority(ctx: TickContext, case: Unrest) -> bool:
    if case.polity is None or case.polity.core_entity_id is None:
        return False
    people = await people_of(ctx.session, case.town)
    return people is not None and people.id != case.polity.core_entity_id and contentment(case.society) < ctx.rules.revolts.minority_loyalty


async def succession(ctx: TickContext, case: Unrest) -> bool:
    if case.member is None:
        return False
    pressed = await ctx.session.scalar(
        select(ClaimRow.id)
        .where(ClaimRow.polity_entity_id == case.member.polity_entity_id, ClaimRow.pressed.is_(True), ClaimRow.ended_epoch.is_(None))
        .limit(1)
    )
    return pressed is not None


async def nobles(ctx: TickContext, case: Unrest) -> bool:
    return bitter(case, SocialClass.NOBLE, 1, ctx.rules.revolts.noble_bitter)


async def mutiny(ctx: TickContext, case: Unrest) -> bool:
    profile = await ctx.session.get(SettlementProfileRow, case.town.id)
    guarded = profile is not None and (profile.militia > 0 or profile.garrison_entity_id is not None)
    return guarded and bitter(case, SocialClass.WARRIOR, 1, ctx.rules.revolts.class_bitter)


async def taxed(ctx: TickContext, case: Unrest) -> bool:
    if case.member is None:
        return False
    burden = await ctx.session.scalar(select(func.sum(TaxPolicyRow.rate)).where(TaxPolicyRow.polity_entity_id == case.member.polity_entity_id))
    return int(burden or 0) >= ctx.rules.revolts.tax_heavy


async def faithful(ctx: TickContext, case: Unrest) -> bool:
    if case.polity is None or case.polity.state_religion_id is None:
        return False
    patron = await living_patron(ctx.session, case.town)
    cult = await ctx.session.get(EntityRow, case.polity.state_religion_id)
    faith = await living_patron(ctx.session, cult) if cult is not None else None
    return patron is not None and faith is not None and faith.id != patron.id


def per_ten_thousand(rate: int, people: int) -> int:
    return max(1, round_half_up(rate * people / TEN_THOUSAND))


async def made_minds(ctx: TickContext, case: Unrest) -> bool:
    here = select(EntityRow.id).where(EntityRow.location_id == case.town.id, EntityRow.status == EntityStatus.CANON)
    count = await ctx.session.scalar(
        select(func.count()).select_from(MindProfileRow).where(MindProfileRow.node_id.in_(here), MindProfileRow.origin.in_(list(MADE_ORIGINS)))
    )
    return int(count or 0) >= per_ten_thousand(ctx.rules.revolts.made_minds_at, stat_or(case.town, "population", 0))


async def gifted(ctx: TickContext, case: Unrest) -> bool:
    if case.member is None:
        return False
    bound = await ctx.session.scalar(
        select(func.count())
        .select_from(PowerRegistryRow)
        .where(
            PowerRegistryRow.polity_entity_id == case.member.polity_entity_id, (PowerRegistryRow.conscripted.is_(True)) | (PowerRegistryRow.licensed.is_(False))
        )
    )
    realm = await ctx.session.get(EntityRow, case.member.polity_entity_id)
    subjects = stat_or(realm, "subjects", 0) if realm is not None else 0
    return int(bound or 0) >= per_ten_thousand(ctx.rules.revolts.gifted_at, subjects)


async def workers(ctx: TickContext, case: Unrest) -> bool:
    return bitter(case, SocialClass.WORKER, ctx.rules.revolts.class_share_pct, ctx.rules.revolts.class_bitter)


async def scholars(ctx: TickContext, case: Unrest) -> bool:
    return bitter(case, SocialClass.SCRIBE, 1, ctx.rules.revolts.class_bitter) or bitter(case, SocialClass.PROFESSIONAL, 1, ctx.rules.revolts.class_bitter)


async def urban(ctx: TickContext, case: Unrest) -> bool:
    return stat_or(case.town, "population", 0) >= ctx.rules.revolts.urban_population


CAUSES: tuple[tuple[RevoltKind, Cause], ...] = (
    (RevoltKind.SLAVE, enslaved),
    (RevoltKind.SECESSION, seceding),
    (RevoltKind.COLONIAL, colonial),
    (RevoltKind.MINORITY, minority),
    (RevoltKind.SUCCESSION, succession),
    (RevoltKind.NOBLE, nobles),
    (RevoltKind.MUTINY, mutiny),
    (RevoltKind.MADE_MINDS, made_minds),
    (RevoltKind.GIFTED, gifted),
    (RevoltKind.RELIGIOUS, faithful),
    (RevoltKind.TAX, taxed),
    (RevoltKind.WORKER, workers),
    (RevoltKind.SCHOLAR, scholars),
    (RevoltKind.URBAN, urban),
)


async def revolt_kind(ctx: TickContext, town: EntityRow) -> RevoltKind:
    society = await ctx.session.get(CommunitySocietyRow, town.id)
    member = await ctx.session.scalar(select(PolityMemberRow).where(PolityMemberRow.member_entity_id == town.id).limit(1))
    polity = await ctx.session.get(PolityProfileRow, member.polity_entity_id) if member is not None else None
    case = Unrest(town, society, member, polity)
    for kind, cause in CAUSES:
        if await cause(ctx, case):
            return kind
    return RevoltKind.PEASANT
