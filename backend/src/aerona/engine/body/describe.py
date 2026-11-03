from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.body_plans import PLANS
from aerona.constants.units import PERCENT
from aerona.db.tables.body import BodyCustomRow, BodyRow, ConditionRow, InjuryRow, MaimedCohortRow, ProsthesisRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.foreign_gods import ForeignGodRow
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.body import LASTING_INJURY_STATES, OPEN_INJURY_STATES, BodyReading, Capacity, ConditionKind, InjuryKind, InjuryState, MaimedKind
from aerona.domain.enums.entity import EntityType
from aerona.engine.body.book import anatomy_for
from aerona.engine.body.cohorts import maimed_share
from aerona.rules.registry import Rules

Bearer = EntityRow | SonRow | ForeignGodRow

CONDITION_TEXT: dict[ConditionKind, str] = {
    ConditionKind.CHRONIC_ILLNESS: "a lingering illness",
    ConditionKind.PARANOIA: "paranoia",
    ConditionKind.VISIONS: "visions",
    ConditionKind.RAGE: "fits of rage",
    ConditionKind.MELANCHOLY: "melancholy",
    ConditionKind.ADDICTION: "an addiction",
    ConditionKind.AGE_BLINDNESS: "blindness of age",
    ConditionKind.AGE_DEAFNESS: "deafness of age",
    ConditionKind.WITHERED_LIMB: "a withered limb",
    ConditionKind.ENDLESS_HUNGER: "an endless hunger",
    ConditionKind.POSSESSION: "a possessing spirit",
    ConditionKind.VOID_TAINT: "the taint of the void",
    ConditionKind.CHOSEN_MARK: "the mark of the chosen",
    ConditionKind.DIVINE_BRAND: "a god's brand",
}

LOST: dict[InjuryKind, str] = {InjuryKind.SEVERED: "lost", InjuryKind.GOUGED: "gouged out", InjuryKind.DESTROYED: "ruined"}

CAPACITY_TEXT: dict[Capacity, str] = {
    Capacity.MELEE: "fighting hand to hand",
    Capacity.MISSILE: "shooting and throwing",
    Capacity.COMMAND: "giving orders",
    Capacity.CRAFT: "making things",
    Capacity.SCHOLARSHIP: "reading and study",
    Capacity.PRESENCE: "how others see them",
    Capacity.MOBILITY: "getting about",
    Capacity.FERTILITY: "bearing children",
}

MAIMED_TEXT: dict[MaimedKind, str] = {
    MaimedKind.ONE_ARMED: "one-armed",
    MaimedKind.ONE_LEGGED: "one-legged",
    MaimedKind.ONE_EYED: "one-eyed",
    MaimedKind.BLIND: "blind",
    MaimedKind.DEAF: "deaf",
    MaimedKind.MUTE: "mute",
    MaimedKind.LAME: "lame",
    MaimedKind.SCARRED: "disfigured",
    MaimedKind.BROKEN_MINDED: "broken in mind",
}

READING_TEXT: dict[BodyReading, str] = {
    BodyReading.NEUTRAL: "they pity the maimed",
    BodyReading.MARTIAL_HONOUR: "they honour battle scars and scorn the marks of punishment",
    BodyReading.PURITY: "they shun visible wounds and missing parts",
    BodyReading.SANCTIFIED_SUFFERING: "they hold suffering and its scars sacred",
}


def weakened(body: BodyRow, rules: Rules) -> list[str]:
    floor = PERCENT - rules.context.body_weakness_pct
    return [f"{CAPACITY_TEXT[capacity]} {getattr(body, capacity.value)}%" for capacity in Capacity if getattr(body, capacity.value) <= floor]


def frame_line(body: BodyRow) -> str:
    spec = PLANS[body.plan]
    return f"Body: {body.plan.value.replace('_', ' ')} ({spec.label}), {body.height_class.value} and {body.build.value} of build"


async def _bearer_lines(session: AsyncSession, rules: Rules, body: BodyRow, bearer_id: int, *, private: bool) -> list[str]:
    anatomy = anatomy_for(body)
    injuries = list(await session.scalars(select(InjuryRow).where(InjuryRow.bearer_node_id == bearer_id, InjuryRow.state != InjuryState.LETHAL)))
    fitted = {row.injury_id: row for row in await session.scalars(select(ProsthesisRow).where(ProsthesisRow.bearer_node_id == bearer_id))}

    def label(key: str) -> str:
        found = anatomy.part(key)
        return (found.label if found else key.replace("_", " ")).lower()

    def worn(row: InjuryRow) -> str:
        return f" (wears a {fitted[row.id].material.value.replace('_', ' ')} one)" if row.id in fitted else ""

    shown = [row for row in injuries if row.visible or private]
    groups = {
        "Missing": [f"{label(row.part)} {LOST[row.kind]}{worn(row)}" for row in shown if row.kind in LOST and row.state not in OPEN_INJURY_STATES],
        "Scars": [
            f"{row.kind.value.replace('_', ' ')} on the {label(row.part)}" for row in shown if row.state in LASTING_INJURY_STATES and row.kind not in LOST
        ],
        "Open wounds": [
            f"{row.kind.value.replace('_', ' ')} on the {label(row.part)}" + (" (festering)" if row.state is InjuryState.INFECTED else "")
            for row in shown
            if row.state in OPEN_INJURY_STATES
        ],
    }
    lines = [f"{title}: " + "; ".join(items) for title, items in groups.items() if items]
    conditions = list(await session.scalars(select(ConditionRow).where(ConditionRow.bearer_node_id == bearer_id, ConditionRow.ended_epoch.is_(None))))
    known = [CONDITION_TEXT[row.kind] for row in conditions if row.visible or private]
    if known:
        lines.append("Lives with: " + "; ".join(known))
    weak = weakened(body, rules) if private else []
    if weak:
        lines.append("Hampered in: " + "; ".join(weak))
    return lines


async def _community_lines(session: AsyncSession, rules: Rules, community: EntityRow) -> list[str]:
    lines: list[str] = []
    cohorts = list(await session.scalars(select(MaimedCohortRow).where(MaimedCohortRow.community_entity_id == community.id, MaimedCohortRow.count > 0)))
    if cohorts:
        share = round(maimed_share(rules, community, cohorts) * PERCENT)
        parts = ", ".join(f"{row.count} {MAIMED_TEXT[row.kind]}" for row in sorted(cohorts, key=lambda row: -row.count))
        lines.append(f"The maimed among them ({share}%): {parts}")
    custom = await session.get(BodyCustomRow, community.id) if community.entity_type is EntityType.PEOPLE else None
    if custom is not None:
        customs = [READING_TEXT[custom.reading]]
        customs += ["a ruler must be whole in body"] if custom.wholeness_required else []
        customs += ["their maimed veterans are pensioned"] if custom.pension else []
        customs += ["they keep a festival of scars"] if custom.scar_festivals else []
        lines.append("Of wounds and bodies: " + "; ".join(customs))
    return lines


async def body_lines(session: AsyncSession, rules: Rules, bearer: Bearer, *, private: bool = False) -> list[str]:
    body = await session.get(BodyRow, bearer.id)
    lines = [frame_line(body)] if body is not None else []
    lines += await _bearer_lines(session, rules, body, bearer.id, private=private) if body is not None else []
    if isinstance(bearer, EntityRow) and bearer.entity_type in {EntityType.SETTLEMENT, EntityType.PEOPLE}:
        lines += await _community_lines(session, rules, bearer)
    return lines
