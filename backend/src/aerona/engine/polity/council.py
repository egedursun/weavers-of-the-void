from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.db.tables.customs import MeasureStandardRow
from aerona.db.tables.intrigue import SchemeRow, SecretRow
from aerona.db.tables.military import ArmyProfileRow
from aerona.db.tables.polity import OfficeRow
from aerona.db.tables.statecraft import PolityRegardRow
from aerona.db.tables.warfare import ArmyRow
from aerona.db.write_guard import held
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.mind import MemoryKind
from aerona.domain.enums.polity import OfficeKind
from aerona.domain.enums.settlement import TreasuryEntry
from aerona.domain.enums.statecraft import CouncilTask
from aerona.engine.context import TickContext
from aerona.engine.crafts.reckoning import reckoned
from aerona.engine.intrigue.schemes import OPEN
from aerona.engine.notes import note
from aerona.engine.polity.book import Realm, RealmBook
from aerona.engine.polity.governance import spend
from aerona.engine.polity.offices import POWER_SKILLS, power_skill, powers_of
from aerona.engine.primitives.numbers import clamp_int, round_half_up
from aerona.engine.primitives.stats import shift_stat, stat
from aerona.engine.relations.book import relation
from aerona.engine.services.community_relations import change_relation

TASKS: dict[OfficeKind, CouncilTask] = {
    OfficeKind.CHANCELLOR: CouncilTask.IMPROVE_RELATIONS,
    OfficeKind.MARSHAL: CouncilTask.TRAIN_TROOPS,
    OfficeKind.TREASURER: CouncilTask.COLLECT_TAXES,
    OfficeKind.SPYMASTER: CouncilTask.DISRUPT_SCHEMES,
    OfficeKind.CHAPLAIN: CouncilTask.CONVERT_PROVINCE,
    OfficeKind.HIGH_JUDGE: CouncilTask.PURGE_CORRUPTION,
    OfficeKind.HEAD_OF_GOVERNMENT: CouncilTask.IMPROVE_RELATIONS,
    OfficeKind.MINISTER: CouncilTask.COLLECT_TAXES,
    OfficeKind.GENERAL: CouncilTask.TRAIN_TROOPS,
    OfficeKind.ADMIRAL: CouncilTask.TRAIN_TROOPS,
    OfficeKind.SPEAKER: CouncilTask.PURGE_CORRUPTION,
}
TASK = "task"
DILIGENCE = "diligence"
CORRUPTION = "corruption"


@dataclass
class CouncilTally:
    tasks: int = 0
    leaks: int = 0


@dataclass(frozen=True)
class Work:
    realm: Realm
    office: OfficeRow
    strength: float


