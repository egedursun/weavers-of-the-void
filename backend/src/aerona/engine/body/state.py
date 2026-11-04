from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.units import PERCENT
from aerona.db.tables.body import ARMOUR_COLUMNS, BodyRow, InjuryRow
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.body import InjuryKind
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import EntityType
from aerona.engine.body.book import Bearer, Reading, active_conditions, armour_of, ensure_body, factors_of, injuries_of, open_severity, prostheses_of
from aerona.engine.body.capacities import pain_of
from aerona.engine.body.customs import customs_of, presence_pct
from aerona.engine.body.derived import refresh_body_modifiers
from aerona.engine.gods.queries import community_of
from aerona.engine.primitives.faith import living_patron
from aerona.engine.primitives.queries import active_bonds
from aerona.rules.registry import Rules

PAIN = "pain"


async def has_reader(session: AsyncSession, bearer: Bearer) -> bool:
    return bool(await active_bonds(session, [BondKind.APPRENTICE_OF], targets=[bearer.id]))


async def reading_of(session: AsyncSession, rules: Rules, bearer: Bearer) -> Reading:
    if not isinstance(bearer, EntityRow):
        return Reading()
    custom = await customs_of(session, rules, bearer)
    patron = await living_patron(session, bearer)
    injuries = await injuries_of(session, bearer.id)
    conditions = await active_conditions(session, bearer.id)
    pct = presence_pct(rules, custom, injuries, conditions, role=bearer.mortal_role, patron_id=patron.id if patron is not None else None)
    return Reading(pct, await has_reader(session, bearer))


async def refresh(session: AsyncSession, rules: Rules, bearer: Bearer, epoch: int) -> BodyRow:
    body = await ensure_body(session, rules, bearer, epoch)
    injuries = await injuries_of(session, bearer.id)
    prostheses = await prostheses_of(session, bearer.id)
    conditions = await active_conditions(session, bearer.id)
    reading = await reading_of(session, rules, bearer)
    locked = set(body.locked)
    for capacity, value in factors_of(rules, bearer, body, injuries=injuries, prostheses=prostheses, conditions=conditions, reading=reading).items():
        if capacity.value not in locked:
            setattr(body, capacity.value, value)
    if PAIN not in locked:
        body.pain = pain_of(rules.capacities, open_severity(injuries))
    community = await community_of(session, bearer) if isinstance(bearer, EntityRow) else None
    armour = await armour_of(session, rules, bearer, community.id if community is not None else None)
    for column, value in zip(ARMOUR_COLUMNS, (armour.head, armour.torso, armour.limbs), strict=True):
        if column not in locked:
            setattr(body, column, value)
    cap_sanity(rules, bearer, injuries)
    body.updated_epoch = epoch
    if isinstance(bearer, EntityRow) and bearer.entity_type is EntityType.MORTAL:
        await session.flush()
        await refresh_body_modifiers(session, rules, epoch, bearer.id)
    return body


def sanity_ceiling(rules: Rules, injuries: Sequence[InjuryRow]) -> int:
    lost = sum(row.severity for row in injuries if row.kind is InjuryKind.VOID_TOUCH) * rules.injury.void_sanity_per_severity
    return max(0, PERCENT - lost)


def cap_sanity(rules: Rules, bearer: Bearer, injuries: Sequence[InjuryRow]) -> None:
    ceiling = sanity_ceiling(rules, injuries)
    if ceiling >= PERCENT:
        return
    current = bearer.sanity if bearer.sanity is not None else rules.cosmic_horror.default_sanity
    if current > ceiling:
        bearer.sanity = ceiling
