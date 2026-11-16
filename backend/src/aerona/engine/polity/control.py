from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from sqlalchemy import delete, select

from aerona.catalog.law_areas import LAW_AREAS
from aerona.constants.units import PERCENT
from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.db.tables.economy import LoanRow
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.foreign_gods import ForeignGodRow
from aerona.db.tables.lifecycle import DesignatedHeirRow
from aerona.db.tables.mortal import MortalProfileRow
from aerona.db.tables.polity import (
    ClaimRow,
    HeirloomRow,
    HouseMemberRow,
    HouseProfileRow,
    LawJurisdictionRow,
    LawProfileRow,
    OathRow,
    OfficeRow,
    PolityMemberRow,
    PolityTerritoryRow,
    TreatyClauseRow,
    TreatyPartyRow,
    TreatyProfileRow,
    VassalageRow,
)
from aerona.domain.enums.bond import BondKind
from aerona.domain.enums.economy import LoanStatus
from aerona.domain.enums.entity import EntityFlag, EntityStatus, EntityType
from aerona.domain.enums.polity import (
    ClaimBasis,
    ClauseKind,
    DecisionRule,
    GovernmentKind,
    HouseTrait,
    LawKind,
    LegitimacyBasis,
    OathKind,
    OathStatus,
    OfficeKind,
    OfficePower,
    PartyRole,
    RegionalStanding,
    TreatyKind,
    TreatyStatus,
)
from aerona.domain.enums.statecraft import SubjectKind
from aerona.engine.context import TickContext
from aerona.engine.lifecycle.succession import pass_rule
from aerona.engine.polity.accords import PARTY_TYPES, Clause, accept, end_treaty, reject, sign
from aerona.engine.polity.book import Realm, RealmBook
from aerona.engine.polity.formation import found_polity, refresh_realms
from aerona.engine.polity.houses import HouseBook, extinguish, found_house, join
from aerona.engine.polity.laws import edit_law, enact, ensure_profile, jurisdiction_of, repeal, validate
from aerona.engine.polity.oath_terms import OathTerms
from aerona.engine.polity.oaths import break_oath, keep, swear
from aerona.engine.polity.offices import DEFAULT_POWERS, appoint
from aerona.engine.polity.repute import repute_of
from aerona.engine.polity.treaties import breach
from aerona.engine.primitives.queries import active_bonds, add_flag, close, connect, living_entity, remove_flag
from aerona.engine.primitives.records import retire_in

TREATY_LOCKS = ("until_epoch", "status")
LAW_LOCKS = ("repeal", "params", "enforcement", "basis")
PROFILE_NUMBERS = ("legitimacy", "stability", "war_weariness")
PROFILE_POSITIVE = ("treasury", "debt", "war_chest")
PROFILE_CHOICES = {"government": GovernmentKind, "decision_rule": DecisionRule, "standing": RegionalStanding}
PROFILE_LINKS = {"capital": "capital_entity_id", "state_religion": "state_religion_id", "ideology": "ideology_entity_id"}
PROFILE_SCALARS = ("administration", "overextension", "tier", "tier_strain")
EMBLEM_PARTS = ("emblem_field", "emblem_charge", "emblem_tincture", "emblem_motto")


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
        await set_polity_value(ctx, found, key, value)
        profile.locked = lock(profile.locked, key)
    for key in release:
        profile.locked = [item for item in profile.locked if item != key]
    await ctx.session.flush()
    return found


def counted(key: str, value: int | str | bool | None, *, cap: int | None) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0 or (cap is not None and value > cap):
        bound = f"runs from 0 to {cap}" if cap is not None else "cannot be negative"
        raise ValidationFailedError(f"{key.replace('_', ' ').capitalize()} {bound}.")
    return value


