from pydantic import Field

from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.justice import Verdict
from aerona.domain.enums.law_depth import CourtLevel, JurisdictionClaim, KillMethod, LegalSystem, RegistryKind
from aerona.domain.enums.mortal import CrimeKind
from aerona.engine.law import control
from aerona.services.player.cosmography import Edit, Edited
from aerona.services.player.scope import Command, Effect, PlayerScope, player_action

SPAN = 100
COIN = 100000


class SystemDraft(Command):
    holder_id: int
    system: LegalSystem


class SystemEdit(Edited):
    holder_id: int


class SystemTarget(Command):
    holder_id: int


class PrecedentDraft(Command):
    holder_id: int
    crime: CrimeKind
    verdict: Verdict
    court: CourtLevel = CourtLevel.LOCAL
    authority: int = Field(default=50, ge=0, le=SPAN)


class PrecedentEdit(Edited):
    precedent_id: int


class PrecedentTarget(Command):
    precedent_id: int


class AppealDraft(Command):
    case_id: int
    to_court: CourtLevel = CourtLevel.PROVINCIAL
    fee: int = Field(default=0, ge=0, le=COIN)


class AppealEdit(Edited):
    case_id: int


class AppealTarget(Command):
    case_id: int


class OracleAnswer(Command):
    case_id: int
    verdict: Verdict | None = None


class RegistryDraft(Command):
    holder_id: int
    kind: RegistryKind
    owner_id: int | None = None
    counterparty_id: int | None = None
    subject_id: int | None = None
    amount: int = Field(default=0, ge=0, le=COIN)


class RegistryEdit(Edited):
    registry_id: int


class RegistryTarget(Command):
    registry_id: int


class ClaimDraft(Command):
    holder_id: int
    claimant_id: int
    claim: JurisdictionClaim
    strength: int = Field(default=50, ge=0, le=SPAN)


class ClaimEdit(Edited):
    holder_id: int
    claimant_id: int
    claim: JurisdictionClaim


class ClaimTarget(Command):
    holder_id: int
    claimant_id: int
    claim: JurisdictionClaim


class PardonDraft(Command):
    granter_id: int
    mortal_id: int


class RealmTarget(Command):
    polity_id: int


class PardonTarget(Command):
    pardon_id: int


class OutlawDraft(Command):
    mortal_id: int
    polity_id: int | None = None
    bounty: int = Field(default=30, ge=0, le=COIN)


class OutlawEdit(Edited):
    mortal_id: int


class MortalTarget(Command):
    mortal_id: int


class PrisonDraft(Command):
    structure_id: int
    values: Edit = Field(default_factory=dict)


class PrisonEdit(Edited):
    structure_id: int


class PrisonTarget(Command):
    structure_id: int


class JailDraft(Command):
    mortal_id: int
    prison_id: int
    term: int = Field(default=3, ge=0, le=SPAN)


class PrisonerEdit(Edited):
    mortal_id: int


class CellDraft(Command):
    network_id: int
    handler_id: int | None = None
    safe_house_id: int | None = None
    dead_drops: int = Field(default=1, ge=0, le=SPAN)


class CellEdit(Edited):
    cell_id: int


class CellTarget(Command):
    cell_id: int


class HuntTarget(Command):
    hunt_id: int


class DefectionDraft(Command):
    mortal_id: int
    from_id: int | None = None
    to_id: int
    protected: bool = True


class DefectionEdit(Edited):
    defection_id: int


class DefectionTarget(Command):
    defection_id: int


class KillingDraft(Command):
    victim_id: int
    killer_id: int | None = None
    method: KillMethod
    recognised: bool = True


class KillingEdit(Edited):
    killing_id: int


class KillingTarget(Command):
    killing_id: int


@player_action("legal_system:set", ActionKind.EDIT_RECORD)
async def legal_system_set(scope: PlayerScope, command: SystemDraft) -> Effect:
    ctx = await scope.context("legal_system_set")
    await control.set_system(ctx, command.holder_id, command.system)
    return Effect("The realm judges by that law now.", command.holder_id)


@player_action("legal_system:edit", ActionKind.EDIT_RECORD)
async def legal_system_edit(scope: PlayerScope, command: SystemEdit) -> Effect:
    ctx = await scope.context("legal_system_edit")
    await control.edit_system(ctx, command.holder_id, command.values, command.release)
    return Effect("The legal system is set so.", command.holder_id)


