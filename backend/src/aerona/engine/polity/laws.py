import re
from collections import defaultdict
from collections.abc import Mapping
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aerona.catalog.backfill_words import LAW_WORDS
from aerona.catalog.laws import LAW_PARAMS, LAW_TITLES, defaults_for, law_terms, penal_cruelty, term_text
from aerona.constants.units import PERCENT
from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.db.read_memo import memoized
from aerona.db.tables.bonds import BondRow
from aerona.db.tables.cosmos import AppliedFixupRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.polity import LawJurisdictionRow, LawProfileRow, PolityMemberRow
from aerona.domain.enums.bond import BondKind, BondState
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.mind import ValueAxis
from aerona.domain.enums.polity import LAW_AREAS, Jurisdiction, LawKind, LegitimacyBasis
from aerona.domain.models.entity_stats import LawStats
from aerona.engine.context import TickContext
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.primitives.records import RecordSpec, create_record, retire_in
from aerona.engine.primitives.stats import set_stats, stat_or

ParamValue = int | str | bool
KIND_FIXUP = "law_kinds_from_text"
CULT_FIRST = frozenset({LawKind.BURIAL_LAW, LawKind.MARRIAGE_LAW, LawKind.RITE_RESTRICTIONS, LawKind.WORSHIP_BAN, LawKind.MAGIC_BAN, LawKind.TITHE})
KIND_VALUES: Mapping[LawKind, Mapping[ValueAxis, int]] = {
    LawKind.SLAVERY: {ValueAxis.MERCY: -1, ValueAxis.HIERARCHY: 1},
    LawKind.PENAL_CODE: {ValueAxis.MERCY: -1, ValueAxis.TRADITION: 1},
    LawKind.CONSCRIPTION: {ValueAxis.MARTIAL: 1},
    LawKind.CENSORSHIP: {ValueAxis.HIERARCHY: 1, ValueAxis.TRUTH: -1, ValueAxis.KNOWLEDGE: -1},
    LawKind.RELIGIOUS_TOLERANCE: {ValueAxis.XENOPHILIA: 1, ValueAxis.PIETY: -1},
    LawKind.FOREIGNER_RIGHTS: {ValueAxis.XENOPHILIA: 1},
    LawKind.SUMPTUARY: {ValueAxis.HIERARCHY: 1, ValueAxis.WEALTH: -1},
    LawKind.MAGIC_BAN: {ValueAxis.SUPERSTITION: 1, ValueAxis.KNOWLEDGE: -1},
    LawKind.TAX_RATE: {ValueAxis.WEALTH: -1},
    LawKind.BLOOD_FEUD: {ValueAxis.HONOUR: 1, ValueAxis.KINSHIP: 1},
    LawKind.FRANCHISE: {ValueAxis.HIERARCHY: -1},
    LawKind.LABOUR_LAW: {ValueAxis.MERCY: 1, ValueAxis.WEALTH: -1},
    LawKind.ENVIRONMENT_LAW: {ValueAxis.NATURE: 1, ValueAxis.WEALTH: -1},
    LawKind.DATA_PRIVACY: {ValueAxis.HIERARCHY: -1},
    LawKind.WEAPONS_LAW: {ValueAxis.MARTIAL: -1, ValueAxis.LAW: 1},
    LawKind.INTELLECTUAL_PROPERTY: {ValueAxis.WEALTH: 1, ValueAxis.KNOWLEDGE: -1},
    LawKind.MACHINE_LAW: {ValueAxis.TRADITION: 1, ValueAxis.KNOWLEDGE: -1},
    LawKind.SPACE_LAW: {ValueAxis.XENOPHILIA: 1},
    LawKind.MIND_STATUS: {ValueAxis.MERCY: 1, ValueAxis.TRADITION: -1},
    LawKind.COPY_LAW: {ValueAxis.TRADITION: 1, ValueAxis.FAMILY: 1},
    LawKind.COPY_SUCCESSION: {ValueAxis.LAW: 1},
    LawKind.ERASURE_LAW: {ValueAxis.MERCY: 1},
    LawKind.AUGMENT_LAW: {ValueAxis.TRADITION: 1, ValueAxis.PURITY: 1},
    LawKind.NETWORK_LAW: {ValueAxis.HIERARCHY: 1},
    LawKind.SURVEILLANCE_LAW: {ValueAxis.LAW: 1, ValueAxis.HIERARCHY: 1},
    LawKind.PROVISION_LAW: {ValueAxis.MERCY: 1, ValueAxis.WEALTH: -1},
    LawKind.POWER_LAW: {ValueAxis.LAW: 1, ValueAxis.HIERARCHY: 1},
    LawKind.SOURCE_LAW: {ValueAxis.TRADITION: 1, ValueAxis.PIETY: 1},
}


