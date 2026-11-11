from sqlalchemy import select

from aerona.core.errors import ConflictError, ValidationFailedError
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.justice import CrimeCaseRow
from aerona.db.tables.law_depth import (
    APPEAL_FIELDS,
    CELL_FIELDS,
    DEFECTION_FIELDS,
    JURISDICTION_FIELDS,
    KILLING_FIELDS,
    OUTLAW_FIELDS,
    PRECEDENT_FIELDS,
    PRISON_FIELDS,
    PRISONER_FIELDS,
    REGISTRY_FIELDS,
    SYSTEM_FIELDS,
    AppealRow,
    DefectionRow,
    JurisdictionRow,
    KillingRow,
    LegalSystemRow,
    MoleHuntRow,
    OutlawRow,
    PardonRow,
    PrecedentRow,
    PrisonerRow,
    PrisonRow,
    RegistryRow,
    SpyCellRow,
)
from aerona.db.tables.military import SpyNetworkRow
from aerona.db.tables.polity import OfficeRow
from aerona.db.tables.structures import StructureProfileRow
from aerona.domain.enums.entity import EntityType
from aerona.domain.enums.justice import CaseStage, Verdict
from aerona.domain.enums.law_depth import CourtLevel, JurisdictionClaim, KillMethod, LegalSystem, RegistryKind
from aerona.domain.enums.mortal import CrimeKind
from aerona.domain.enums.polity import OfficeKind
from aerona.domain.enums.structure import StructureKind
from aerona.engine.context import TickContext
from aerona.engine.divine.control import apply
from aerona.engine.gatherings.control import Values, allowed, entity, found
from aerona.engine.law.appeals import AppealTally, hear_appeal
from aerona.engine.law.outlawry import declare_outlaw
from aerona.engine.law.pardons import declare_amnesty, grant_pardon
from aerona.engine.law.prisons import ensure_prison
from aerona.engine.law.registries import register
from aerona.engine.military.mole_hunts import MoleTally, hunt
from aerona.engine.military.spy_depth import defect
from aerona.engine.primitives.queries import living_entity

HOLDERS = frozenset({EntityType.POLITY, EntityType.CULT, EntityType.SETTLEMENT})
CLAIMANTS = frozenset({EntityType.POLITY, EntityType.CULT, EntityType.FACTION})


async def of_type(ctx: TickContext, entity_id: int, kinds: frozenset[EntityType], label: str) -> EntityRow:
    row = await entity(ctx, entity_id, label)
    if row.entity_type not in kinds:
        raise ValidationFailedError(f"{row.name} is not {label}.")
    return row


async def mortal(ctx: TickContext, mortal_id: int) -> EntityRow:
    row = await living_entity(ctx.session, mortal_id)
    if row is None or row.entity_type is not EntityType.MORTAL:
        raise ValidationFailedError("That is not a living mortal.")
    return row


async def saved[Row](ctx: TickContext, row: Row) -> Row:
    ctx.session.add(row)
    await ctx.session.flush()
    return row


async def set_system(ctx: TickContext, holder_id: int, system: LegalSystem) -> LegalSystemRow:
    await of_type(ctx, holder_id, HOLDERS, "a realm, cult or settlement")
    row = await ctx.session.get(LegalSystemRow, holder_id)
    if row is None:
        row = await saved(ctx, LegalSystemRow(holder_entity_id=holder_id, since_epoch=ctx.epoch, locked=[]))
    apply(row, {"system": system}, [])
    row.since_epoch = ctx.epoch
    await ctx.session.flush()
    return row


async def edit_system(ctx: TickContext, holder_id: int, values: Values, release: list[str]) -> LegalSystemRow:
    row = apply(await found(ctx, LegalSystemRow, holder_id, "legal system"), allowed(values, SYSTEM_FIELDS, "legal system"), release)
    await ctx.session.flush()
    return row


async def delete_system(ctx: TickContext, holder_id: int) -> None:
    await ctx.session.delete(await found(ctx, LegalSystemRow, holder_id, "legal system"))
    await ctx.session.flush()


async def add_precedent(ctx: TickContext, holder_id: int, crime: CrimeKind, *, verdict: Verdict, court: CourtLevel, authority: int) -> PrecedentRow:
    await of_type(ctx, holder_id, HOLDERS, "a realm, cult or settlement")
    row = PrecedentRow(holder_entity_id=holder_id, crime=crime, verdict=verdict, court=court, authority=0, overturned=False, epoch=ctx.epoch, locked=[])
    apply(row, {"authority": authority}, [])
    return await saved(ctx, row)