async def set_polity_value(ctx: TickContext, found: Realm, key: str, value: int | str | bool | None) -> None:
    profile = found.profile
    if key in PROFILE_NUMBERS:
        setattr(profile, key, counted(key, value, cap=PERCENT))
    elif key in (*PROFILE_POSITIVE, *PROFILE_SCALARS):
        setattr(profile, key, counted(key, value, cap=None))
    elif key in PROFILE_CHOICES:
        try:
            setattr(profile, key, PROFILE_CHOICES[key](str(value)))
        except ValueError as error:
            raise ValidationFailedError(f"{value} is not a known {key.replace('_', ' ')}.") from error
    elif key in PROFILE_LINKS:
        setattr(profile, PROFILE_LINKS[key], int(value) if isinstance(value, int) else None)
    elif key == "name" and isinstance(value, str) and value.strip():
        found.entity.name = value.strip()
    elif key == "heir":
        await set_heir(ctx, found, int(value) if isinstance(value, int) else None)
    elif key == "core":
        if not isinstance(value, int) or value not in found.members:
            raise ValidationFailedError("The heartland must be one of the realm's members.")
        profile.core_entity_id = value
    elif key == "patron":
        profile.patron_son_id = int(value) if isinstance(value, int) else None
    elif key in EMBLEM_PARTS:
        profile.emblem = {**profile.emblem, key.removeprefix("emblem_"): str(value or "")}
    else:
        raise ValidationFailedError(f"Unknown realm field: {key}.")


async def set_heir(ctx: TickContext, found: Realm, heir_id: int | None) -> None:
    if found.ruler_id is None:
        raise ValidationFailedError("The realm has no ruler to name an heir for.")
    await ctx.session.execute(delete(DesignatedHeirRow).where(DesignatedHeirRow.ruler_entity_id == found.ruler_id))
    designate = found.office(OfficeKind.HEIR_DESIGNATE)
    if heir_id is None:
        if designate is not None:
            designate.holder_entity_id = None
        return
    heir = await living_entity(ctx.session, heir_id)
    if heir is None or heir.entity_type is not EntityType.MORTAL or heir.id == found.ruler_id:
        raise NotFoundError("No such living mortal to be heir.")
    ctx.session.add(DesignatedHeirRow(ruler_entity_id=found.ruler_id, heir_entity_id=heir.id, epoch=ctx.epoch))
    if designate is None:
        designate = OfficeRow(polity_entity_id=found.entity.id, kind=OfficeKind.HEIR_DESIGNATE, since_epoch=ctx.epoch, powers=[], locked=[])
        ctx.session.add(designate)
        found.offices.append(designate)
    designate.holder_entity_id = heir.id
    designate.since_epoch = ctx.epoch


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
    law = await enact(ctx, holder, kind, params, basis=basis or LegitimacyBasis.DECREE, name=name.strip() if name and name.strip() else None)
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
        law.name = name.strip()
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


async def grant_claim(
    ctx: TickContext, claimant_id: int, polity_id: int, *, strength: int, basis: ClaimBasis, office: OfficeKind = OfficeKind.RULER
) -> ClaimRow:
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
        office=office,
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
        await require_party(ctx, party)
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


async def edit_treaty(
    ctx: TickContext,
    treaty_id: int,
    *,
    until_epoch: int | None,
    status: TreatyStatus | None,
    kind: TreatyKind | None = None,
    witness_son_id: int | None = None,
    renewals: int | None = None,
    hold: Sequence[str] = (),
    release: Sequence[str] = (),
) -> TreatyProfileRow:
    profile = await ctx.session.get(TreatyProfileRow, treaty_id)
    if profile is None:
        raise NotFoundError("No such treaty.")
    if until_epoch is not None:
        profile.until_epoch = until_epoch
        profile.locked = lock(profile.locked, "until_epoch")
    if kind is not None:
        profile.kind = kind
    if witness_son_id is not None:
        profile.witness_son_id = witness_son_id or None
    if renewals is not None:
        profile.renewals = counted("renewals", renewals, cap=None)
    if status is not None and status is not profile.status:
        if status is TreatyStatus.IN_FORCE and profile.status is TreatyStatus.PROPOSED:
            await accept(ctx, profile)
        elif status is TreatyStatus.IN_FORCE:
            profile.status = status
            profile.ended_epoch = None
        elif status is TreatyStatus.REJECTED:
            reject(ctx, profile)
        else:
            await end_treaty(ctx, profile, status, "ended by the Creator")
        profile.locked = lock(profile.locked, "status")
    profile.locked = sorted({*profile.locked, *(key for key in hold if key in TREATY_LOCKS)} - set(release))
    await ctx.session.flush()
    return profile


