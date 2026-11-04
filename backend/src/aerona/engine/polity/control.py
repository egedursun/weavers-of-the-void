from collections.abc import Mapping, Sequence

from sqlalchemy import select

from aerona.constants.units import PERCENT
from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.polity import ClaimRow, HouseMemberRow, LawJurisdictionRow, LawProfileRow, OathRow, OfficeRow, TreatyProfileRow
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.entity import EntityFlag, EntityStatus, EntityType
from aerona.domain.enums.polity import (
    LAW_AREAS,
    ClaimBasis,
    ClauseKind,
    DecisionRule,
    GovernmentKind,
    LawKind,
    LegitimacyBasis,
    OathKind,
    OfficeKind,
    PartyRole,
    RegionalStanding,
    TreatyKind,
    TreatyStatus,
)
from aerona.engine.context import TickContext
from aerona.engine.lifecycle.succession import pass_rule
from aerona.engine.polity.book import Realm, RealmBook
from aerona.engine.polity.formation import refresh_realms
from aerona.engine.polity.houses import HouseBook, extinguish, found_house, join
from aerona.engine.polity.laws import edit_law, enact, ensure_profile, jurisdiction_of, repeal, validate
from aerona.engine.polity.oaths import break_oath, swear
from aerona.engine.polity.offices import appoint
from aerona.engine.polity.treaties import Clause, breach, end_treaty, sign
from aerona.engine.primitives.queries import active_bonds, add_flag, close, connect, living_entity, remove_flag

LAW_LOCKS = ("repeal", "params", "enforcement", "basis")
PROFILE_NUMBERS = ("legitimacy", "stability", "war_weariness")
PROFILE_POSITIVE = ("treasury", "debt", "war_chest")
PROFILE_CHOICES = {"government": GovernmentKind, "decision_rule": DecisionRule, "standing": RegionalStanding}
PROFILE_LINKS = {"capital": "capital_entity_id", "state_religion": "state_religion_id", "ideology": "ideology_entity_id"}


async def realm(ctx: TickContext, polity_id: int) -> tuple[RealmBook, Realm]:
    book = await RealmBook.load(ctx.session)
    found = book.realms.get(polity_id)
    if found is None:
        raise NotFoundError("No such realm.")
    return book, found


def lock(locked: list[str], key: str) -> list[str]:
    return locked if key in locked else [*locked, key]


async def edit_polity(ctx: TickContext, polity_id: int, values: Mapping[str, int | str | bool | None], *, release: list[str]) -> Realm:
    _, found = await realm(ctx, polity_id)
    profile = found.profile
    for key, value in values.items():
        if key in PROFILE_NUMBERS:
            if not isinstance(value, int) or not 0 <= value <= PERCENT:
                raise ValidationFailedError(f"{key.replace('_', ' ').capitalize()} runs from 0 to {PERCENT}.")
            setattr(profile, key, value)
        elif key in PROFILE_POSITIVE:
            if not isinstance(value, int) or value < 0:
                raise ValidationFailedError(f"{key.replace('_', ' ').capitalize()} cannot be negative.")
            setattr(profile, key, value)
        elif key in PROFILE_CHOICES:
            try:
                setattr(profile, key, PROFILE_CHOICES[key](str(value)))
            except ValueError as error:
                raise ValidationFailedError(f"{value} is not a known {key.replace('_', ' ')}.") from error
        elif key in PROFILE_LINKS:
            setattr(profile, PROFILE_LINKS[key], int(value) if isinstance(value, int) else None)
        elif key == "name" and isinstance(value, str) and value.strip():
            found.entity.name = value.strip()[:120]
        else:
            raise ValidationFailedError(f"Unknown realm field: {key}.")
        profile.locked = lock(profile.locked, key)
    for key in release:
        profile.locked = [item for item in profile.locked if item != key]
    await ctx.session.flush()
    return found


