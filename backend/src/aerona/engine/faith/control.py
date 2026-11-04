from collections.abc import Mapping

from sqlalchemy import select

from aerona.catalog.tenets import DOMAIN_TENETS, OPPOSED, STRATUM_NAMES, VALUE_TENETS
from aerona.constants.units import PERCENT
from aerona.core.errors import ConflictError, NotFoundError, ValidationFailedError
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.faith import AfterlifeStratumRow, CultDoctrineRow, CultTenetRow, HeresyRow, RelicRow, SoulJudgementRow, SpiritProfileRow
from aerona.domain.enums.entity import EntityStatus, EntityType
from aerona.domain.enums.faith import AfterlifeState, BindingKind, JudgementDoctrine, ReincarnationGate, SpiritAlignment, StratumKind, TenetKind
from aerona.engine.context import TickContext
from aerona.engine.faith.book import FaithBook
from aerona.engine.faith.doctrine import found_doctrine
from aerona.engine.faith.souls import home_of, rebirth
from aerona.engine.faith.works import canonise
from aerona.engine.faith.zealotry import record_heresy
from aerona.engine.mind.book import values_for
from aerona.engine.polity.control import lock
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.primitives.queries import living_entity
from aerona.engine.primitives.records import retire_in
from aerona.engine.primitives.stats import set_stats

Values = Mapping[str, int | str | bool | None]
PERCENT_FIELDS = frozenset({"orthodoxy", "tithe_rate", "clergy_quality", "doctrinal_distance"})
POSITIVE_FIELDS = frozenset({"treasury", "clergy_count"})
SPIRIT_PERCENT = frozenset({"memory_strength", "veneration"})


def percent(key: str, value: object) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or not 0 <= value <= PERCENT:
        raise ValidationFailedError(f"{key.replace('_', ' ').capitalize()} runs from 0 to {PERCENT}.")
    return value


async def church(ctx: TickContext, cult_id: int) -> tuple[FaithBook, CultDoctrineRow]:
    book = await FaithBook.load(ctx.session)
    found = book.churches.get(cult_id)
    if found is None:
        raise NotFoundError("No such living cult.")
    doctrine = found.doctrine or await found_doctrine(ctx, found)
    return book, doctrine


async def edit_doctrine(ctx: TickContext, cult_id: int, values: Values, *, release: list[str]) -> CultDoctrineRow:
    _, doctrine = await church(ctx, cult_id)
    for key, value in values.items():
        if key in PERCENT_FIELDS:
            setattr(doctrine, key, percent(key, value))
        elif key in POSITIVE_FIELDS:
            if not isinstance(value, int) or value < 0:
                raise ValidationFailedError(f"{key.replace('_', ' ').capitalize()} cannot be negative.")
            setattr(doctrine, key, value)
        elif key == "judgement":
            try:
                doctrine.judgement = JudgementDoctrine(str(value))
            except ValueError as error:
                raise ValidationFailedError(f"{value} is not a known judgement.") from error
        elif key == "zeal":
            cult = await ctx.session.get(EntityRow, cult_id)
            if cult is not None:
                set_stats(cult, zeal=percent(key, value))
        else:
            raise ValidationFailedError(f"Unknown doctrine field: {key}.")
        doctrine.locked = lock(doctrine.locked, key)
    for key in release:
        doctrine.locked = [item for item in doctrine.locked if item != key]
    await ctx.session.flush()
    return doctrine


async def set_tenet(ctx: TickContext, cult_id: int, tenet: TenetKind, *, held: bool, target: str | None, son_id: int | None) -> CultTenetRow | None:
    await church(ctx, cult_id)
    row = await ctx.session.get(CultTenetRow, (cult_id, tenet))
    if not held:
        if row is not None:
            await ctx.session.delete(row)
            await ctx.session.flush()
        return None
    for other in await ctx.session.scalars(select(CultTenetRow.tenet).where(CultTenetRow.cult_entity_id == cult_id)):
        if frozenset({tenet, other}) in OPPOSED:
            raise ConflictError(f"{tenet.value.replace('_', ' ')} cannot stand beside {other.value.replace('_', ' ')}.")
    if son_id is not None and await revelation_fit(ctx, cult_id, tenet) < ctx.rules.doctrine.reveal_fit:
        raise ConflictError(f"The faithful will not accept {tenet.value.replace('_', ' ')}; it is too far from what they believe.")
    if row is None:
        row = CultTenetRow(cult_entity_id=cult_id, tenet=tenet, since_epoch=ctx.epoch, revealed_by_son_id=son_id)
        ctx.session.add(row)
    row.target = target
    await ctx.session.flush()
    return row