async def require_party(ctx: TickContext, party_id: int) -> None:
    entity = await living_entity(ctx.session, party_id)
    if entity is not None and entity.entity_type in PARTY_TYPES:
        return
    if entity is None and await ctx.session.get(ForeignGodRow, party_id) is not None:
        return
    raise NotFoundError("A party must be a living realm, community, house, cult, beast, mortal or foreign god.")


async def add_clause(
    ctx: TickContext, treaty_id: int, kind: ClauseKind, *, obligor_id: int | None, beneficiary_id: int | None, params: Mapping[str, int | str | bool]
) -> TreatyClauseRow:
    if await ctx.session.get(TreatyProfileRow, treaty_id) is None:
        raise NotFoundError("No such treaty.")
    row = TreatyClauseRow(treaty_entity_id=treaty_id, kind=kind, obligor_node_id=obligor_id, beneficiary_node_id=beneficiary_id, params=dict(params), locked=[])
    ctx.session.add(row)
    await ctx.session.flush()
    return row


async def edit_clause(
    ctx: TickContext,
    clause_id: int,
    *,
    params: Mapping[str, int | str | bool] | None,
    obligor_id: int | None,
    beneficiary_id: int | None,
    release: Sequence[str],
) -> TreatyClauseRow:
    row = await ctx.session.get(TreatyClauseRow, clause_id)
    if row is None:
        raise NotFoundError("No such clause.")
    if params is not None:
        row.params = {**row.params, **params}
        row.locked = lock(row.locked, "params")
    if obligor_id is not None:
        row.obligor_node_id = obligor_id
    if beneficiary_id is not None:
        row.beneficiary_node_id = beneficiary_id
    row.locked = release_keys(row.locked, release)
    await ctx.session.flush()
    return row


async def remove_clause(ctx: TickContext, clause_id: int) -> TreatyClauseRow:
    row = await ctx.session.get(TreatyClauseRow, clause_id)
    if row is None:
        raise NotFoundError("No such clause.")
    await ctx.session.delete(row)
    await ctx.session.flush()
    return row


async def add_party(ctx: TickContext, treaty_id: int, party_id: int, role: PartyRole) -> TreatyPartyRow:
    if await ctx.session.get(TreatyProfileRow, treaty_id) is None:
        raise NotFoundError("No such treaty.")
    await require_party(ctx, party_id)
    row = await ctx.session.get(TreatyPartyRow, (treaty_id, party_id))
    if row is None:
        row = TreatyPartyRow(treaty_entity_id=treaty_id, party_node_id=party_id, role=role)
        ctx.session.add(row)
    row.role = role
    await ctx.session.flush()
    return row


async def remove_party(ctx: TickContext, treaty_id: int, party_id: int) -> None:
    row = await ctx.session.get(TreatyPartyRow, (treaty_id, party_id))
    if row is None:
        raise NotFoundError("That party is not bound by the treaty.")
    left = await ctx.session.scalars(select(TreatyPartyRow).where(TreatyPartyRow.treaty_entity_id == treaty_id))
    if len([item for item in left if item.role is not PartyRole.GUARANTOR and item.party_node_id != party_id]) < 2 and row.role is not PartyRole.GUARANTOR:
        raise ValidationFailedError("A treaty needs at least two parties bound by it.")
    await ctx.session.delete(row)
    await ctx.session.flush()


async def create_vassalage(ctx: TickContext, vassal_id: int, overlord_id: int, *, tribute_pct: int, levy_pct: int) -> VassalageRow:
    book = await RealmBook.load(ctx.session)
    vassal, overlord = book.realms.get(vassal_id), book.realms.get(overlord_id)
    if vassal is None or overlord is None or vassal_id == overlord_id:
        raise NotFoundError("Choose two different realms.")
    if vassal.profile.core_entity_id is None or overlord.profile.core_entity_id is None:
        raise ValidationFailedError("Both realms need a heartland.")
    treaty = await sign(
        ctx,
        TreatyKind.VASSALAGE,
        [(vassal.profile.core_entity_id, PartyRole.VASSAL), (overlord.profile.core_entity_id, PartyRole.OVERLORD)],
        clauses=[
            Clause(ClauseKind.TRIBUTE, vassal.profile.core_entity_id, overlord.profile.core_entity_id, {"amount": tribute_pct}),
            Clause(ClauseKind.CALL_TO_ARMS, vassal.profile.core_entity_id, overlord.profile.core_entity_id),
        ],
    )
    row = book.vassals.get(vassal_id)
    if row is None:
        row = VassalageRow(vassal_entity_id=vassal_id, overlord_entity_id=overlord_id, since_epoch=ctx.epoch, locked=[])
        ctx.session.add(row)
    row.overlord_entity_id, row.treaty_entity_id = overlord_id, treaty.id
    row.tribute_pct = counted("tribute", tribute_pct, cap=PERCENT)
    row.levy_pct = counted("levy", levy_pct, cap=PERCENT)
    await ctx.session.flush()
    return row