async def appoint_office(ctx: TickContext, polity_id: int, kind: OfficeKind, mortal_id: int | None, *, region_id: int | None) -> OfficeRow:
    _, found = await realm(ctx, polity_id)
    if kind is OfficeKind.RULER:
        raise ValidationFailedError("A ruler is crowned or deposed, not appointed.")
    holder = await living_entity(ctx.session, mortal_id) if mortal_id is not None else None
    if mortal_id is not None and (holder is None or holder.entity_type is not EntityType.MORTAL):
        raise NotFoundError("No such living mortal.")
    office = next((row for row in found.offices if row.kind is kind and row.region_entity_id == region_id), None)
    if office is None:
        office = OfficeRow(polity_entity_id=polity_id, kind=kind, region_entity_id=region_id, since_epoch=ctx.epoch, powers=[])
        ctx.session.add(office)
        found.offices.append(office)
        await ctx.session.flush()
    await appoint(ctx, found, office, holder, by_id=None, reason="appointed by the Creator")
    found.profile.locked = lock(found.profile.locked, "offices") if holder is not None else found.profile.locked
    await ctx.session.flush()
    return office


async def depose(ctx: TickContext, polity_id: int) -> EntityRow | None:
    _, found = await realm(ctx, polity_id)
    ruler = await living_entity(ctx.session, found.ruler_id) if found.ruler_id is not None else None
    if ruler is None:
        raise ValidationFailedError("The realm has no ruler to depose.")
    heir = await pass_rule(ctx, ruler)
    await ctx.session.flush()
    return heir


async def split(ctx: TickContext, polity_id: int, member_ids: Sequence[int]) -> int:
    book, found = await realm(ctx, polity_id)
    moved = 0
    for member_id in member_ids:
        if member_id not in found.members or member_id == found.profile.core_entity_id:
            continue
        for bond in await active_bonds(ctx.session, [BondKind.RULES], targets=[member_id]):
            await close(ctx.session, bond, ctx.epoch, "set free by the Creator")
        await add_flag(ctx.session, member_id, EntityFlag.INDEPENDENT, ctx.epoch)
        moved += 1
    await refresh_realms(ctx, book)
    return moved


async def merge(ctx: TickContext, polity_id: int, into_id: int) -> None:
    book, found = await realm(ctx, polity_id)
    target = book.realms.get(into_id)
    if target is None or target.entity.id == found.entity.id:
        raise NotFoundError("No such realm to merge into.")
    core, lord = found.profile.core_entity_id, target.profile.core_entity_id
    if core is None or lord is None:
        raise ValidationFailedError("Both realms need a heartland.")
    await remove_flag(ctx.session, core, EntityFlag.INDEPENDENT)
    await connect(ctx.session, lord, core, BondKind.RULES, ctx.epoch, description="united by the Creator")
    await refresh_realms(ctx, book)


async def grant_independence(ctx: TickContext, polity_id: int) -> None:
    book, found = await realm(ctx, polity_id)
    row = book.vassals.get(polity_id)
    if row is not None:
        if row.treaty_entity_id is not None:
            profile = await ctx.session.get(TreatyProfileRow, row.treaty_entity_id)
            if profile is not None and profile.status is TreatyStatus.IN_FORCE:
                await end_treaty(ctx, profile, TreatyStatus.FULFILLED, "independence granted")
        await ctx.session.delete(row)
    core = found.profile.core_entity_id
    if core is not None:
        for kind in (BondKind.PAYS_TRIBUTE,):
            for bond in await active_bonds(ctx.session, [kind], sources=[core]):
                await close(ctx.session, bond, ctx.epoch, "independence granted")
        for bond in await active_bonds(ctx.session, [BondKind.RULES], targets=[core]):
            source = await living_entity(ctx.session, bond.source_node_id)
            if source is not None and source.entity_type is not EntityType.MORTAL:
                await close(ctx.session, bond, ctx.epoch, "independence granted")
        await add_flag(ctx.session, core, EntityFlag.INDEPENDENT, ctx.epoch)
    await ctx.session.flush()


async def enact_law(
    ctx: TickContext,
    holder_id: int,
    kind: LawKind,
    params: Mapping[str, int | str | bool],
    *,
    name: str | None = None,
    enforcement: int | None = None,
    basis: LegitimacyBasis | None = None,
    hold: Sequence[str] = (),
) -> EntityRow:
    holder = await living_entity(ctx.session, holder_id)
    if holder is None or holder.entity_type not in {EntityType.POLITY, EntityType.SETTLEMENT, EntityType.PEOPLE, EntityType.CULT}:
        raise NotFoundError("No realm, settlement or cult to lay down the law.")
    law = await enact(ctx, holder, kind, params, basis=basis or LegitimacyBasis.DECREE, name=name.strip()[:120] if name and name.strip() else None)
    profile = await ctx.session.get(LawProfileRow, law.id)
    if profile is not None:
        if enforcement is not None:
            profile.enforcement = enforcement
        profile.locked = sorted({*profile.locked, *(key for key in hold if key in LAW_LOCKS)})
    await ctx.session.flush()
    return law


