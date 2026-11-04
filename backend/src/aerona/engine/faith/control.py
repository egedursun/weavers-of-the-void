from collections.abc import Awaitable, Callable, Mapping, Sequence

from pydantic import ValidationError
from sqlalchemy import delete, select

from aerona.catalog.tenets import DOMAIN_TENETS, OPPOSED, STRATUM_NAMES, VALUE_TENETS
from aerona.constants.units import PERCENT
from aerona.core.errors import ConflictError, NotFoundError, ValidationFailedError
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.faith import (
    AfterlifeStratumRow,
    CultDoctrineRow,
    CultHoldingRow,
    CultOfficeRow,
    CultTenetRow,
    HeresyRow,
    PossessionRow,
    RelicRow,
    SoulJudgementRow,
    SpiritProfileRow,
)
from aerona.db.tables.sons import SonRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import COMMUNITY_TYPES, EntityStatus, EntityType
from aerona.domain.enums.faith import (
    AfterlifeState,
    BindingKind,
    ClergyOffice,
    FanaticismKind,
    FuneralRite,
    HoldingKind,
    JudgementDoctrine,
    RebirthPath,
    ReincarnationGate,
    SpiritAlignment,
    StratumKind,
    TenetKind,
)
from aerona.domain.enums.mind import TraitKind, ValueAxis
from aerona.domain.models.entity_stats import SpiritStats
from aerona.domain.models.faith import StratumCriteria
from aerona.engine.context import TickContext
from aerona.engine.faith.book import Church, FaithBook
from aerona.engine.faith.doctrine import found_doctrine
from aerona.engine.faith.judgement import ledger, new_stratum, place, profile_for, recount, seal, unseal
from aerona.engine.faith.souls import home_of, rebirth, release_host, take_host
from aerona.engine.faith.works import canonise
from aerona.engine.faith.zealotry import record_heresy
from aerona.engine.mind.book import values_for
from aerona.engine.polity.control import lock
from aerona.engine.primitives.numbers import clamp_int
from aerona.engine.primitives.queries import connect, living_entity
from aerona.engine.primitives.records import RecordSpec, open_record, retire_in
from aerona.engine.primitives.stats import set_stats

Values = Mapping[str, object]
PERCENT_FIELDS = frozenset({"orthodoxy", "tithe_rate", "clergy_quality", "doctrinal_distance"})
POSITIVE_FIELDS = frozenset({"treasury", "clergy_count"})
SPIRIT_PERCENT = frozenset({"memory_strength", "veneration", "seal_strength"})
DEEDS = ("renown", "honour", "faith", "violence", "infamy")
VALUE_SPAN = 100


def percent(key: str, value: object) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or not 0 <= value <= PERCENT:
        raise ValidationFailedError(f"{key.replace('_', ' ').capitalize()} runs from 0 to {PERCENT}.")
    return value


def count(key: str, value: object) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValidationFailedError(f"{key.replace('_', ' ').capitalize()} cannot be negative.")
    return value


def choice[E: (JudgementDoctrine, RebirthPath, FanaticismKind, SpiritAlignment, FuneralRite, AfterlifeState)](kind: type[E], key: str, value: object) -> E:
    try:
        return kind(str(value))
    except ValueError as error:
        raise ValidationFailedError(f"{value} is not a known {key.replace('_', ' ')}.") from error


def release_keys(locked: list[str], release: Sequence[str]) -> list[str]:
    return [item for item in locked if item not in set(release)]


async def church(ctx: TickContext, cult_id: int) -> tuple[FaithBook, CultDoctrineRow]:
    book = await FaithBook.load(ctx.session)
    found = book.churches.get(cult_id)
    if found is None:
        raise NotFoundError("No such living cult.")
    doctrine = found.doctrine or await found_doctrine(ctx, found)
    return book, doctrine


async def entity_of(ctx: TickContext, entity_id: object, kinds: set[EntityType], message: str) -> EntityRow:
    found = await living_entity(ctx.session, entity_id) if isinstance(entity_id, int) and not isinstance(entity_id, bool) else None
    if found is None or found.entity_type not in kinds:
        raise ValidationFailedError(message)
    return found