@dataclass(frozen=True)
class SubjectTerms:
    kind: SubjectKind | None = None
    liberty: int | None = None
    private_war: bool | None = None
    coinage: bool | None = None
    confirm_succession: bool | None = None


async def edit_vassalage(
    ctx: TickContext,
    vassal_id: int,
    *,
    tribute_pct: int | None,
    levy_pct: int | None,
    loyalty: int | None,
    release: Sequence[str],
    terms: SubjectTerms | None = None,
) -> VassalageRow:
    row = await ctx.session.get(VassalageRow, vassal_id)
    if row is None:
        raise NotFoundError("That realm is no one's vassal.")
    for key, value in (("tribute_pct", tribute_pct), ("levy_pct", levy_pct), ("loyalty", loyalty), ("liberty", terms.liberty if terms else None)):
        if value is not None:
            setattr(row, key, counted(key, value, cap=PERCENT))
            row.locked = lock(row.locked, key)
    if terms is not None:
        for key, flag in (
            ("kind", terms.kind),
            ("private_war", terms.private_war),
            ("coinage", terms.coinage),
            ("confirm_succession", terms.confirm_succession),
        ):
            if flag is not None:
                setattr(row, key, flag)
                row.locked = lock(row.locked, key)
    row.locked = release_keys(row.locked, release)
    await ctx.session.flush()
    return row


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


def release_keys(locked: list[str], keys: Sequence[str]) -> list[str]:
    return [item for item in locked if item not in set(keys)]


async def found_realm(ctx: TickContext, core_id: int, *, name: str | None, government: GovernmentKind | None) -> Realm:
    core = await living_entity(ctx.session, core_id)
    if core is None or core.entity_type not in {EntityType.SETTLEMENT, EntityType.PEOPLE}:
        raise NotFoundError("A realm is founded on a living settlement or people.")
    book = await RealmBook.load(ctx.session)
    current = book.realm_of(core.id)
    if current is not None and current.profile.core_entity_id == core.id:
        raise ValidationFailedError(f"{core.name} already heads {current.entity.name}.")
    for bond in await active_bonds(ctx.session, [BondKind.RULES], targets=[core.id]):
        source = await living_entity(ctx.session, bond.source_node_id)
        if source is not None and source.entity_type is not EntityType.MORTAL:
            await close(ctx.session, bond, ctx.epoch, "a realm of its own by the Creator")
    await add_flag(ctx.session, core.id, EntityFlag.INDEPENDENT, ctx.epoch)
    found = await found_polity(ctx, book, core)
    if name and name.strip():
        found.entity.name = name.strip()
        found.profile.locked = lock(found.profile.locked, "name")
    if government is not None:
        found.profile.government = government
        found.profile.locked = lock(found.profile.locked, "government")
    await refresh_realms(ctx, book)
    await ctx.session.flush()
    return found


async def dissolve_realm(ctx: TickContext, polity_id: int) -> int:
    book, found = await realm(ctx, polity_id)
    freed = await split(ctx, polity_id, [member for member in found.members if member != found.profile.core_entity_id])
    await retire_in(ctx, found.entity, "dissolved by the Creator", EntityStatus.DESTROYED)
    await ctx.session.delete(found.profile)
    book.realms.pop(polity_id, None)
    await ctx.session.flush()
    return freed


async def edit_member(ctx: TickContext, polity_id: int, member_id: int, *, autonomy: int | None, release: Sequence[str]) -> PolityMemberRow:
    _, found = await realm(ctx, polity_id)
    row = found.members.get(member_id)
    if row is None:
        raise NotFoundError("That land is not part of the realm.")
    if autonomy is not None:
        row.autonomy = counted("autonomy", autonomy, cap=PERCENT)
        row.locked = lock(row.locked, "autonomy")
    row.locked = release_keys(row.locked, release)
    await ctx.session.flush()
    return row


