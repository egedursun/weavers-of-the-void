from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from aerona.constants.units import PERCENT
from aerona.db.tables.body import ARMOUR_COLUMNS, BodyRow, InjuryRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.genetics import GenomeRow
from aerona.domain.enums.body import BodyFunction, Capacity, ConditionKind, Consciousness, InjuryKind
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.crafts import AssistiveAid
from aerona.engine.body.book import (
    Bearer,
    Reading,
    active_conditions,
    anatomy_for,
    armour_of,
    consciousness_of,
    counts_of,
    ensure_body,
    factors_of,
    injuries_of,
    open_severity,
    prostheses_of,
    wounds_from,
)
from aerona.engine.body.capacities import BodyState, function_percents, pain_of
from aerona.engine.body.customs import customs_of, presence_pct
from aerona.engine.crafts.aiding import aid_quality
from aerona.engine.gods.queries import community_of
from aerona.engine.mortal.equipment import mount_pct
from aerona.engine.mortal.variants import strength, variants_by_id
from aerona.engine.primitives.faith import living_patron
from aerona.engine.primitives.queries import active_bonds
from aerona.rules.registry import Rules

PAIN = "pain"


async def has_reader(session: AsyncSession, bearer: Bearer) -> bool:
    return (
        bool(await active_bonds(session, [BondKind.APPRENTICE_OF], targets=[bearer.id])) or await aid_quality(session, bearer.id, AssistiveAid.SPECTACLES) > 0
    )


async def reading_of(session: AsyncSession, rules: Rules, bearer: Bearer) -> Reading:
    if not isinstance(bearer, EntityRow):
        return Reading()
    custom = await customs_of(session, rules, bearer)
    patron = await living_patron(session, bearer)
    injuries = await injuries_of(session, bearer.id)
    conditions = await active_conditions(session, bearer.id)
    genome = await session.get(GenomeRow, bearer.id)
    pct = presence_pct(
        rules,
        custom,
        injuries,
        conditions,
        role=bearer.mortal_role,
        patron_id=patron.id if patron is not None else None,
        beauty=genome.beauty if genome is not None else None,
    )
    table = rules.aids
    return Reading(
        pct,
        await has_reader(session, bearer),
        await aid_quality(session, bearer.id, AssistiveAid.HEARING_HORN) * table.hearing_restore_pct / PERCENT / PERCENT,
        await aid_quality(session, bearer.id, AssistiveAid.CANE) * table.cane_aid_pct / PERCENT / PERCENT,
        await aid_quality(session, bearer.id, AssistiveAid.MAGNIFIER) * table.magnifier_craft_pct / PERCENT / PERCENT,
    )


async def refresh(session: AsyncSession, rules: Rules, bearer: Bearer, epoch: int) -> BodyRow:
    body = await ensure_body(session, rules, bearer, epoch)
    injuries = await injuries_of(session, bearer.id)
    prostheses = await prostheses_of(session, bearer.id)
    conditions = await active_conditions(session, bearer.id)
    reading = await reading_of(session, rules, bearer)
    locked = set(body.locked)
    variants = await variants_by_id(session, (row.variant_id for row in conditions))
    scale = {variant_id: strength(variants, variant_id) for variant_id in variants}
    if "consciousness" not in locked:
        comatose = any(row.kind is ConditionKind.COMATOSE for row in conditions)
        body.consciousness = (
            Consciousness.UNCONSCIOUS if comatose else consciousness_of(rules, bearer, pain_of(rules.capacities, open_severity(injuries)), body.blood)
        )
    for capacity, value in factors_of(
        rules, bearer, body, injuries=injuries, prostheses=prostheses, conditions=conditions, reading=reading, variant_scale=scale
    ).items():
        if capacity.value not in locked:
            setattr(body, capacity.value, value)
    if isinstance(bearer, EntityRow):
        moving, riding = await mount_pct(session, rules, bearer.id)
        if Capacity.MOBILITY.value not in locked:
            body.mobility = round(body.mobility * moving)
        if Capacity.MELEE.value not in locked:
            body.melee = round(body.melee * riding)
    if PAIN not in locked:
        body.pain = pain_of(rules.capacities, open_severity(injuries))
    functions = function_percents(rules, BodyState(anatomy_for(body), wounds_from(injuries, prostheses), counts_of(body), open_severity(injuries)))
    for function, level in functions.items():
        if function.value not in locked:
            setattr(body, function.value, level)
    community = await community_of(session, bearer) if isinstance(bearer, EntityRow) else None
    armour = await armour_of(session, rules, bearer, community.id if community is not None else None)
    for column, value in zip(ARMOUR_COLUMNS, (armour.head, armour.torso, armour.limbs), strict=True):
        if column not in locked:
            setattr(body, column, value)
    bodily = [row for row in injuries if row.kind is not InjuryKind.VOID_TOUCH]
    wits_state = BodyState(anatomy_for(body), wounds_from(bodily, prostheses), counts_of(body), open_severity(bodily))
    wits = function_percents(rules, wits_state)[BodyFunction.COGNITION]
    cap_sanity(rules, bearer, injuries, wits)
    body.updated_epoch = epoch
    return body


def sanity_ceiling(rules: Rules, injuries: Sequence[InjuryRow], cognition: int = PERCENT) -> int:
    lost = sum(row.severity for row in injuries if row.kind is InjuryKind.VOID_TOUCH) * rules.injury.void_sanity_per_severity
    wits = (PERCENT - max(0, min(PERCENT, cognition))) * rules.injury.cognition_sanity_pct / PERCENT
    return max(0, round(PERCENT - lost - wits))


def cap_sanity(rules: Rules, bearer: Bearer, injuries: Sequence[InjuryRow], cognition: int = PERCENT) -> None:
    ceiling = sanity_ceiling(rules, injuries, cognition)
    if ceiling >= PERCENT:
        return
    current = bearer.sanity if bearer.sanity is not None else rules.cosmic_horror.default_sanity
    if current > ceiling:
        bearer.sanity = ceiling