async def set_fanaticism(ctx: TickContext, doctrine: CultDoctrineRow, value: object) -> None:
    doctrine.fanaticism = None if value is None else choice(FanaticismKind, "fanaticism", value)
    doctrine.fanaticism_epoch = ctx.epoch if value is not None else None


async def set_liturgy(ctx: TickContext, doctrine: CultDoctrineRow, value: object) -> None:
    doctrine.liturgical_language_id = (
        None if value is None else (await entity_of(ctx, value, {EntityType.LANGUAGE}, "The liturgy must be a living language.")).id
    )


async def set_mother(ctx: TickContext, doctrine: CultDoctrineRow, value: object) -> None:
    parent = None if value is None else await entity_of(ctx, value, {EntityType.CULT}, "The mother church must be a living cult.")
    if parent is not None and parent.id == doctrine.cult_entity_id:
        raise ValidationFailedError("A faith cannot be its own mother church.")
    doctrine.parent_cult_id = parent.id if parent is not None else None


async def set_outcasts(ctx: TickContext, doctrine: CultDoctrineRow, value: object) -> None:
    if not isinstance(value, list):
        raise ValidationFailedError("Name the cast-out as a list of mortals.")
    doctrine.excommunicated = [(await entity_of(ctx, item, {EntityType.MORTAL}, "Only living mortals can be cast out.")).id for item in value]


async def set_zeal_parts(ctx: TickContext, doctrine: CultDoctrineRow, value: object) -> None:
    if not isinstance(value, dict) or not all(isinstance(part, str) and isinstance(amount, int) for part, amount in value.items()):
        raise ValidationFailedError("Zeal parts are named amounts.")
    doctrine.zeal_parts = {str(part)[:80]: int(amount) for part, amount in value.items()}


async def set_judgement(ctx: TickContext, doctrine: CultDoctrineRow, value: object) -> None:
    doctrine.judgement = choice(JudgementDoctrine, "judgement", value)


async def set_rebirth_path(ctx: TickContext, doctrine: CultDoctrineRow, value: object) -> None:
    doctrine.rebirth_path = choice(RebirthPath, "rebirth_path", value)


DoctrineSetter = Callable[[TickContext, CultDoctrineRow, object], Awaitable[None]]
DOCTRINE_SETTERS: dict[str, DoctrineSetter] = {
    "judgement": set_judgement,
    "rebirth_path": set_rebirth_path,
    "fanaticism": set_fanaticism,
    "liturgical_language_id": set_liturgy,
    "parent_cult_id": set_mother,
    "excommunicated": set_outcasts,
    "zeal_parts": set_zeal_parts,
}


async def doctrine_field(ctx: TickContext, doctrine: CultDoctrineRow, key: str, value: object) -> None:
    if key in PERCENT_FIELDS:
        setattr(doctrine, key, percent(key, value))
    elif key in POSITIVE_FIELDS:
        setattr(doctrine, key, count(key, value))
    elif key in DOCTRINE_SETTERS:
        await DOCTRINE_SETTERS[key](ctx, doctrine, value)
    else:
        raise ValidationFailedError(f"Unknown doctrine field: {key}.")


async def edit_doctrine(ctx: TickContext, cult_id: int, values: Values, *, release: list[str]) -> CultDoctrineRow:
    _, doctrine = await church(ctx, cult_id)
    cult = await ctx.session.get(EntityRow, cult_id)
    for key, value in values.items():
        if key in {"zeal", "devotion"}:
            if cult is not None:
                set_stats(cult, **{key: percent(key, value) if key == "zeal" else count(key, value)})
        else:
            await doctrine_field(ctx, doctrine, key, value)
        doctrine.locked = lock(doctrine.locked, key)
    doctrine.locked = release_keys(doctrine.locked, release)
    await ctx.session.flush()
    return doctrine