async def edit_territory(
    ctx: TickContext, polity_id: int, region_id: int, *, control: int | None, province: str | None, release: Sequence[str]
) -> PolityTerritoryRow:
    _, found = await realm(ctx, polity_id)
    row = found.territory.get(region_id)
    if row is None:
        raise NotFoundError("The realm holds no land there.")
    if control is not None:
        row.control = counted("control", control, cap=PERCENT)
        row.locked = lock(row.locked, "control")
    if province is not None:
        row.province = province.strip() or None
        row.locked = lock(row.locked, "province")
    row.locked = release_keys(row.locked, release)
    await ctx.session.flush()
    return row


def checked_powers(powers: Sequence[str]) -> list[str]:
    known = {item.value for item in OfficePower}
    unknown = [item for item in powers if item not in known]
    if unknown:
        raise ValidationFailedError(f"No such office power: {', '.join(unknown)}.")
    return sorted(set(powers))


async def create_office(
    ctx: TickContext,
    polity_id: int,
    kind: OfficeKind,
    *,
    title: str | None,
    powers: Sequence[str] | None,
    region_id: int | None,
    target_id: int | None,
    holder_id: int | None,
) -> OfficeRow:
    _, found = await realm(ctx, polity_id)
    if kind is OfficeKind.RULER:
        raise ValidationFailedError("A realm has one throne; crown or depose its ruler instead.")
    office = OfficeRow(
        polity_entity_id=polity_id,
        kind=kind,
        region_entity_id=region_id,
        target_entity_id=target_id,
        title=title.strip() if title and title.strip() else None,
        since_epoch=ctx.epoch,
        powers=checked_powers(powers) if powers is not None else [power.value for power in DEFAULT_POWERS.get(kind, ())],
        locked=["powers"] if powers is not None else [],
    )
    ctx.session.add(office)
    found.offices.append(office)
    await ctx.session.flush()
    if holder_id is not None:
        holder = await living_entity(ctx.session, holder_id)
        if holder is None or holder.entity_type is not EntityType.MORTAL:
            raise NotFoundError("No such living mortal.")
        await appoint(ctx, found, office, holder, by_id=None, reason="appointed by the Creator")
        office.locked = lock(office.locked, "holder")
    await ctx.session.flush()
    return office


async def edit_office(
    ctx: TickContext,
    office_id: int,
    *,
    title: str | None,
    powers: Sequence[str] | None,
    holder_id: int | None,
    vacate: bool,
    region_id: int | None,
    target_id: int | None,
    release: Sequence[str],
) -> OfficeRow:
    office = await ctx.session.get(OfficeRow, office_id)
    if office is None:
        raise NotFoundError("No such office.")
    _, found = await realm(ctx, office.polity_entity_id)
    office = next(row for row in found.offices if row.id == office_id)
    if title is not None:
        office.title = title.strip() or None
    if powers is not None:
        office.powers = checked_powers(powers)
        office.locked = lock(office.locked, "powers")
    if region_id is not None:
        office.region_entity_id = region_id
        office.locked = lock(office.locked, "region")
    if target_id is not None:
        office.target_entity_id = target_id
        office.locked = lock(office.locked, "target")
    if vacate or holder_id is not None:
        if office.kind is OfficeKind.RULER:
            raise ValidationFailedError("A ruler is crowned or deposed, not appointed.")
        holder = await living_entity(ctx.session, holder_id) if holder_id is not None else None
        if holder_id is not None and (holder is None or holder.entity_type is not EntityType.MORTAL):
            raise NotFoundError("No such living mortal.")
        await appoint(ctx, found, office, holder, by_id=None, reason="appointed by the Creator")
        office.locked = lock(office.locked, "holder")
    office.locked = release_keys(office.locked, release)
    await ctx.session.flush()
    return office