async def edit_precedent(ctx: TickContext, precedent_id: int, values: Values, release: list[str]) -> PrecedentRow:
    row = apply(await found(ctx, PrecedentRow, precedent_id, "precedent"), allowed(values, PRECEDENT_FIELDS, "precedent"), release)
    await ctx.session.flush()
    return row


async def delete_precedent(ctx: TickContext, precedent_id: int) -> None:
    await ctx.session.delete(await found(ctx, PrecedentRow, precedent_id, "precedent"))
    await ctx.session.flush()


async def closed_case(ctx: TickContext, case_id: int) -> CrimeCaseRow:
    case = await found(ctx, CrimeCaseRow, case_id, "case")
    if case.verdict is not Verdict.GUILTY:
        raise ConflictError("Only a conviction can be appealed.")
    return case


async def file_appeal(ctx: TickContext, case_id: int, to_court: CourtLevel, fee: int) -> AppealRow:
    case = await closed_case(ctx, case_id)
    if await ctx.session.get(AppealRow, case_id) is not None:
        raise ConflictError("That conviction is already under appeal.")
    return await saved(ctx, AppealRow(case_id=case_id, from_court=case.court, to_court=to_court, fee=fee, filed_epoch=ctx.epoch, reversed=False, locked=[]))


async def edit_appeal(ctx: TickContext, case_id: int, values: Values, release: list[str]) -> AppealRow:
    row = apply(await found(ctx, AppealRow, case_id, "appeal"), allowed(values, APPEAL_FIELDS, "appeal"), release)
    await ctx.session.flush()
    return row


async def hear_now(ctx: TickContext, case_id: int) -> AppealRow:
    row = await found(ctx, AppealRow, case_id, "appeal")
    await hear_appeal(ctx, row, AppealTally())
    await ctx.session.flush()
    return row


async def delete_appeal(ctx: TickContext, case_id: int) -> None:
    await ctx.session.delete(await found(ctx, AppealRow, case_id, "appeal"))
    await ctx.session.flush()


async def answer_oracle(ctx: TickContext, case_id: int, verdict: Verdict | None) -> CrimeCaseRow:
    case = await found(ctx, CrimeCaseRow, case_id, "case")
    if case.stage is not CaseStage.TRIAL:
        raise ConflictError("Only a case awaiting trial can be answered.")
    case.oracle_answer = verdict
    await ctx.session.flush()
    return case


async def add_registry(
    ctx: TickContext, holder_id: int, kind: RegistryKind, *, owner_id: int | None, counterparty_id: int | None, subject_id: int | None, amount: int
) -> RegistryRow:
    await of_type(ctx, holder_id, HOLDERS, "a realm, cult or settlement")
    for node_id, label in ((owner_id, "owner"), (counterparty_id, "counterparty"), (subject_id, "subject")):
        if node_id is not None:
            await entity(ctx, node_id, label)
    row = await register(ctx, holder_id, kind, owner_id=owner_id, counterparty_id=counterparty_id, subject_id=subject_id, amount=0)
    apply(row, {"amount": amount}, [])
    await ctx.session.flush()
    return row


async def edit_registry(ctx: TickContext, registry_id: int, values: Values, release: list[str]) -> RegistryRow:
    row = apply(await found(ctx, RegistryRow, registry_id, "registry entry"), allowed(values, REGISTRY_FIELDS, "registry entry"), release)
    await ctx.session.flush()
    return row


async def delete_registry(ctx: TickContext, registry_id: int) -> None:
    await ctx.session.delete(await found(ctx, RegistryRow, registry_id, "registry entry"))
    await ctx.session.flush()


async def set_claim(ctx: TickContext, holder_id: int, claimant_id: int, claim: JurisdictionClaim, strength: int) -> JurisdictionRow:
    await of_type(ctx, holder_id, frozenset({EntityType.POLITY}), "a realm")
    await of_type(ctx, claimant_id, CLAIMANTS, "a realm, cult or faction")
    if holder_id == claimant_id:
        raise ValidationFailedError("A realm cannot claim courts against itself.")
    key = (holder_id, claimant_id, claim)
    row = await ctx.session.get(JurisdictionRow, key)
    if row is None:
        row = await saved(
            ctx, JurisdictionRow(holder_entity_id=holder_id, claimant_entity_id=claimant_id, claim=claim, strength=0, since_epoch=ctx.epoch, locked=[])
        )
    apply(row, {"strength": strength}, [])
    await ctx.session.flush()
    return row


async def edit_claim(ctx: TickContext, key: tuple[int, int, JurisdictionClaim], values: Values, release: list[str]) -> JurisdictionRow:
    row = apply(await found(ctx, JurisdictionRow, key, "jurisdiction claim"), allowed(values, JURISDICTION_FIELDS, "jurisdiction claim"), release)
    await ctx.session.flush()
    return row