async def protect_law(ctx: TickContext, law_id: int, *, hold: Sequence[str], release: Sequence[str]) -> LawProfileRow:
    law = await ctx.session.get(EntityRow, law_id)
    if law is None or law.entity_type is not EntityType.LAW:
        raise NotFoundError("No such law.")
    unknown = [key for key in [*hold, *release] if key not in LAW_LOCKS]
    if unknown:
        raise ValidationFailedError(f"A law can only be held on {', '.join(LAW_LOCKS)}.")
    profile = await ensure_profile(ctx.session, law, ctx.epoch)
    profile.locked = sorted({*profile.locked, *hold} - set(release))
    await ctx.session.flush()
    return profile


async def repeal_law(ctx: TickContext, law_id: int) -> EntityRow:
    law = await ctx.session.get(EntityRow, law_id)
    if law is None or law.entity_type is not EntityType.LAW or law.status is not EntityStatus.CANON:
        raise NotFoundError("No such law.")
    await repeal(ctx, law, "repealed by the Creator")
    return law


async def change_law(
    ctx: TickContext,
    law_id: int,
    params: Mapping[str, int | str | bool],
    *,
    enforcement: int | None,
    basis: LegitimacyBasis | None = None,
    name: str | None = None,
    holder_ids: Sequence[int] | None = None,
    release: Sequence[str] = (),
    kind: LawKind | None = None,
    conflict: int | None = None,
) -> LawProfileRow:
    if kind is not None:
        current = await ctx.session.get(LawProfileRow, law_id)
        if current is not None and current.kind is not kind:
            current.kind = kind
            current.area = LAW_AREAS[kind]
            current.params = validate(kind, params)
            params = {}
    profile = await edit_law(ctx, law_id, params, enforcement=enforcement)
    if conflict is not None:
        if not 0 <= conflict <= PERCENT:
            raise ValidationFailedError(f"Conflict runs from 0 to {PERCENT}.")
        profile.conflict = conflict
    if params:
        profile.locked = lock(profile.locked, "params")
    if basis is not None:
        profile.legitimacy_basis = basis
        profile.locked = lock(profile.locked, "basis")
    law = await ctx.session.get(EntityRow, law_id)
    if law is not None and name is not None and name.strip():
        law.name = name.strip()[:120]
    if holder_ids is not None:
        await rehome_law(ctx, law_id, holder_ids)
    profile.locked = [key for key in profile.locked if key not in set(release)]
    await ctx.session.flush()
    return profile


async def rehome_law(ctx: TickContext, law_id: int, holder_ids: Sequence[int]) -> None:
    if not holder_ids:
        raise ValidationFailedError("A law must hold somewhere.")
    holders = []
    for holder_id in holder_ids:
        holder = await living_entity(ctx.session, holder_id)
        if holder is None or holder.entity_type not in {EntityType.POLITY, EntityType.SETTLEMENT, EntityType.PEOPLE, EntityType.CULT}:
            raise NotFoundError("Laws hold over realms, settlements, peoples and cults.")
        holders.append(holder)
    for row in await ctx.session.scalars(select(LawJurisdictionRow).where(LawJurisdictionRow.law_entity_id == law_id)):
        await ctx.session.delete(row)
    await ctx.session.flush()
    for holder in holders:
        ctx.session.add(LawJurisdictionRow(law_entity_id=law_id, node_entity_id=holder.id, jurisdiction=jurisdiction_of(holder)))


async def found_house_by_hand(ctx: TickContext, mortal_id: int) -> EntityRow:
    mortal = await living_entity(ctx.session, mortal_id)
    if mortal is None or mortal.entity_type is not EntityType.MORTAL:
        raise NotFoundError("No such living mortal.")
    book = await HouseBook.load(ctx)
    realms = await RealmBook.load(ctx.session)
    return await found_house(ctx, book, mortal, polity_id=realms.member_of.get(mortal.location_id or -1))