async def abolish_office(ctx: TickContext, office_id: int) -> OfficeRow:
    office = await ctx.session.get(OfficeRow, office_id)
    if office is None:
        raise NotFoundError("No such office.")
    if office.kind is OfficeKind.RULER:
        raise ValidationFailedError("The throne itself cannot be abolished.")
    _, found = await realm(ctx, office.polity_entity_id)
    if office.holder_entity_id is not None:
        await appoint(ctx, found, office, None, by_id=None, reason="the office was abolished")
    found.profile.locked = lock(found.profile.locked, "offices")
    await ctx.session.delete(office)
    await ctx.session.flush()
    return office


async def edit_claim(
    ctx: TickContext,
    claim_id: int,
    *,
    strength: int | None,
    basis: ClaimBasis | None,
    pressed: bool | None,
    office: OfficeKind | None,
    backer_id: int | None,
    release: Sequence[str],
) -> ClaimRow:
    row = await ctx.session.get(ClaimRow, claim_id)
    if row is None:
        raise NotFoundError("No such claim.")
    if strength is not None:
        row.strength = counted("strength", strength, cap=PERCENT)
        row.locked = lock(row.locked, "strength")
    if basis is not None:
        row.basis = basis
    if office is not None:
        row.office = office
    if pressed is not None:
        row.pressed = pressed
        row.locked = lock(row.locked, "pressed")
    if backer_id is not None:
        row.backer_entity_id = backer_id or None
    row.locked = release_keys(row.locked, release)
    await ctx.session.flush()
    return row


async def revoke_claim(ctx: TickContext, claim_id: int) -> ClaimRow:
    row = await ctx.session.get(ClaimRow, claim_id)
    if row is None or row.ended_epoch is not None:
        raise NotFoundError("No standing claim.")
    row.ended_epoch = ctx.epoch
    await ctx.session.flush()
    return row


async def edit_repute(ctx: TickContext, mortal_id: int, *, honour: int | None, infamy: int | None, release: Sequence[str]) -> MortalProfileRow:
    mortal = await ctx.session.get(EntityRow, mortal_id)
    if mortal is None or mortal.entity_type is not EntityType.MORTAL:
        raise NotFoundError("No such mortal.")
    row = await repute_of(ctx.session, mortal_id, ctx.epoch)
    if honour is not None:
        row.honour = counted("honour", honour, cap=PERCENT)
        row.locked = lock(row.locked, "honour")
    if infamy is not None:
        row.infamy = counted("infamy", infamy, cap=PERCENT)
        row.locked = lock(row.locked, "infamy")
    row.locked = release_keys(row.locked, release)
    row.updated_epoch = ctx.epoch
    await ctx.session.flush()
    return row


async def lend(ctx: TickContext, polity_id: int, lender_id: int, *, principal: int, interest_pct: int, epochs: int) -> LoanRow:
    _, found = await realm(ctx, polity_id)
    lender = await living_entity(ctx.session, lender_id)
    if lender is None or lender.id == polity_id:
        raise NotFoundError("No such lender.")
    loan = LoanRow(
        lender_entity_id=lender.id,
        borrower_entity_id=polity_id,
        principal=counted("principal", principal, cap=None) or 1,
        interest_pct=counted("interest", interest_pct, cap=PERCENT),
        repaid=0,
        issued_epoch=ctx.epoch,
        due_epoch=ctx.epoch + max(1, epochs),
        status=LoanStatus.OPEN,
        purpose="crown debt",
    )
    ctx.session.add(loan)
    found.profile.treasury += loan.principal
    found.profile.debt += round(loan.principal * (1 + loan.interest_pct / PERCENT))
    await ctx.session.flush()
    return loan


async def edit_house(ctx: TickContext, house_id: int, values: Mapping[str, object], *, release: Sequence[str]) -> HouseProfileRow:
    profile = await ctx.session.get(HouseProfileRow, house_id)
    house = await ctx.session.get(EntityRow, house_id)
    if profile is None or house is None:
        raise NotFoundError("No such house.")
    for key, value in values.items():
        await set_house_value(ctx, profile, house, key, value)
        profile.locked = lock(profile.locked, key)
    profile.locked = release_keys(profile.locked, release)
    await ctx.session.flush()
    return profile