async def reset_doctrine(ctx: TickContext, cult_id: int) -> CultDoctrineRow:
    book = await FaithBook.load(ctx.session)
    found = book.churches.get(cult_id)
    if found is None:
        raise NotFoundError("No such living cult.")
    await ctx.session.execute(delete(CultTenetRow).where(CultTenetRow.cult_entity_id == cult_id))
    await ctx.session.execute(delete(CultOfficeRow).where(CultOfficeRow.cult_entity_id == cult_id))
    if found.doctrine is not None:
        await ctx.session.delete(found.doctrine)
    await ctx.session.flush()
    fresh = Church(found.cult, None, {}, found.god, found.members)
    doctrine = await found_doctrine(ctx, fresh)
    await ctx.session.flush()
    return doctrine


async def set_tenet(
    ctx: TickContext, cult_id: int, tenet: TenetKind, *, held: bool, target: str | None, son_id: int | None, name: str | None = None
) -> CultTenetRow | None:
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
    if name is not None:
        row.name = name.strip()[:200] or None
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


async def set_office(ctx: TickContext, cult_id: int, kind: ClergyOffice, *, holder_id: int | None, locked: bool | None, remove: bool) -> CultOfficeRow | None:
    await church(ctx, cult_id)
    row = await ctx.session.scalar(select(CultOfficeRow).where(CultOfficeRow.cult_entity_id == cult_id, CultOfficeRow.kind == kind).limit(1))
    if remove:
        if row is not None:
            await ctx.session.delete(row)
            await ctx.session.flush()
        return None
    if row is None:
        row = CultOfficeRow(cult_entity_id=cult_id, kind=kind, since_epoch=ctx.epoch, locked=False)
        ctx.session.add(row)
    if holder_id is not None:
        holder = await entity_of(ctx, holder_id, {EntityType.MORTAL}, "Only a living mortal can hold a clergy office.")
        row.holder_entity_id, row.since_epoch = holder.id, ctx.epoch
        row.locked = True
    if locked is not None:
        row.locked = locked
    await ctx.session.flush()
    return row


async def set_holding(ctx: TickContext, cult_id: int, entity_id: int, kind: HoldingKind, *, remove: bool) -> CultHoldingRow | None:
    await church(ctx, cult_id)
    row = await ctx.session.get(CultHoldingRow, (cult_id, entity_id))
    if remove:
        if row is not None:
            await ctx.session.delete(row)
            await ctx.session.flush()
        return None
    target = await living_entity(ctx.session, entity_id)
    if target is None:
        raise NotFoundError("Nothing living to hold.")
    if row is None:
        row = CultHoldingRow(cult_entity_id=cult_id, holding_entity_id=target.id, kind=kind, since_epoch=ctx.epoch)
        ctx.session.add(row)
    row.kind = kind
    await ctx.session.flush()
    return row


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
    return await edit_heresy(ctx, heresy_id, {"suppressed": suppressed, "tolerated": not suppressed}, release=[])


async def edit_heresy(ctx: TickContext, heresy_id: int, values: Values, *, release: list[str]) -> HeresyRow:
    row = await ctx.session.get(HeresyRow, heresy_id)
    if row is None:
        raise NotFoundError("No such heresy.")
    for key, value in values.items():
        if key == "distance":
            row.distance = percent(key, value)
        elif key in {"suppressed", "tolerated"}:
            if not isinstance(value, bool):
                raise ValidationFailedError(f"{key.capitalize()} is yes or no.")
            setattr(row, key, value)
        else:
            raise ValidationFailedError(f"Unknown heresy field: {key}.")
        row.locked = lock(row.locked, key)
    row.locked = release_keys(row.locked, release)
    await ctx.session.flush()
    return row


async def undeclare_heresy(ctx: TickContext, heresy_id: int) -> int:
    row = await ctx.session.get(HeresyRow, heresy_id)
    if row is None:
        raise NotFoundError("No such heresy.")
    parent = row.parent_entity_id
    await ctx.session.delete(row)
    await ctx.session.flush()
    return parent