async def merge_houses(ctx: TickContext, house_id: int, into_id: int) -> int:
    book = await HouseBook.load(ctx)
    if house_id not in book.houses or into_id not in book.houses or house_id == into_id:
        raise NotFoundError("No such houses to merge.")
    moved = 0
    for member_id in sorted(book.members[house_id]):
        mortal = await living_entity(ctx.session, member_id)
        if mortal is not None:
            await join(ctx, book, into_id, mortal, by_marriage=False)
            moved += 1
    await extinguish(ctx, book, house_id, f"it was joined to {book.houses[into_id].name}")
    return moved


async def end_house(ctx: TickContext, house_id: int) -> None:
    book = await HouseBook.load(ctx)
    if house_id not in book.houses:
        raise NotFoundError("No such house.")
    for row in await ctx.session.scalars(select(HouseMemberRow).where(HouseMemberRow.house_entity_id == house_id)):
        await ctx.session.delete(row)
    await extinguish(ctx, book, house_id, "the Creator struck its name")


async def grant_claim(ctx: TickContext, claimant_id: int, polity_id: int, *, strength: int, basis: ClaimBasis) -> ClaimRow:
    claimant = await living_entity(ctx.session, claimant_id)
    if claimant is None or claimant.entity_type is not EntityType.MORTAL:
        raise NotFoundError("No such living mortal.")
    await realm(ctx, polity_id)
    if not 0 <= strength <= PERCENT:
        raise ValidationFailedError(f"A claim's strength runs from 0 to {PERCENT}.")
    house = await ctx.session.scalar(select(HouseMemberRow.house_entity_id).where(HouseMemberRow.mortal_entity_id == claimant_id).limit(1))
    row = ClaimRow(
        claimant_entity_id=claimant_id,
        house_entity_id=house,
        polity_entity_id=polity_id,
        office=OfficeKind.RULER,
        strength=strength,
        basis=basis,
        pressed=False,
        since_epoch=ctx.epoch,
    )
    ctx.session.add(row)
    await ctx.session.flush()
    return row


async def sign_treaty(
    ctx: TickContext,
    kind: TreatyKind,
    parties: Sequence[tuple[int, PartyRole]],
    clauses: Sequence[tuple[ClauseKind, int | None, int | None, dict[str, int | str | bool]]],
    *,
    epochs: int | None,
) -> EntityRow:
    if len(parties) < 2:
        raise ValidationFailedError("A treaty needs at least two parties.")
    for party, _ in parties:
        if await living_entity(ctx.session, party) is None:
            raise NotFoundError("Every party must be alive.")
    return await sign(
        ctx,
        kind,
        parties,
        clauses=[Clause(item, obligor, beneficiary, params) for item, obligor, beneficiary, params in clauses],
        until=ctx.epoch + epochs if epochs else None,
    )


async def break_treaty(ctx: TickContext, treaty_id: int, breaker_id: int) -> None:
    profile = await ctx.session.get(TreatyProfileRow, treaty_id)
    if profile is None or profile.status is not TreatyStatus.IN_FORCE:
        raise NotFoundError("No treaty in force.")
    await breach(ctx, profile, breaker_id, clause=None, reason="the Creator bade it")


async def edit_treaty(ctx: TickContext, treaty_id: int, *, until_epoch: int | None, status: TreatyStatus | None) -> TreatyProfileRow:
    profile = await ctx.session.get(TreatyProfileRow, treaty_id)
    if profile is None:
        raise NotFoundError("No such treaty.")
    if until_epoch is not None:
        profile.until_epoch = until_epoch
        profile.locked = lock(profile.locked, "until_epoch")
    if status is not None and status is not profile.status:
        if status is TreatyStatus.IN_FORCE:
            profile.status = status
            profile.ended_epoch = None
        else:
            await end_treaty(ctx, profile, status, "ended by the Creator")
    await ctx.session.flush()
    return profile


async def swear_oath(ctx: TickContext, swearer_id: int, kind: OathKind, recipient_id: int | None) -> OathRow:
    swearer = await living_entity(ctx.session, swearer_id)
    if swearer is None:
        raise NotFoundError("No such living swearer.")
    return await swear(ctx, swearer, kind, recipient_id=recipient_id, note_text="sworn before the Creator")


async def break_oath_by_hand(ctx: TickContext, oath_id: int) -> OathRow:
    oath = await ctx.session.get(OathRow, oath_id)
    if oath is None:
        raise NotFoundError("No such oath.")
    await break_oath(ctx, oath, "the Creator released no one")
    return oath