async def set_house_value(ctx: TickContext, profile: HouseProfileRow, house: EntityRow, key: str, value: object) -> None:
    if key == "prestige":
        profile.prestige = counted(key, value if isinstance(value, int) else None, cap=PERCENT)
    elif key == "wealth":
        profile.wealth = counted(key, value if isinstance(value, int) else None, cap=None)
    elif key == "motto":
        profile.motto = str(value).strip() or None if value is not None else None
    elif key == "name" and isinstance(value, str) and value.strip():
        house.name = value.strip()
    elif key in {"emblem_field", "emblem_charge"}:
        profile.emblem = {**profile.emblem, key.removeprefix("emblem_"): str(value or "")}
    elif key == "traits" and isinstance(value, list):
        known = {item.value for item in HouseTrait}
        if any(str(item) not in known for item in value):
            raise ValidationFailedError("No such bloodline trait.")
        profile.traits = [HouseTrait(str(item)) for item in dict.fromkeys(value)]
    elif key == "seats" and isinstance(value, list):
        profile.seats = [int(item) for item in value if isinstance(item, int)]
    elif key in {"head", "parent", "polity", "divine_son"}:
        column = {"head": "head_entity_id", "parent": "parent_house_id", "polity": "polity_entity_id", "divine_son": "divine_son_id"}[key]
        setattr(profile, column, int(value) if isinstance(value, int) else None)
    else:
        raise ValidationFailedError(f"Unknown house field: {key}.")


async def house_member(ctx: TickContext, house_id: int, mortal_id: int, *, remove: bool, by_marriage: bool) -> int:
    book = await HouseBook.load(ctx)
    if house_id not in book.houses:
        raise NotFoundError("No such house.")
    mortal = await ctx.session.get(EntityRow, mortal_id)
    if mortal is None or mortal.entity_type is not EntityType.MORTAL:
        raise NotFoundError("No such mortal.")
    if remove:
        row = await ctx.session.get(HouseMemberRow, (house_id, mortal_id))
        if row is None:
            raise NotFoundError("That mortal is not of the house.")
        await ctx.session.delete(row)
    else:
        await join(ctx, book, house_id, mortal, by_marriage=by_marriage)
    await ctx.session.flush()
    return len(book.members[house_id])


async def house_heirloom(ctx: TickContext, house_id: int, item_id: int, *, remove: bool) -> None:
    if await ctx.session.get(HouseProfileRow, house_id) is None:
        raise NotFoundError("No such house.")
    item = await living_entity(ctx.session, item_id)
    row = await ctx.session.get(HeirloomRow, item_id)
    if remove:
        if row is None or row.house_entity_id != house_id:
            raise NotFoundError("That treasure is not the house's.")
        await ctx.session.delete(row)
    elif item is None or item.entity_type is not EntityType.ITEM:
        raise NotFoundError("No such living item.")
    elif row is None:
        ctx.session.add(HeirloomRow(item_entity_id=item_id, house_entity_id=house_id, since_epoch=ctx.epoch))
    else:
        row.house_entity_id, row.since_epoch = house_id, ctx.epoch
    await ctx.session.flush()


async def edit_oath(
    ctx: TickContext,
    oath_id: int,
    *,
    deadline_epoch: int | None,
    note: str | None,
    recipient_id: int | None,
    witness_son_id: int | None,
    clear_deadline: bool,
    terms: OathTerms | None = None,
) -> OathRow:
    oath = await ctx.session.get(OathRow, oath_id)
    if oath is None:
        raise NotFoundError("No such oath.")
    if deadline_epoch is not None:
        oath.deadline_epoch = deadline_epoch
    if clear_deadline:
        oath.deadline_epoch = None
    if note is not None:
        oath.note = note.strip() or None
    if recipient_id is not None:
        oath.recipient_node_id = recipient_id or None
    if witness_son_id is not None:
        oath.witness_son_id = witness_son_id or None
    if terms is not None:
        if terms.witness_node_id is not None:
            oath.witness_node_id = terms.witness_node_id or None
        if terms.penalty is not None:
            oath.penalty = terms.penalty
        if terms.clear_penalty:
            oath.penalty = None
    await ctx.session.flush()
    return oath


async def release_oath(ctx: TickContext, oath_id: int) -> OathRow:
    oath = await ctx.session.get(OathRow, oath_id)
    if oath is None or oath.status is not OathStatus.SWORN:
        raise NotFoundError("No sworn oath.")
    await keep(ctx, oath, fulfilled=False)
    await ctx.session.flush()
    return oath
