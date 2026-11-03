from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.anatomy import SIGHT_PARTS
from aerona.constants.units import PERCENT
from aerona.db.tables.body import BodyCustomRow, ConditionRow, InjuryRow
from aerona.db.tables.entities import EntityRow
from aerona.domain.enums.body import LASTING_INJURY_STATES, OPEN_INJURY_STATES, BodyReading, ConditionKind, HarmCause, InjuryKind
from aerona.domain.enums.bond import BondKind, BondRole
from aerona.domain.enums.domain import Domain
from aerona.domain.enums.entity import EntityType, MortalRole
from aerona.engine.body.hits import TOTAL_LOSS_KINDS
from aerona.engine.gods.queries import community_of
from aerona.engine.primitives.faith import living_patron
from aerona.engine.primitives.queries import active_bonds, living_entity
from aerona.engine.primitives.stats import stat
from aerona.rules.registry import Rules

PURITY_DOMAINS = frozenset({Domain.LIGHT, Domain.SUN, Domain.GLASS, Domain.SALT, Domain.OATH})
SUFFERING_DOMAINS = frozenset({Domain.BLOOD, Domain.PLAGUE, Domain.HUNGER, Domain.BONE, Domain.MADNESS})
MARTIAL_DOMAINS = frozenset({Domain.WAR, Domain.HUNT})
HONOURED_CAUSES = frozenset({HarmCause.BATTLE, HarmCause.DUEL, HarmCause.MONSTER, HarmCause.QUEST})
SHAMEFUL_CAUSES = frozenset({HarmCause.PUNISHMENT, HarmCause.TORTURE})
CUSTOM_FIELDS = ("reading", "wholeness_required", "seer_eye", "scar_festivals", "pension")


async def people_of(session: AsyncSession, entity: EntityRow) -> EntityRow | None:
    if entity.entity_type is EntityType.PEOPLE:
        return entity
    community = entity if entity.entity_type is EntityType.SETTLEMENT else await community_of(session, entity)
    if community is None:
        return None
    if community.entity_type is EntityType.PEOPLE:
        return community
    for bond in await active_bonds(session, [BondKind.LIVES_IN], targets=[community.id]):
        source = await living_entity(session, bond.source_node_id)
        if bond.role is BondRole.HOMELAND and source is not None and source.entity_type is EntityType.PEOPLE:
            return source
    for bond in await active_bonds(session, [BondKind.DESCENDS_FROM], sources=[community.id]):
        ancestor = await living_entity(session, bond.target_node_id)
        if ancestor is not None and ancestor.entity_type is EntityType.PEOPLE:
            return ancestor
    return None


async def derived_reading(session: AsyncSession, rules: Rules, people: EntityRow) -> tuple[BodyReading, bool]:
    table = rules.body_customs
    patron = await living_patron(session, people)
    domains = set(patron.domains) if patron is not None else set()
    if domains & PURITY_DOMAINS:
        return BodyReading.PURITY, True
    if domains & SUFFERING_DOMAINS:
        return BodyReading.SANCTIFIED_SUFFERING, False
    martiality = stat(people, "martiality") or 0
    if domains & MARTIAL_DOMAINS or martiality >= table.martial_martiality:
        return BodyReading.MARTIAL_HONOUR, False
    return BodyReading.NEUTRAL, False


async def ensure_customs(session: AsyncSession, rules: Rules, people: EntityRow) -> BodyCustomRow:
    row = await session.get(BodyCustomRow, people.id)
    if row is not None:
        return row
    reading, wholeness = await derived_reading(session, rules, people)
    row = BodyCustomRow(people_entity_id=people.id, reading=reading, wholeness_required=wholeness, locked=[])
    session.add(row)
    await session.flush()
    return row


async def customs_of(session: AsyncSession, rules: Rules, entity: EntityRow) -> BodyCustomRow | None:
    people = await people_of(session, entity)
    return await ensure_customs(session, rules, people) if people is not None else None


def missing(row: InjuryRow) -> bool:
    return row.visible and row.kind in TOTAL_LOSS_KINDS and row.state not in OPEN_INJURY_STATES


def scarred(row: InjuryRow) -> bool:
    return row.visible and row.state in LASTING_INJURY_STATES


def presence_pct(
    rules: Rules,
    custom: BodyCustomRow | None,
    injuries: list[InjuryRow],
    conditions: list[ConditionRow],
    *,
    role: MortalRole | None,
    patron_id: int | None,
) -> int:
    table = rules.body_customs
    reading = custom.reading if custom is not None else BodyReading.NEUTRAL
    lost = sum(1 for row in injuries if missing(row))
    marks = [row for row in injuries if scarred(row)]
    shift = 0
    if reading is BodyReading.MARTIAL_HONOUR:
        honoured = sum(1 for row in marks if row.cause_kind in HONOURED_CAUSES)
        shameful = sum(1 for row in marks if row.cause_kind in SHAMEFUL_CAUSES)
        shift += min(table.martial_scar_cap, honoured * table.martial_scar_pct) - shameful * table.martial_mutilation_pct
    elif reading is BodyReading.PURITY:
        shift -= lost * table.purity_missing_pct + len(marks) * table.purity_scar_pct
    elif reading is BodyReading.SANCTIFIED_SUFFERING:
        shift += min(table.suffering_cap, len(marks) * table.suffering_pct)
    else:
        shift -= lost * table.neutral_missing_pct
    seer_lost_eye = any(row.kind is InjuryKind.GOUGED or (row.kind is InjuryKind.DESTROYED and row.part in SIGHT_PARTS) for row in injuries)
    if custom is not None and custom.seer_eye and role is MortalRole.SEER and seer_lost_eye:
        shift += table.seer_eye_pct
    for row in injuries:
        if row.kind is InjuryKind.DIVINE_BRAND:
            shift += table.brand_blessed_pct if row.cause_node_id is not None and row.cause_node_id == patron_id else -table.brand_damned_pct
    for condition in conditions:
        if condition.kind is ConditionKind.CHOSEN_MARK and reading is BodyReading.PURITY:
            shift += table.purity_chosen_pct
    return max(table.reading_floor_pct, min(table.reading_cap_pct, PERCENT + shift))


def maimed_for_rule(custom: BodyCustomRow | None, injuries: list[InjuryRow]) -> bool:
    return custom is not None and custom.wholeness_required and any(missing(row) for row in injuries)