async def delete_claim(ctx: TickContext, key: tuple[int, int, JurisdictionClaim]) -> None:
    await ctx.session.delete(await found(ctx, JurisdictionRow, key, "jurisdiction claim"))
    await ctx.session.flush()


async def pardon(ctx: TickContext, granter_id: int, mortal_id: int) -> PardonRow:
    granter, pardoned = await mortal(ctx, granter_id), await mortal(ctx, mortal_id)
    jailed = await ctx.session.get(PrisonerRow, pardoned.id)
    outlaw = await ctx.session.get(OutlawRow, pardoned.id)
    if jailed is None and outlaw is None:
        raise ConflictError(f"{pardoned.name} is neither in prison nor outlawed.")
    polity = outlaw.polity_entity_id if outlaw is not None else None
    return await grant_pardon(ctx, granter, pardoned, polity_id=polity, case_id=jailed.case_id if jailed is not None else None)


async def amnesty(ctx: TickContext, polity_id: int) -> int:
    await of_type(ctx, polity_id, frozenset({EntityType.POLITY}), "a realm")
    holder = await ctx.session.scalar(
        select(OfficeRow.holder_entity_id)
        .where(OfficeRow.polity_entity_id == polity_id, OfficeRow.kind == OfficeKind.RULER, OfficeRow.holder_entity_id.is_not(None))
        .limit(1)
    )
    ruler = await living_entity(ctx.session, holder) if holder is not None else None
    if ruler is None:
        raise ConflictError("The realm has no living ruler to declare it.")
    return await declare_amnesty(ctx, polity_id, ruler)


async def delete_pardon(ctx: TickContext, pardon_id: int) -> None:
    await ctx.session.delete(await found(ctx, PardonRow, pardon_id, "pardon"))
    await ctx.session.flush()


async def declare(ctx: TickContext, mortal_id: int, polity_id: int | None, bounty: int) -> OutlawRow:
    target = await mortal(ctx, mortal_id)
    if polity_id is not None:
        await of_type(ctx, polity_id, frozenset({EntityType.POLITY}), "a realm")
    row = await ctx.session.get(OutlawRow, target.id) or await declare_outlaw(ctx, target, polity_id, bounty=bounty)
    if row is None:
        raise ConflictError(f"{target.name} cannot be outlawed now.")
    apply(row, {"bounty": bounty}, [])
    await ctx.session.flush()
    return row


async def edit_outlaw(ctx: TickContext, mortal_id: int, values: Values, release: list[str]) -> OutlawRow:
    row = apply(await found(ctx, OutlawRow, mortal_id, "outlaw"), allowed(values, OUTLAW_FIELDS, "outlaw"), release)
    await ctx.session.flush()
    return row


async def lift_outlawry(ctx: TickContext, mortal_id: int) -> None:
    await ctx.session.delete(await found(ctx, OutlawRow, mortal_id, "outlaw"))
    await ctx.session.flush()


async def prison_structure(ctx: TickContext, structure_id: int) -> StructureProfileRow:
    structure = await found(ctx, StructureProfileRow, structure_id, "structure")
    if structure.kind is not StructureKind.PRISON:
        raise ValidationFailedError("That structure is not a prison.")
    return structure


async def set_prison(ctx: TickContext, structure_id: int, values: Values) -> PrisonRow:
    await prison_structure(ctx, structure_id)
    row = apply(await ensure_prison(ctx, structure_id), allowed(values, PRISON_FIELDS, "prison"), [])
    await ctx.session.flush()
    return row


async def edit_prison(ctx: TickContext, structure_id: int, values: Values, release: list[str]) -> PrisonRow:
    row = apply(await found(ctx, PrisonRow, structure_id, "prison"), allowed(values, PRISON_FIELDS, "prison"), release)
    await ctx.session.flush()
    return row


async def delete_prison(ctx: TickContext, structure_id: int) -> None:
    await ctx.session.delete(await found(ctx, PrisonRow, structure_id, "prison"))
    await ctx.session.flush()


async def jail(ctx: TickContext, mortal_id: int, prison_id: int, term: int) -> PrisonerRow:
    target = await mortal(ctx, mortal_id)
    await prison_structure(ctx, prison_id)
    await ensure_prison(ctx, prison_id)
    row = await ctx.session.get(PrisonerRow, target.id)
    if row is None:
        row = await saved(ctx, PrisonerRow(mortal_entity_id=target.id, prison_entity_id=prison_id, term=0, gang_rank=0, since_epoch=ctx.epoch, locked=[]))
    row.prison_entity_id = prison_id
    apply(row, {"term": term}, [])
    await ctx.session.flush()
    return row