async def diligence_of(ctx: TickContext, realm: Realm, office: OfficeRow) -> int:
    ruler = realm.ruler_id
    if office.holder_entity_id is None or ruler is None or ruler == office.holder_entity_id:
        return PERCENT
    view = await relation(ctx.session, office.holder_entity_id, ruler)
    return clamp_int(PERCENT // 2 + (view.friendship if view is not None else 0) / 2, 0, PERCENT)


async def neighbour_to_soothe(ctx: TickContext, realm: Realm) -> int | None:
    row = await ctx.session.scalar(
        select(PolityRegardRow)
        .where(PolityRegardRow.holder_entity_id != realm.entity.id, PolityRegardRow.subject_entity_id == realm.entity.id)
        .order_by(PolityRegardRow.threat.desc(), PolityRegardRow.holder_entity_id)
    )
    return row.holder_entity_id if row is not None else None


async def least_pious(ctx: TickContext, book: RealmBook, realm: Realm) -> int | None:
    members = [member for member in book.members(realm) if stat(member, "piety") is not None]
    return min(members, key=lambda member: (stat(member, "piety") or 0, member.id)).id if members else None


async def choose(ctx: TickContext, book: RealmBook, realm: Realm, office: OfficeRow) -> None:
    task = TASKS.get(office.kind)
    if task is None or TASK in (office.locked or []):
        return
    office.task = task
    if task is CouncilTask.IMPROVE_RELATIONS:
        office.task_target_node_id = await neighbour_to_soothe(ctx, realm)
    elif task is CouncilTask.CONVERT_PROVINCE:
        office.task_target_node_id = await least_pious(ctx, book, realm)
    else:
        office.task_target_node_id = None


async def improve_relations(ctx: TickContext, book: RealmBook, work: Work) -> None:
    other = book.realms.get(work.office.task_target_node_id or -1)
    mine, theirs = work.realm.profile.core_entity_id, other.profile.core_entity_id if other is not None else None
    if mine is None or theirs is None or held(theirs):
        return
    await change_relation(ctx, mine, theirs, ctx.rules.affairs.relations_gain * work.strength, MemoryKind.GOODWILL, note="courted by a chancellor")


async def train_troops(ctx: TickContext, book: RealmBook, work: Work) -> None:
    members = list(work.realm.members)
    if not members:
        return
    gain = round_half_up(ctx.rules.affairs.drill_gain * work.strength)
    armies = await ctx.session.scalars(
        select(ArmyProfileRow)
        .join(ArmyRow, ArmyRow.entity_id == ArmyProfileRow.army_entity_id)
        .where(ArmyRow.owner_entity_id.in_(members), ArmyRow.disbanded_epoch.is_(None))
    )
    for army in armies:
        if not held(army.army_entity_id) and "cohesion" not in (army.locked or []):
            army.cohesion = clamp_int(army.cohesion + gain, 0, PERCENT)


async def collect_taxes(ctx: TickContext, book: RealmBook, work: Work) -> None:
    gathered = round_half_up(ctx.rules.affairs.collect_gain * len(work.realm.members) * work.strength)
    standard = await ctx.session.get(MeasureStandardRow, work.realm.entity.id)
    if standard is not None and standard.standard:
        gathered = round_half_up(gathered * (1 + ctx.rules.measures.tax_pct / PERCENT))
    gathered = round_half_up(gathered * await reckoned(ctx.session, work.realm.entity.id, ctx.rules.numeracy.tax_pct))
    if gathered > 0 and "treasury" not in work.realm.profile.locked:
        spend(ctx, work.realm, gathered, TreasuryEntry.TAX, "gathered by the treasurer")


async def disrupt_schemes(ctx: TickContext, book: RealmBook, work: Work) -> None:
    guarded = {work.realm.entity.id, *work.realm.members, *([work.realm.ruler_id] if work.realm.ruler_id is not None else [])}
    loss = round_half_up(ctx.rules.affairs.disrupt_gain * work.strength)
    for scheme in await ctx.session.scalars(select(SchemeRow).where(SchemeRow.target_node_id.in_(list(guarded)), SchemeRow.phase.in_(list(OPEN)))):
        if not held(scheme.owner_node_id) and "progress" not in (scheme.locked or []):
            scheme.progress = clamp_int(scheme.progress - loss, 0, PERCENT)


async def convert_province(ctx: TickContext, book: RealmBook, work: Work) -> None:
    target = book.entities.get(work.office.task_target_node_id or -1)
    if target is not None and not held(target.id) and stat(target, "piety") is not None:
        shift_stat(target, "piety", ctx.rules.affairs.convert_gain * work.strength)


async def purge_corruption(ctx: TickContext, book: RealmBook, work: Work) -> None:
    if CORRUPTION not in work.realm.profile.locked:
        work.realm.profile.corruption = clamp_int(work.realm.profile.corruption - ctx.rules.affairs.purge_gain * work.strength, 0, PERCENT)


EFFECTS: dict[CouncilTask, Callable[[TickContext, RealmBook, Work], Awaitable[None]]] = {
    CouncilTask.IMPROVE_RELATIONS: improve_relations,
    CouncilTask.TRAIN_TROOPS: train_troops,
    CouncilTask.COLLECT_TAXES: collect_taxes,
    CouncilTask.DISRUPT_SCHEMES: disrupt_schemes,
    CouncilTask.CONVERT_PROVINCE: convert_province,
    CouncilTask.PURGE_CORRUPTION: purge_corruption,
}


async def leak(ctx: TickContext, book: RealmBook, realm: Realm, office: OfficeRow, tally: CouncilTally) -> None:
    ruler = realm.ruler_id
    if office.kind is not OfficeKind.SPYMASTER or ruler is None or office.diligence >= ctx.rules.affairs.leak_below:
        return
    rival = next(
        (other.ruler_id for other in sorted(book.realms.values(), key=lambda item: item.entity.id) if other.entity.id != realm.entity.id and other.ruler_id),
        None,
    )
    secret = await ctx.session.scalar(
        select(SecretRow).where(SecretRow.holder_node_id == ruler, SecretRow.exposed_epoch.is_(None)).order_by(SecretRow.severity.desc()).limit(1)
    )
    if rival is None or secret is None or held(ruler) or "known_by" in (secret.locked or []) or rival in (secret.known_by or []):
        return
    secret.known_by = [*(secret.known_by or []), rival]
    tally.leaks += 1
    await note(
        ctx, f"The spymaster of {realm.entity.name} sold the ruler's secret abroad.", key="affairs.leak", ids=[realm.entity.id], kind=ChronicleKind.CIVILIZATION
    )


async def serve(ctx: TickContext, book: RealmBook, realm: Realm, office: OfficeRow, tally: CouncilTally) -> None:
    if office.holder_entity_id is None or held(office.holder_entity_id):
        return
    await choose(ctx, book, realm, office)
    if DILIGENCE not in (office.locked or []):
        office.diligence = await diligence_of(ctx, realm, office)
    await leak(ctx, book, realm, office, tally)
    if office.task is None:
        return
    power = next(iter(powers_of(office)), None)
    skill = await power_skill(ctx, office, power) if power is not None and power in POWER_SKILLS else 0.0
    strength = skill * ctx.rules.affairs.task_skill_pct / PERCENT * office.diligence / PERCENT
    if strength > 0:
        await EFFECTS[office.task](ctx, book, Work(realm, office, strength))
        tally.tasks += 1


async def tend_council(ctx: TickContext, tally: CouncilTally) -> None:
    book = await RealmBook.load(ctx.session)
    for realm in sorted(book.realms.values(), key=lambda item: item.entity.id):
        if held(realm.entity.id):
            continue
        for office in realm.offices:
            await serve(ctx, book, realm, office, tally)