async def canonise_saint(ctx: TickContext, cult_id: int, saint_id: int, item_id: int | None) -> RelicRow:
    book, _ = await church(ctx, cult_id)
    saint = await ctx.session.get(EntityRow, saint_id)
    if saint is None or saint.entity_type is not EntityType.MORTAL:
        raise ValidationFailedError("Only a mortal can be named a saint.")
    item = await living_entity(ctx.session, item_id) if item_id is not None else None
    row = await canonise(ctx, book.churches[cult_id], saint, item)
    await ctx.session.flush()
    return row


async def edit_relic(ctx: TickContext, item_id: int, values: Values, *, release: list[str]) -> RelicRow:
    row = await ctx.session.get(RelicRow, item_id)
    if row is None:
        raise NotFoundError("No such relic.")
    for key, value in values.items():
        if key == "sanctity":
            row.sanctity = percent(key, value)
        elif key == "pilgrims":
            row.pilgrims = count(key, value)
        elif key == "shrine_id":
            row.shrine_entity_id = None if value is None else (await entity_of(ctx, value, set(COMMUNITY_TYPES), "A shrine stands in a living community.")).id
        elif key == "cult_id":
            row.cult_entity_id = (await entity_of(ctx, value, {EntityType.CULT}, "A relic is kept by a living cult.")).id
        elif key == "saint_id":
            saint = await ctx.session.get(EntityRow, value) if isinstance(value, int) else None
            if saint is None or saint.entity_type is not EntityType.MORTAL:
                raise ValidationFailedError("A relic's saint is a mortal.")
            row.saint_entity_id = saint.id
        else:
            raise ValidationFailedError(f"Unknown relic field: {key}.")
        row.locked = lock(row.locked, key)
    row.locked = release_keys(row.locked, release)
    await ctx.session.flush()
    return row


async def remove_relic(ctx: TickContext, item_id: int) -> int | None:
    row = await ctx.session.get(RelicRow, item_id)
    if row is None:
        raise NotFoundError("No such relic.")
    cult = row.cult_entity_id
    if cult is not None:
        holding = await ctx.session.get(CultHoldingRow, (cult, item_id))
        if holding is not None:
            await ctx.session.delete(holding)
    await ctx.session.delete(row)
    await ctx.session.flush()
    return cult


async def spirit_profile(ctx: TickContext, spirit_id: int) -> tuple[EntityRow, SpiritProfileRow]:
    spirit = await ctx.session.get(EntityRow, spirit_id)
    if spirit is None or spirit.entity_type is not EntityType.SPIRIT:
        raise NotFoundError("No such spirit.")
    profile = await ctx.session.get(SpiritProfileRow, spirit_id)
    if profile is None:
        profile = SpiritProfileRow(
            spirit_entity_id=spirit_id,
            imprint={},
            traits=[],
            deeds=dict.fromkeys(DEEDS, 0),
            memory_strength=PERCENT,
            veneration=0,
            seal_strength=0,
            updated_epoch=ctx.epoch,
            locked=[],
        )
        ctx.session.add(profile)
    return spirit, profile