@player_action("legal_system:delete", ActionKind.EDIT_RECORD)
async def legal_system_delete(scope: PlayerScope, command: SystemTarget) -> Effect:
    ctx = await scope.context("legal_system_delete")
    await control.delete_system(ctx, command.holder_id)
    return Effect("The legal system will be chosen anew.", command.holder_id)


@player_action("precedent:add", ActionKind.EDIT_RECORD)
async def precedent_add(scope: PlayerScope, command: PrecedentDraft) -> Effect:
    ctx = await scope.context("precedent_add")
    await control.add_precedent(ctx, command.holder_id, command.crime, verdict=command.verdict, court=command.court, authority=command.authority)
    return Effect("The ruling binds the courts.", command.holder_id)


@player_action("precedent:edit", ActionKind.EDIT_RECORD)
async def precedent_edit(scope: PlayerScope, command: PrecedentEdit) -> Effect:
    ctx = await scope.context("precedent_edit")
    await control.edit_precedent(ctx, command.precedent_id, command.values, command.release)
    return Effect("The precedent is set so.")


@player_action("precedent:delete", ActionKind.EDIT_RECORD)
async def precedent_delete(scope: PlayerScope, command: PrecedentTarget) -> Effect:
    ctx = await scope.context("precedent_delete")
    await control.delete_precedent(ctx, command.precedent_id)
    return Effect("The precedent is struck.")


@player_action("appeal:file", ActionKind.EDIT_RECORD)
async def appeal_file(scope: PlayerScope, command: AppealDraft) -> Effect:
    ctx = await scope.context("appeal_file")
    await control.file_appeal(ctx, command.case_id, command.to_court, command.fee)
    return Effect("The appeal is filed.")


@player_action("appeal:edit", ActionKind.EDIT_RECORD)
async def appeal_edit(scope: PlayerScope, command: AppealEdit) -> Effect:
    ctx = await scope.context("appeal_edit")
    await control.edit_appeal(ctx, command.case_id, command.values, command.release)
    return Effect("The appeal is set so.")


@player_action("appeal:hear", ActionKind.EDIT_RECORD)
async def appeal_hear(scope: PlayerScope, command: AppealTarget) -> Effect:
    ctx = await scope.context("appeal_hear")
    await control.hear_now(ctx, command.case_id)
    return Effect("The higher court has ruled.")


@player_action("appeal:delete", ActionKind.EDIT_RECORD)
async def appeal_delete(scope: PlayerScope, command: AppealTarget) -> Effect:
    ctx = await scope.context("appeal_delete")
    await control.delete_appeal(ctx, command.case_id)
    return Effect("The appeal is withdrawn.")


@player_action("oracle:answer", ActionKind.EDIT_RECORD)
async def oracle_answer(scope: PlayerScope, command: OracleAnswer) -> Effect:
    ctx = await scope.context("oracle_answer")
    await control.answer_oracle(ctx, command.case_id, command.verdict)
    return Effect("The oracle will speak your answer.")


@player_action("registry:add", ActionKind.EDIT_RECORD)
async def registry_add(scope: PlayerScope, command: RegistryDraft) -> Effect:
    ctx = await scope.context("registry_add")
    await control.add_registry(
        ctx,
        command.holder_id,
        command.kind,
        owner_id=command.owner_id,
        counterparty_id=command.counterparty_id,
        subject_id=command.subject_id,
        amount=command.amount,
    )
    return Effect("The deed is registered.", command.holder_id)


@player_action("registry:edit", ActionKind.EDIT_RECORD)
async def registry_edit(scope: PlayerScope, command: RegistryEdit) -> Effect:
    ctx = await scope.context("registry_edit")
    await control.edit_registry(ctx, command.registry_id, command.values, command.release)
    return Effect("The deed is set so.")


@player_action("registry:delete", ActionKind.EDIT_RECORD)
async def registry_delete(scope: PlayerScope, command: RegistryTarget) -> Effect:
    ctx = await scope.context("registry_delete")
    await control.delete_registry(ctx, command.registry_id)
    return Effect("The deed is struck.")


@player_action("jurisdiction:set", ActionKind.EDIT_RECORD)
async def jurisdiction_set(scope: PlayerScope, command: ClaimDraft) -> Effect:
    ctx = await scope.context("jurisdiction_set")
    await control.set_claim(ctx, command.holder_id, command.claimant_id, command.claim, command.strength)
    return Effect("The claim to courts is made.", command.holder_id)