async def edit_prisoner(ctx: TickContext, mortal_id: int, values: Values, release: list[str]) -> PrisonerRow:
    row = apply(await found(ctx, PrisonerRow, mortal_id, "prisoner"), allowed(values, PRISONER_FIELDS, "prisoner"), release)
    await ctx.session.flush()
    return row


async def free(ctx: TickContext, mortal_id: int) -> None:
    await ctx.session.delete(await found(ctx, PrisonerRow, mortal_id, "prisoner"))
    await ctx.session.flush()


async def add_cell(ctx: TickContext, network_id: int, handler_id: int | None, safe_house_id: int | None, dead_drops: int) -> SpyCellRow:
    await found(ctx, SpyNetworkRow, network_id, "spy network")
    for node_id, label in ((handler_id, "handler"), (safe_house_id, "safe house")):
        if node_id is not None:
            await entity(ctx, node_id, label)
    row = SpyCellRow(network_id=network_id, handler_entity_id=handler_id, safe_house_entity_id=safe_house_id, dead_drops=0, locked=[])
    apply(row, {"dead_drops": dead_drops}, [])
    return await saved(ctx, row)


async def edit_cell(ctx: TickContext, cell_id: int, values: Values, release: list[str]) -> SpyCellRow:
    row = apply(await found(ctx, SpyCellRow, cell_id, "spy cell"), allowed(values, CELL_FIELDS, "spy cell"), release)
    await ctx.session.flush()
    return row


async def delete_cell(ctx: TickContext, cell_id: int) -> None:
    await ctx.session.delete(await found(ctx, SpyCellRow, cell_id, "spy cell"))
    await ctx.session.flush()


async def order_hunt(ctx: TickContext, polity_id: int) -> MoleTally:
    await of_type(ctx, polity_id, frozenset({EntityType.POLITY}), "a realm")
    holder = await ctx.session.scalar(
        select(OfficeRow.holder_entity_id)
        .where(OfficeRow.polity_entity_id == polity_id, OfficeRow.kind == OfficeKind.SPYMASTER, OfficeRow.holder_entity_id.is_not(None))
        .limit(1)
    )
    spymaster = await living_entity(ctx.session, holder) if holder is not None else None
    if spymaster is None:
        raise ConflictError("The realm has no living spymaster to hunt.")
    tally = MoleTally()
    await hunt(ctx, polity_id, spymaster, tally, forced=True)
    await ctx.session.flush()
    return tally


async def delete_hunt(ctx: TickContext, hunt_id: int) -> None:
    await ctx.session.delete(await found(ctx, MoleHuntRow, hunt_id, "mole hunt"))
    await ctx.session.flush()


async def defect_now(ctx: TickContext, mortal_id: int, from_id: int | None, to_id: int, protected: bool) -> DefectionRow:
    target = await mortal(ctx, mortal_id)
    await of_type(ctx, to_id, CLAIMANTS, "a realm, cult or faction")
    row = await defect(ctx, target, from_id, to_id, protected=protected)
    if row is None:
        raise ConflictError(f"{target.name} cannot defect now.")
    return row


async def edit_defection(ctx: TickContext, defection_id: int, values: Values, release: list[str]) -> DefectionRow:
    row = apply(await found(ctx, DefectionRow, defection_id, "defection"), allowed(values, DEFECTION_FIELDS, "defection"), release)
    await ctx.session.flush()
    return row


async def delete_defection(ctx: TickContext, defection_id: int) -> None:
    await ctx.session.delete(await found(ctx, DefectionRow, defection_id, "defection"))
    await ctx.session.flush()


async def add_killing(ctx: TickContext, victim_id: int, killer_id: int | None, method: KillMethod, recognised: bool) -> KillingRow:
    await entity(ctx, victim_id, "victim")
    if killer_id is not None:
        await entity(ctx, killer_id, "killer")
    row = KillingRow(victim_entity_id=victim_id, killer_entity_id=killer_id, method=method, recognised=False, epoch=ctx.epoch, locked=[])
    apply(row, {"recognised": recognised}, [])
    return await saved(ctx, row)


async def edit_killing(ctx: TickContext, killing_id: int, values: Values, release: list[str]) -> KillingRow:
    row = apply(await found(ctx, KillingRow, killing_id, "killing"), allowed(values, KILLING_FIELDS, "killing"), release)
    await ctx.session.flush()
    return row


async def delete_killing(ctx: TickContext, killing_id: int) -> None:
    await ctx.session.delete(await found(ctx, KillingRow, killing_id, "killing"))
    await ctx.session.flush()