async def raise_soul(ctx: TickContext, mortal_id: int, *, alignment: SpiritAlignment, place_id: int | None) -> EntityRow:
    mortal = await ctx.session.get(EntityRow, mortal_id)
    if mortal is None or mortal.entity_type is not EntityType.MORTAL or mortal.status is not EntityStatus.DEAD:
        raise ValidationFailedError("Only a dead mortal leaves a soul.")
    known = await ctx.session.scalar(select(SpiritProfileRow.spirit_entity_id).where(SpiritProfileRow.origin_mortal_id == mortal.id).limit(1))
    if known is not None:
        raise ConflictError(f"The soul of {mortal.name} already walks.")
    where = await living_entity(ctx.session, place_id) if place_id is not None else await living_entity(ctx.session, mortal.location_id)
    spirit = await open_record(
        ctx.session,
        ctx.epoch,
        RecordSpec(
            entity_type=EntityType.SPIRIT,
            name=f"Spirit of {mortal.name}"[:200],
            body=f"The Creator called up the soul of {mortal.name}.",
            stats=SpiritStats(strength=PERCENT // 2, unrest=0),
            power=max(1, mortal.power_level),
            location_id=where.id if where is not None else None,
            world_id=where.world_id if where is not None else mortal.world_id,
        ),
    )
    await connect(ctx.session, spirit.id, mortal.id, BondKind.DESCENDS_FROM, ctx.epoch, description="their spirit")
    profile = await profile_for(ctx, spirit, mortal)
    profile.alignment = alignment
    profile.locked = lock(profile.locked, "alignment")
    await ctx.session.flush()
    return spirit


async def judge_soul(ctx: TickContext, spirit_id: int, stratum_id: int, reason: str) -> SpiritProfileRow:
    spirit, profile = await spirit_profile(ctx, spirit_id)
    stratum = await ctx.session.get(AfterlifeStratumRow, stratum_id)
    if stratum is None:
        raise NotFoundError("No such stratum of the afterlife.")
    await place(ctx, profile, stratum)
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
    for row in list(await ctx.session.scalars(select(PossessionRow).where(PossessionRow.spirit_entity_id == spirit.id))):
        await release_host(ctx, row)
    profile.state = AfterlifeState.RELEASED
    await retire_in(ctx, spirit, "released from all bonds of the afterlife", close_bonds=True)
    if profile.stratum_id is not None:
        await recount(ctx, {profile.stratum_id})
    return profile


async def bind_spirit(ctx: TickContext, spirit_id: int, target_id: int, binding: BindingKind) -> SpiritProfileRow:
    _, profile = await spirit_profile(ctx, spirit_id)
    if binding is BindingKind.NONE:
        profile.binding, profile.bound_entity_id = BindingKind.NONE, None
        await ctx.session.flush()
        return profile
    target = await living_entity(ctx.session, target_id)
    if target is None:
        raise NotFoundError("Nothing to bind the spirit to.")
    profile.binding, profile.bound_entity_id = binding, target.id
    profile.locked = lock(profile.locked, "binding")
    await ctx.session.flush()
    return profile


async def seal_soul(ctx: TickContext, spirit_id: int, *, sealed: bool, strength: int | None = None) -> SpiritProfileRow:
    _, profile = await spirit_profile(ctx, spirit_id)
    profile.locked = release_keys(profile.locked, ["sealed"])
    if sealed:
        seal(profile, percent("seal strength", strength) if strength is not None else PERCENT)
        if strength is not None:
            profile.seal_strength = strength
    else:
        unseal(profile)
    profile.locked = lock(profile.locked, "sealed")
    await ctx.session.flush()
    return profile


async def reincarnate_soul(ctx: TickContext, spirit_id: int, community_id: int | None, *, gate: ReincarnationGate = ReincarnationGate.GOD) -> EntityRow:
    spirit, profile = await spirit_profile(ctx, spirit_id)
    if spirit.status is not EntityStatus.CANON:
        raise ConflictError(f"{spirit.name} has already gone on.")
    if profile.sealed:
        raise ConflictError(f"{spirit.name} is sealed against return.")
    home = await living_entity(ctx.session, community_id) if community_id is not None else await home_of(ctx, profile)
    if home is None or home.entity_type not in COMMUNITY_TYPES:
        raise ValidationFailedError("Name a living community for the soul to be born into.")
    return await rebirth(ctx, profile, spirit, home, gate)


async def set_spirit_state(ctx: TickContext, profile: SpiritProfileRow, value: object) -> None:
    state = choice(AfterlifeState, "state", value)
    if state not in {AfterlifeState.WANDERING, AfterlifeState.JUDGED, AfterlifeState.IN_REALM}:
        raise ValidationFailedError("Use release or rebirth to end a soul's walk.")
    if state is AfterlifeState.IN_REALM and profile.stratum_id is None:
        raise ValidationFailedError("Judge the soul into a stratum first.")
    profile.state = state
    if profile.stratum_id is not None:
        await recount(ctx, {profile.stratum_id})


async def set_deeds(ctx: TickContext, profile: SpiritProfileRow, value: object) -> None:
    if not isinstance(value, dict) or set(value) - set(DEEDS):
        raise ValidationFailedError(f"Deeds are {', '.join(DEEDS)}.")
    profile.deeds = {**dict.fromkeys(DEEDS, 0), **dict(profile.deeds or {}), **{deed: percent(deed, amount) for deed, amount in value.items()}}


async def set_imprint(ctx: TickContext, profile: SpiritProfileRow, value: object) -> None:
    if not isinstance(value, dict):
        raise ValidationFailedError("An imprint is a set of values.")
    imprint: dict[str, int] = {}
    for axis, amount in value.items():
        if axis not in {item.value for item in ValueAxis} or not isinstance(amount, int) or not -VALUE_SPAN <= amount <= VALUE_SPAN:
            raise ValidationFailedError(f"{axis} is not a value between -{VALUE_SPAN} and {VALUE_SPAN}.")
        imprint[str(axis)] = amount
    profile.imprint = imprint


async def set_traits(ctx: TickContext, profile: SpiritProfileRow, value: object) -> None:
    if not isinstance(value, list) or any(item not in {trait.value for trait in TraitKind} for item in value):
        raise ValidationFailedError("Traits must be known traits.")
    profile.traits = sorted({str(item) for item in value})


async def set_patron(ctx: TickContext, profile: SpiritProfileRow, value: object) -> None:
    son = await ctx.session.get(SonRow, value) if isinstance(value, int) else None
    if value is not None and son is None:
        raise ValidationFailedError("No such god.")
    profile.patron_son_id = son.id if son is not None else None


async def set_alignment(ctx: TickContext, profile: SpiritProfileRow, value: object) -> None:
    profile.alignment = choice(SpiritAlignment, "alignment", value)


async def set_rite(ctx: TickContext, profile: SpiritProfileRow, value: object) -> None:
    profile.rite = choice(FuneralRite, "rite", value)


SpiritSetter = Callable[[TickContext, SpiritProfileRow, object], Awaitable[None]]
SPIRIT_SETTERS: dict[str, SpiritSetter] = {
    "alignment": set_alignment,
    "rite": set_rite,
    "state": set_spirit_state,
    "deeds": set_deeds,
    "imprint": set_imprint,
    "traits": set_traits,
    "patron_son_id": set_patron,
}


async def spirit_field(ctx: TickContext, profile: SpiritProfileRow, key: str, value: object) -> None:
    if key in SPIRIT_PERCENT:
        setattr(profile, key, percent(key, value))
    elif key in SPIRIT_SETTERS:
        await SPIRIT_SETTERS[key](ctx, profile, value)
    else:
        raise ValidationFailedError(f"Unknown spirit field: {key}.")


async def edit_spirit(ctx: TickContext, spirit_id: int, values: Values, *, release: Sequence[str] = ()) -> SpiritProfileRow:
    _, profile = await spirit_profile(ctx, spirit_id)
    for key, value in values.items():
        await spirit_field(ctx, profile, key, value)
        profile.locked = lock(profile.locked, key)
    profile.locked = release_keys(profile.locked, release)
    await ctx.session.flush()
    return profile


async def refresh_ledger(ctx: TickContext, spirit_id: int) -> SpiritProfileRow:
    _, profile = await spirit_profile(ctx, spirit_id)
    mortal = await ctx.session.get(EntityRow, profile.origin_mortal_id) if profile.origin_mortal_id is not None else None
    if mortal is None:
        raise ConflictError("This spirit was never a mortal; it has no deeds to read.")
    profile.deeds = await ledger(ctx, mortal)
    profile.locked = release_keys(profile.locked, ["deeds"])
    await ctx.session.flush()
    return profile


async def possess_host(ctx: TickContext, spirit_id: int, host_id: int) -> PossessionRow:
    spirit, profile = await spirit_profile(ctx, spirit_id)
    if spirit.status is not EntityStatus.CANON:
        raise ConflictError(f"{spirit.name} is gone.")
    host = await entity_of(ctx, host_id, {EntityType.MORTAL}, "Only a living mortal can be possessed.")
    if await ctx.session.get(PossessionRow, host.id) is not None:
        raise ConflictError(f"{host.name} is already possessed.")
    return await take_host(ctx, profile, spirit, host)


async def edit_possession(ctx: TickContext, host_id: int, values: Values, *, release: Sequence[str] = ()) -> PossessionRow:
    row = await ctx.session.get(PossessionRow, host_id)
    if row is None:
        raise NotFoundError("No one is possessed there.")
    for key, value in values.items():
        if key != "stress":
            raise ValidationFailedError(f"Unknown possession field: {key}.")
        row.stress = percent(key, value)
        row.locked = lock(row.locked, key)
    row.locked = release_keys(row.locked, release)
    await ctx.session.flush()
    return row


async def exorcise_host(ctx: TickContext, host_id: int) -> int:
    row = await ctx.session.get(PossessionRow, host_id)
    if row is None:
        raise NotFoundError("No one is possessed there.")
    spirit = row.spirit_entity_id
    await release_host(ctx, row)
    return spirit


def criteria_of(raw: Mapping[str, object] | StratumCriteria | None) -> StratumCriteria | None:
    if raw is None or isinstance(raw, StratumCriteria):
        return raw
    try:
        return StratumCriteria.model_validate(dict(raw))
    except ValidationError as error:
        raise ValidationFailedError(f"The entry rule is not valid: {error.errors()[0]['msg']}.") from error


async def set_stratum(
    ctx: TickContext,
    realm_id: int,
    kind: StratumKind,
    *,
    name: str | None,
    criteria: Mapping[str, object] | StratumCriteria | None,
    remove: bool,
    stratum_id: int | None = None,
    son_id: int | None = None,
    cult_id: int | None = None,
    closed: bool | None = None,
    clear_links: bool = False,
) -> AfterlifeStratumRow | None:
    realm = await living_entity(ctx.session, realm_id)
    if realm is None:
        raise NotFoundError("No such realm of the dead.")
    row = await ctx.session.get(AfterlifeStratumRow, stratum_id) if stratum_id is not None else None
    if stratum_id is not None and (row is None or row.realm_entity_id != realm.id):
        raise NotFoundError("No such stratum in this realm.")
    if remove:
        if row is not None:
            await unmake_stratum(ctx, row)
        return None
    if row is None:
        row = new_stratum(ctx.rules, realm, kind)
        ctx.session.add(row)
    row.kind = kind
    if name:
        row.name = name.strip()[:200]
    parsed = criteria_of(criteria)
    if parsed is not None:
        row.criteria = parsed.stored()
    if closed is not None:
        row.closed = closed
    await link_stratum(ctx, row, son_id=son_id, cult_id=cult_id, clear=clear_links)
    await ctx.session.flush()
    return row


async def link_stratum(ctx: TickContext, row: AfterlifeStratumRow, *, son_id: int | None, cult_id: int | None, clear: bool) -> None:
    if clear:
        row.son_id, row.cult_entity_id = None, None
    if son_id is not None:
        if await ctx.session.get(SonRow, son_id) is None:
            raise ValidationFailedError("No such god to rule the stratum.")
        row.son_id = son_id
    if cult_id is not None:
        row.cult_entity_id = (await entity_of(ctx, cult_id, {EntityType.CULT}, "Only a living cult can claim a stratum.")).id


async def unmake_stratum(ctx: TickContext, row: AfterlifeStratumRow) -> None:
    for soul in list(await ctx.session.scalars(select(SpiritProfileRow).where(SpiritProfileRow.stratum_id == row.id))):
        soul.stratum_id, soul.state = None, AfterlifeState.JUDGED if soul.state is AfterlifeState.IN_REALM else soul.state
    await ctx.session.delete(row)
    await ctx.session.flush()


def default_name(kind: StratumKind, realm: EntityRow) -> str:
    return f"{STRATUM_NAMES[kind]} of {realm.name}"[:200]