@player_action("jurisdiction:edit", ActionKind.EDIT_RECORD)
async def jurisdiction_edit(scope: PlayerScope, command: ClaimEdit) -> Effect:
    ctx = await scope.context("jurisdiction_edit")
    await control.edit_claim(ctx, (command.holder_id, command.claimant_id, command.claim), command.values, command.release)
    return Effect("The claim is set so.", command.holder_id)


@player_action("jurisdiction:delete", ActionKind.EDIT_RECORD)
async def jurisdiction_delete(scope: PlayerScope, command: ClaimTarget) -> Effect:
    ctx = await scope.context("jurisdiction_delete")
    await control.delete_claim(ctx, (command.holder_id, command.claimant_id, command.claim))
    return Effect("The claim is ended.", command.holder_id)


@player_action("pardon:grant", ActionKind.EDIT_RECORD)
async def pardon_grant(scope: PlayerScope, command: PardonDraft) -> Effect:
    ctx = await scope.context("pardon_grant")
    await control.pardon(ctx, command.granter_id, command.mortal_id)
    return Effect("The pardon is granted.", command.mortal_id)


@player_action("amnesty:declare", ActionKind.EDIT_RECORD)
async def amnesty_declare(scope: PlayerScope, command: RealmTarget) -> Effect:
    ctx = await scope.context("amnesty_declare")
    await control.amnesty(ctx, command.polity_id)
    return Effect("The amnesty is declared.", command.polity_id)


@player_action("pardon:delete", ActionKind.EDIT_RECORD)
async def pardon_delete(scope: PlayerScope, command: PardonTarget) -> Effect:
    ctx = await scope.context("pardon_delete")
    await control.delete_pardon(ctx, command.pardon_id)
    return Effect("The pardon is struck from the record.")


@player_action("outlaw:declare", ActionKind.EDIT_RECORD)
async def outlaw_declare(scope: PlayerScope, command: OutlawDraft) -> Effect:
    ctx = await scope.context("outlaw_declare")
    await control.declare(ctx, command.mortal_id, command.polity_id, command.bounty)
    return Effect("The mortal is outlawed.", command.mortal_id)


@player_action("outlaw:edit", ActionKind.EDIT_RECORD)
async def outlaw_edit(scope: PlayerScope, command: OutlawEdit) -> Effect:
    ctx = await scope.context("outlaw_edit")
    await control.edit_outlaw(ctx, command.mortal_id, command.values, command.release)
    return Effect("The outlaw is set so.", command.mortal_id)


@player_action("outlaw:delete", ActionKind.EDIT_RECORD)
async def outlaw_delete(scope: PlayerScope, command: MortalTarget) -> Effect:
    ctx = await scope.context("outlaw_delete")
    await control.lift_outlawry(ctx, command.mortal_id)
    return Effect("The outlawry is lifted.", command.mortal_id)


@player_action("prison:set", ActionKind.EDIT_RECORD)
async def prison_set(scope: PlayerScope, command: PrisonDraft) -> Effect:
    ctx = await scope.context("prison_set")
    await control.set_prison(ctx, command.structure_id, command.values)
    return Effect("The prison is set so.", command.structure_id)


@player_action("prison:edit", ActionKind.EDIT_RECORD)
async def prison_edit(scope: PlayerScope, command: PrisonEdit) -> Effect:
    ctx = await scope.context("prison_edit")
    await control.edit_prison(ctx, command.structure_id, command.values, command.release)
    return Effect("The prison is set so.", command.structure_id)


@player_action("prison:delete", ActionKind.EDIT_RECORD)
async def prison_delete(scope: PlayerScope, command: PrisonTarget) -> Effect:
    ctx = await scope.context("prison_delete")
    await control.delete_prison(ctx, command.structure_id)
    return Effect("The prison will be drawn anew.", command.structure_id)


@player_action("prisoner:jail", ActionKind.EDIT_RECORD)
async def prisoner_jail(scope: PlayerScope, command: JailDraft) -> Effect:
    ctx = await scope.context("prisoner_jail")
    await control.jail(ctx, command.mortal_id, command.prison_id, command.term)
    return Effect("The mortal is in prison.", command.mortal_id)