async def revelation_fit(ctx: TickContext, cult_id: int, tenet: TenetKind) -> int:
    book = await FaithBook.load(ctx.session)
    found = book.churches.get(cult_id)
    god = found.god if found is not None else None
    if god is not None and tenet in (*DOMAIN_TENETS.get(god.domain_primary, ()), *DOMAIN_TENETS.get(god.domain_secondary, ())):
        return PERCENT
    values = await values_for(ctx.session, cult_id)
    fits = [value for axis, (high, _) in VALUE_TENETS.items() if high is tenet for value in [values.get(axis, 0)]]
    fits += [-value for axis, (_, low) in VALUE_TENETS.items() if low is tenet for value in [values.get(axis, 0)]]
    return clamp_int(PERCENT // 2 + (max(fits) // 2 if fits else 0), 0, PERCENT)


async def declare_heresy(ctx: TickContext, heresy_id: int, parent_id: int) -> HeresyRow:
    heresy, parent = await living_entity(ctx.session, heresy_id), await living_entity(ctx.session, parent_id)
    if heresy is None or parent is None or heresy.entity_type is not EntityType.CULT or parent.entity_type is not EntityType.CULT or heresy.id == parent.id:
        raise ValidationFailedError("Name two different living cults: the heresy and its mother church.")
    existing = await ctx.session.get(HeresyRow, heresy.id)
    if existing is not None:
        existing.parent_entity_id = parent.id
        await ctx.session.flush()
        return existing
    await church(ctx, parent.id)
    row = await record_heresy(ctx, heresy, parent.id)
    await ctx.session.flush()
    return row


async def judge_heresy(ctx: TickContext, heresy_id: int, *, suppressed: bool) -> HeresyRow:
    row = await ctx.session.get(HeresyRow, heresy_id)
    if row is None:
        raise NotFoundError("No such heresy.")
    row.suppressed, row.tolerated = suppressed, not suppressed
    await ctx.session.flush()
    return row


async def canonise_saint(ctx: TickContext, cult_id: int, saint_id: int, item_id: int | None) -> RelicRow:
    book, _ = await church(ctx, cult_id)
    saint = await ctx.session.get(EntityRow, saint_id)
    if saint is None or saint.entity_type is not EntityType.MORTAL:
        raise ValidationFailedError("Only a mortal can be named a saint.")
    item = await living_entity(ctx.session, item_id) if item_id is not None else None
    row = await canonise(ctx, book.churches[cult_id], saint, item)
    await ctx.session.flush()
    return row


async def spirit_profile(ctx: TickContext, spirit_id: int) -> tuple[EntityRow, SpiritProfileRow]:
    spirit = await ctx.session.get(EntityRow, spirit_id)
    if spirit is None or spirit.entity_type is not EntityType.SPIRIT:
        raise NotFoundError("No such spirit.")
    profile = await ctx.session.get(SpiritProfileRow, spirit_id)
    if profile is None:
        profile = SpiritProfileRow(
            spirit_entity_id=spirit_id, imprint={}, traits=[], deeds={}, memory_strength=PERCENT, veneration=0, updated_epoch=ctx.epoch, locked=[]
        )
        ctx.session.add(profile)
    return spirit, profile


async def judge_soul(ctx: TickContext, spirit_id: int, stratum_id: int, reason: str) -> SpiritProfileRow:
    spirit, profile = await spirit_profile(ctx, spirit_id)
    stratum = await ctx.session.get(AfterlifeStratumRow, stratum_id)
    if stratum is None:
        raise NotFoundError("No such stratum of the afterlife.")
    old = await ctx.session.get(AfterlifeStratumRow, profile.stratum_id) if profile.stratum_id is not None else None
    if old is not None and old.population > 0:
        old.population -= 1
    stratum.population += 1
    profile.stratum_id, profile.state = stratum.id, AfterlifeState.IN_REALM
    ctx.session.add(
        SoulJudgementRow(
            spirit_entity_id=spirit.id,
            son_id=profile.patron_son_id,
            doctrine=JudgementDoctrine.FAVOUR,
            stratum_id=stratum.id,
            score=PERCENT,
            rite=profile.rite,
            reason=(reason or "judged by the Creator's hand")[:480],
            epoch=ctx.epoch,
        )
    )
    await ctx.session.flush()
    return profile


async def release_soul(ctx: TickContext, spirit_id: int) -> SpiritProfileRow:
    spirit, profile = await spirit_profile(ctx, spirit_id)
    if spirit.status is not EntityStatus.CANON:
        raise ConflictError(f"{spirit.name} is already gone.")
    profile.state = AfterlifeState.RELEASED
    await retire_in(ctx, spirit, "released from all bonds of the afterlife", close_bonds=True)
    return profile


async def bind_spirit(ctx: TickContext, spirit_id: int, target_id: int, binding: BindingKind) -> SpiritProfileRow:
    _, profile = await spirit_profile(ctx, spirit_id)
    target = await living_entity(ctx.session, target_id)
    if target is None:
        raise NotFoundError("Nothing to bind the spirit to.")
    profile.binding, profile.bound_entity_id = binding, target.id
    await ctx.session.flush()
    return profile


async def seal_soul(ctx: TickContext, spirit_id: int, *, sealed: bool) -> SpiritProfileRow:
    _, profile = await spirit_profile(ctx, spirit_id)
    profile.sealed = sealed
    await ctx.session.flush()
    return profile


async def reincarnate_soul(ctx: TickContext, spirit_id: int, community_id: int | None) -> EntityRow:
    spirit, profile = await spirit_profile(ctx, spirit_id)
    if spirit.status is not EntityStatus.CANON:
        raise ConflictError(f"{spirit.name} has already gone on.")
    if profile.sealed:
        raise ConflictError(f"{spirit.name} is sealed against return.")
    home = await living_entity(ctx.session, community_id) if community_id is not None else await home_of(ctx, profile)
    if home is None:
        raise ValidationFailedError("Name a living community for the soul to be born into.")
    return await rebirth(ctx, profile, spirit, home, ReincarnationGate.GOD)


async def edit_spirit(ctx: TickContext, spirit_id: int, values: Values) -> SpiritProfileRow:
    _, profile = await spirit_profile(ctx, spirit_id)
    for key, value in values.items():
        if key in SPIRIT_PERCENT:
            setattr(profile, key, percent(key, value))
        elif key == "alignment":
            try:
                profile.alignment = SpiritAlignment(str(value))
            except ValueError as error:
                raise ValidationFailedError(f"{value} is not a known alignment.") from error
        else:
            raise ValidationFailedError(f"Unknown spirit field: {key}.")
        profile.locked = lock(profile.locked, key)
    await ctx.session.flush()
    return profile


async def set_stratum(
    ctx: TickContext, realm_id: int, kind: StratumKind, *, name: str | None, criteria: dict[str, int | str] | None, remove: bool
) -> AfterlifeStratumRow | None:
    realm = await living_entity(ctx.session, realm_id)
    if realm is None:
        raise NotFoundError("No such realm of the dead.")
    row = await ctx.session.scalar(
        select(AfterlifeStratumRow).where(AfterlifeStratumRow.realm_entity_id == realm.id, AfterlifeStratumRow.kind == kind).limit(1)
    )
    if remove:
        if row is not None:
            await ctx.session.delete(row)
            await ctx.session.flush()
        return None
    if row is None:
        row = AfterlifeStratumRow(realm_entity_id=realm.id, kind=kind, name=f"{STRATUM_NAMES[kind]} of {realm.name}"[:200], criteria={}, population=0)
        ctx.session.add(row)
    if name:
        row.name = name.strip()[:200]
    if criteria is not None:
        row.criteria = dict(criteria)
    await ctx.session.flush()
    return row
