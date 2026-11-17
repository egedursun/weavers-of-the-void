from collections.abc import Iterable, Mapping
from dataclasses import replace
from types import MappingProxyType

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.anatomy import Anatomy
from aerona.constants.units import PERCENT
from aerona.db.read_memo import memoized
from aerona.db.tables.body import ConditionRow
from aerona.db.tables.disease import DiseaseProfileRow, OutbreakRow
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.body import BodyFunction, ConditionKind, HarmCause, InjuryKind
from aerona.domain.enums.demography import Job
from aerona.domain.enums.disease import DiseaseTarget, OutbreakStatus
from aerona.engine.body.book import anatomy_for, ensure_body
from aerona.engine.body.conditions import gain_condition
from aerona.engine.body.hits import Harm
from aerona.engine.context import TickContext
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.primitives.naming import seed_of
from aerona.rules.registry import Rules

T = DiseaseTarget
J = Job
TARGET_FUNCTION: Mapping[DiseaseTarget, BodyFunction] = MappingProxyType(
    {
        T.BREATH: BodyFunction.BREATH,
        T.VITAL: BodyFunction.VITAL,
        T.COGNITION: BodyFunction.COGNITION,
        T.SIGHT: BodyFunction.SIGHT,
        T.SKIN: BodyFunction.PRESENCE,
    }
)
TARGET_JOBS: Mapping[DiseaseTarget, frozenset[Job]] = MappingProxyType(
    {
        T.BREATH: frozenset({J.FARMING, J.HERDING, J.FISHING, J.MINING, J.BUILDING, J.SOLDIERING}),
        T.VITAL: frozenset(Job),
        T.COGNITION: frozenset({J.SCHOLARSHIP, J.CLERGY, J.TRADE, J.CRAFTING}),
        T.SIGHT: frozenset({J.CRAFTING, J.SCHOLARSHIP, J.FISHING, J.HERDING}),
        T.SKIN: frozenset({J.TRADE, J.CLERGY}),
    }
)
LEVY_TARGETS = frozenset({T.BREATH, T.VITAL, T.SIGHT})


def targets_of(profile: DiseaseProfileRow | None) -> frozenset[DiseaseTarget]:
    if profile is None:
        return frozenset()
    return frozenset(DiseaseTarget(item) for item in profile.target_functions if item in DiseaseTarget._value2member_map_)


def target_parts(anatomy: Anatomy, targets: Iterable[DiseaseTarget]) -> list[str]:
    found: list[str] = []
    for target in sorted(targets, key=lambda item: item.value):
        found.extend(part.key for part in anatomy.with_function(TARGET_FUNCTION[target]) if part.key not in found)
    return found


async def struck_part(ctx: TickContext, mortal: EntityRow, profile: DiseaseProfileRow | None) -> str | None:
    targets = targets_of(profile)
    if not targets:
        return None
    body = await ensure_body(ctx.session, ctx.rules, mortal, ctx.epoch)
    parts = target_parts(anatomy_for(body), targets)
    if not parts:
        return None
    return parts[ctx.rng(seed_of("disease_part", mortal.id, profile.disease_entity_id if profile is not None else 0)).below(len(parts))]


async def disease_harm(ctx: TickContext, mortal: EntityRow, profile: DiseaseProfileRow | None, harm: Harm) -> Harm:
    part = await struck_part(ctx, mortal, profile)
    if part is None:
        return harm
    return replace(harm, part=part, kind=InjuryKind.SICKNESS, source_node_id=profile.disease_entity_id if profile is not None else None)


async def lasting_illness(ctx: TickContext, mortal: EntityRow, profile: DiseaseProfileRow | None, *, chance: float | None = None) -> ConditionRow | None:
    part = await struck_part(ctx, mortal, profile)
    source = profile.disease_entity_id if profile is not None else None
    return await gain_condition(ctx, mortal, ConditionKind.CHRONIC_ILLNESS, HarmCause.DISASTER, chance=chance, part=part, source_node_id=source)


async def community_targets(session: AsyncSession, community_id: int, atlas: RegionAtlas | None = None) -> frozenset[DiseaseTarget]:
    places = atlas or await RegionAtlas.load(session)
    region = places.top_region(community_id)
    if region is None:
        return frozenset()
    return await region_targets(session, region)


@memoized(DiseaseProfileRow, OutbreakRow)
async def region_targets(session: AsyncSession, region: int) -> frozenset[DiseaseTarget]:
    found: set[DiseaseTarget] = set()
    statement = select(DiseaseProfileRow).join(OutbreakRow, OutbreakRow.disease_entity_id == DiseaseProfileRow.disease_entity_id)
    for profile in await session.scalars(statement.where(OutbreakRow.region_entity_id == region, OutbreakRow.status != OutbreakStatus.ENDED)):
        found |= targets_of(profile)
    return frozenset(found)


def sick_work(rules: Rules, job: Job, targets: frozenset[DiseaseTarget]) -> float:
    table = rules.epidemiology
    hit = not targets or any(job in TARGET_JOBS[target] for target in targets)
    return (table.sick_work_pct if hit else table.sick_spared_work_pct) / PERCENT


def sick_levy(rules: Rules, targets: frozenset[DiseaseTarget]) -> float:
    if not targets or targets & LEVY_TARGETS:
        return 0.0
    return rules.epidemiology.sick_levy_pct / PERCENT