@player_action("prisoner:edit", ActionKind.EDIT_RECORD)
async def prisoner_edit(scope: PlayerScope, command: PrisonerEdit) -> Effect:
    ctx = await scope.context("prisoner_edit")
    await control.edit_prisoner(ctx, command.mortal_id, command.values, command.release)
    return Effect("The prisoner is set so.", command.mortal_id)


@player_action("prisoner:free", ActionKind.EDIT_RECORD)
async def prisoner_free(scope: PlayerScope, command: MortalTarget) -> Effect:
    ctx = await scope.context("prisoner_free")
    await control.free(ctx, command.mortal_id)
    return Effect("The prisoner walks free.", command.mortal_id)


@player_action("spy_cell:add", ActionKind.EDIT_RECORD)
async def spy_cell_add(scope: PlayerScope, command: CellDraft) -> Effect:
    ctx = await scope.context("spy_cell_add")
    await control.add_cell(ctx, command.network_id, command.handler_id, command.safe_house_id, command.dead_drops)
    return Effect("The cell is formed.")


@player_action("spy_cell:edit", ActionKind.EDIT_RECORD)
async def spy_cell_edit(scope: PlayerScope, command: CellEdit) -> Effect:
    ctx = await scope.context("spy_cell_edit")
    await control.edit_cell(ctx, command.cell_id, command.values, command.release)
    return Effect("The cell is set so.")


@player_action("spy_cell:delete", ActionKind.EDIT_RECORD)
async def spy_cell_delete(scope: PlayerScope, command: CellTarget) -> Effect:
    ctx = await scope.context("spy_cell_delete")
    await control.delete_cell(ctx, command.cell_id)
    return Effect("The cell is broken up.")


@player_action("mole_hunt:order", ActionKind.EDIT_RECORD)
async def mole_hunt_order(scope: PlayerScope, command: RealmTarget) -> Effect:
    ctx = await scope.context("mole_hunt_order")
    await control.order_hunt(ctx, command.polity_id)
    return Effect("The spymaster hunts.", command.polity_id)


@player_action("mole_hunt:delete", ActionKind.EDIT_RECORD)
async def mole_hunt_delete(scope: PlayerScope, command: HuntTarget) -> Effect:
    ctx = await scope.context("mole_hunt_delete")
    await control.delete_hunt(ctx, command.hunt_id)
    return Effect("The hunt is struck from the record.")


@player_action("defection:make", ActionKind.EDIT_RECORD)
async def defection_make(scope: PlayerScope, command: DefectionDraft) -> Effect:
    ctx = await scope.context("defection_make")
    await control.defect_now(ctx, command.mortal_id, command.from_id, command.to_id, protected=command.protected)
    return Effect("The mortal has crossed over.", command.mortal_id)


@player_action("defection:edit", ActionKind.EDIT_RECORD)
async def defection_edit(scope: PlayerScope, command: DefectionEdit) -> Effect:
    ctx = await scope.context("defection_edit")
    await control.edit_defection(ctx, command.defection_id, command.values, command.release)
    return Effect("The defection is set so.")


@player_action("defection:delete", ActionKind.EDIT_RECORD)
async def defection_delete(scope: PlayerScope, command: DefectionTarget) -> Effect:
    ctx = await scope.context("defection_delete")
    await control.delete_defection(ctx, command.defection_id)
    return Effect("The defection is struck from the record.")


@player_action("killing:add", ActionKind.EDIT_RECORD)
async def killing_add(scope: PlayerScope, command: KillingDraft) -> Effect:
    ctx = await scope.context("killing_add")
    await control.add_killing(ctx, command.victim_id, command.killer_id, command.method, recognised=command.recognised)
    return Effect("The killing is recorded.", command.victim_id)


@player_action("killing:edit", ActionKind.EDIT_RECORD)
async def killing_edit(scope: PlayerScope, command: KillingEdit) -> Effect:
    ctx = await scope.context("killing_edit")
    await control.edit_killing(ctx, command.killing_id, command.values, command.release)
    return Effect("The killing is set so.")


@player_action("killing:delete", ActionKind.EDIT_RECORD)
async def killing_delete(scope: PlayerScope, command: KillingTarget) -> Effect:
    ctx = await scope.context("killing_delete")
    await control.delete_killing(ctx, command.killing_id)
    return Effect("The killing is struck from the record.")