def guess_kind(law: EntityRow) -> LawKind:
    text = " ".join(item for item in (law.name, law.subtype, law.description) if item).lower()
    words = set(re.findall(r"[^\W\d_]+", text))
    for kind, keys in LAW_WORDS.items():
        if kind is LawKind.CUSTOM:
            continue
        if any((key in text) if " " in key else (key in words) for key in keys):
            return kind
    return LawKind.CUSTOM


def validate(kind: LawKind, params: Mapping[str, ParamValue]) -> dict[str, ParamValue]:
    spec = LAW_PARAMS[kind]
    unknown = set(params) - set(spec)
    if unknown:
        raise ValidationFailedError(f"{kind.value.replace('_', ' ')} has no {', '.join(sorted(unknown))}; its terms are: {law_terms(kind)}.")
    merged = defaults_for(kind)
    for key, value in params.items():
        if not spec[key].valid(value):
            raise ValidationFailedError(f"{key.replace('_', ' ')} cannot be {value}; it takes {term_text(key, spec[key])}.")
        merged[key] = value
    return merged


async def attach_profile(
    session: AsyncSession,
    law: EntityRow,
    kind: LawKind,
    params: Mapping[str, ParamValue] | None,
    *,
    holder: EntityRow | None,
    epoch: int,
    by_id: int | None = None,
    basis: LegitimacyBasis | None = None,
) -> LawProfileRow:
    merged = validate(kind, params or {})
    rigidity = stat_or(law, "rigidity", 50)
    profile = LawProfileRow(
        law_entity_id=law.id,
        kind=kind,
        area=LAW_AREAS[kind],
        params=merged,
        enforcement=50,
        legitimacy_basis=basis or (LegitimacyBasis.CUSTOM if rigidity >= PERCENT // 2 else LegitimacyBasis.DECREE),
        conflict=0,
        enacted_epoch=epoch,
        enacted_by_entity_id=by_id,
        locked=[],
    )
    session.add(profile)
    if holder is not None:
        session.add(LawJurisdictionRow(law_entity_id=law.id, node_entity_id=holder.id, jurisdiction=jurisdiction_of(holder)))
    await session.flush()
    return profile


def jurisdiction_of(holder: EntityRow) -> Jurisdiction:
    if holder.entity_type is EntityType.POLITY:
        return Jurisdiction.POLITY
    if holder.entity_type is EntityType.CULT:
        return Jurisdiction.CULT
    return Jurisdiction.SETTLEMENT


async def ensure_profile(session: AsyncSession, law: EntityRow, epoch: int, *, kind: LawKind = LawKind.CUSTOM) -> LawProfileRow:
    found = await session.get(LawProfileRow, law.id)
    if found is not None:
        return found
    holder = await session.get(EntityRow, law.location_id) if law.location_id is not None else None
    profile = await attach_profile(session, law, kind, {}, holder=holder, epoch=law.birth_epoch if law.birth_epoch is not None else epoch)
    return profile


async def backfill_kinds(session: AsyncSession, epoch: int) -> int:
    if await session.get(AppliedFixupRow, KIND_FIXUP) is not None:
        return 0
    laws = list(await session.scalars(select(EntityRow).where(EntityRow.entity_type == EntityType.LAW, EntityRow.status == EntityStatus.CANON)))
    known = set(await session.scalars(select(LawProfileRow.law_entity_id)))
    made = 0
    for law in laws:
        if law.id in known:
            continue
        await ensure_profile(session, law, epoch, kind=guess_kind(law))
        made += 1
    session.add(AppliedFixupRow(key=KIND_FIXUP, result={"laws": made}))
    await session.flush()
    return made


@dataclass
class LawBook:
    profiles: dict[int, LawProfileRow]
    laws: dict[int, EntityRow]
    by_node: dict[int, list[int]] = field(default_factory=lambda: defaultdict(list))
    member_of: dict[int, int] = field(default_factory=dict)
    cults_of: dict[int, list[int]] = field(default_factory=dict)

    @classmethod
    async def load(cls, session: AsyncSession) -> "LawBook":
        laws = {
            row.id: row
            for row in await session.scalars(select(EntityRow).where(EntityRow.entity_type == EntityType.LAW, EntityRow.status == EntityStatus.CANON))
        }
        profiles = {row.law_entity_id: row for row in await session.scalars(select(LawProfileRow)) if row.law_entity_id in laws}
        book = cls(profiles, laws)
        for row in await session.scalars(select(LawJurisdictionRow)):
            if row.law_entity_id in laws:
                book.by_node[row.node_entity_id].append(row.law_entity_id)
        for member in await session.scalars(select(PolityMemberRow)):
            book.member_of[member.member_entity_id] = member.polity_entity_id
        book.cults_of = await faithful_cults(session)
        return book

    def holders(self, node_id: int, kind: LawKind) -> list[int]:
        polity = self.member_of.get(node_id)
        cults = self.cults_of.get(node_id, [])
        ordered = [node_id, *cults, polity] if kind in CULT_FIRST else [node_id, polity, *cults]
        return [holder for holder in ordered if holder is not None]

    def in_force(self, node_id: int, kind: LawKind) -> LawProfileRow | None:
        for holder in self.holders(node_id, kind):
            found = [self.profiles[law_id] for law_id in self.by_node.get(holder, []) if law_id in self.profiles and self.profiles[law_id].kind is kind]
            if found:
                return max(found, key=lambda row: (row.enacted_epoch, row.law_entity_id))
        return None

    def param(self, node_id: int, kind: LawKind, key: str) -> ParamValue | None:
        row = self.in_force(node_id, kind)
        if row is None:
            return None
        return row.params.get(key, LAW_PARAMS[kind][key].default)

    def weight(self, node_id: int, kind: LawKind) -> float:
        row = self.in_force(node_id, kind)
        return row.enforcement / PERCENT if row is not None else 0.0


@memoized(LawJurisdictionRow, BondRow)
async def faithful_cults(session: AsyncSession) -> dict[int, list[int]]:
    cult_holders = set(await session.scalars(select(LawJurisdictionRow.node_entity_id).where(LawJurisdictionRow.jurisdiction == Jurisdiction.CULT)))
    if not cult_holders:
        return {}
    gods: dict[int, list[int]] = defaultdict(list)
    for source, target in await session.execute(
        select(BondRow.source_node_id, BondRow.target_node_id).where(
            BondRow.kind == BondKind.WORSHIPS, BondRow.state == BondState.ACTIVE, BondRow.source_node_id.in_(list(cult_holders))
        )
    ):
        gods[target].append(source)
    if not gods:
        return {}
    found: dict[int, list[int]] = defaultdict(list)
    for source, target in await session.execute(
        select(BondRow.source_node_id, BondRow.target_node_id)
        .where(BondRow.kind == BondKind.WORSHIPS, BondRow.state == BondState.ACTIVE, BondRow.target_node_id.in_(list(gods)))
        .order_by(BondRow.id)
    ):
        if source in cult_holders:
            continue
        for cult in gods[target]:
            if cult not in found[source]:
                found[source].append(cult)
    return dict(found)


async def law_param(session: AsyncSession, node_id: int, kind: LawKind, key: str) -> ParamValue | None:
    polity = await session.scalar(select(PolityMemberRow.polity_entity_id).where(PolityMemberRow.member_entity_id == node_id).limit(1))
    cults = (await faithful_cults(session)).get(node_id, [])
    ordered = [node_id, *cults, polity] if kind in CULT_FIRST else [node_id, polity, *cults]
    for holder in ordered:
        if holder is None:
            continue
        statement = (
            select(LawProfileRow)
            .join(LawJurisdictionRow, LawJurisdictionRow.law_entity_id == LawProfileRow.law_entity_id)
            .join(EntityRow, EntityRow.id == LawProfileRow.law_entity_id)
            .where(LawJurisdictionRow.node_entity_id == holder, LawProfileRow.kind == kind, EntityRow.status == EntityStatus.CANON)
            .order_by(LawProfileRow.enacted_epoch.desc(), LawProfileRow.law_entity_id.desc())
            .limit(1)
        )
        row = await session.scalar(statement)
        if row is not None:
            return row.params.get(key, LAW_PARAMS[kind][key].default)
    return None


def law_reading(kind: LawKind, params: Mapping[str, ParamValue], values: Mapping[ValueAxis, int]) -> int:
    leaning = KIND_VALUES.get(kind)
    if not leaning:
        return 0
    harsh = 1
    if kind is LawKind.SLAVERY:
        harsh = 1 if params.get("status") == "allowed" else -1
    elif kind is LawKind.PENAL_CODE:
        harsh = 1 if penal_cruelty(dict(params)) >= PERCENT // 2 else -1
    elif kind in {LawKind.RELIGIOUS_TOLERANCE, LawKind.FOREIGNER_RIGHTS}:
        harsh = -1 if params.get("level") in {"persecution", "none"} else 1
    reading = sum(values.get(axis, 0) * sign * harsh for axis, sign in leaning.items())
    return clamp_int(reading / max(1, len(leaning)), -PERCENT, PERCENT)


def discord(kind: LawKind, params: Mapping[str, ParamValue], values: Mapping[ValueAxis, int]) -> int:
    return clamp_int(-law_reading(kind, params, values), 0, PERCENT)


def justice_of(kind: LawKind, params: Mapping[str, ParamValue], values: Mapping[ValueAxis, int]) -> int:
    base = PERCENT - discord(kind, params, values)
    if kind is LawKind.PENAL_CODE:
        base -= penal_cruelty(dict(params)) // 3
    return clamp_int(base, 0, PERCENT)


async def enact(
    ctx: TickContext,
    holder: EntityRow,
    kind: LawKind,
    params: Mapping[str, ParamValue] | None = None,
    *,
    by_id: int | None = None,
    basis: LegitimacyBasis = LegitimacyBasis.DECREE,
    name: str | None = None,
) -> EntityRow:
    validate(kind, params or {})
    title = name or f"{LAW_TITLES.get(kind, 'the ' + kind.value.replace('_', ' ') + ' law').capitalize()} of {holder.name}"
    law = await create_record(
        ctx,
        RecordSpec(
            entity_type=EntityType.LAW,
            name=title,
            body=f"{holder.name} laid down {kind.value.replace('_', ' ')}.",
            stats=LawStats(rigidity=30 if basis is LegitimacyBasis.DECREE else 60, justice=50),
            power=2,
            location_id=holder.id,
            world_id=holder.world_id,
            subtype=kind.value.replace("_", " "),
            pending=False,
        ),
    )
    await attach_profile(ctx.session, law, kind, params, holder=holder, epoch=ctx.epoch, by_id=by_id, basis=basis)
    return law


async def repeal(ctx: TickContext, law: EntityRow, reason: str) -> None:
    await retire_in(ctx, law, reason, status=EntityStatus.DESTROYED)


async def edit_law(ctx: TickContext, law_id: int, params: Mapping[str, ParamValue], *, enforcement: int | None) -> LawProfileRow:
    law = await ctx.session.get(EntityRow, law_id)
    if law is None or law.entity_type is not EntityType.LAW:
        raise NotFoundError("No such law.")
    profile = await ensure_profile(ctx.session, law, ctx.epoch)
    profile.params = validate(profile.kind, {**profile.params, **params})
    if enforcement is not None:
        if not 0 <= enforcement <= PERCENT:
            raise ValidationFailedError(f"Enforcement runs from 0 to {PERCENT}.")
        profile.enforcement = enforcement
        profile.locked = profile.locked if "enforcement" in profile.locked else [*profile.locked, "enforcement"]
    await ctx.session.flush()
    return profile


def settle_justice(law: EntityRow, profile: LawProfileRow, values: Mapping[ValueAxis, int]) -> None:
    set_stats(law, justice=justice_of(profile.kind, profile.params, values))
