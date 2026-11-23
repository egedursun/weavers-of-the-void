from pydantic import Field

from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.couplings import FieldAgreementKind, RestraintKind, RiteComponent, SealKind, SignCause, SociolectKind
from aerona.domain.enums.knowledge import KnowledgeKind
from aerona.engine.couplings import control
from aerona.engine.couplings.deep import SealLinks
from aerona.services.player.cosmography import Edited
from aerona.services.player.scope import Command, Effect, PlayerScope, player_action


class ComponentChoice(Command):
    rite_id: int
    component: RiteComponent
    present: bool = True


class RestraintChoice(Command):
    captive_id: int
    restraint: RestraintKind
    present: bool = True


class SociolectDraft(Command):
    holder_id: int
    kind: SociolectKind


class SociolectMerge(Command):
    kept_id: int
    merged_id: int


class SignDraft(Command):
    community_id: int
    cause: SignCause


class CarrionKeep(Command):
    region_id: int
    kept: bool = True


class TeachingDraft(Command):
    teacher_id: int
    learner_id: int
    kind: KnowledgeKind


class TeachingBlock(Command):
    teacher_id: int
    learner_id: int


class LoreGrant(Command):
    beast_id: int
    collection_id: int


class LoreReveal(Command):
    beast_id: int
    learner_id: int


class AgreementDraft(Command):
    kind: FieldAgreementKind
    war_id: int | None = None
    commander_id: int | None = None
    counterpart_id: int | None = None
    place_id: int | None = None


class SealDraft(Command):
    place_id: int
    kind: SealKind = SealKind.DIVINE
    strength: int = Field(default=80, ge=1, le=100)
    oath_id: int | None = None
    power_id: int | None = None
    line_id: int | None = None


class NoveltyDraft(Edited):
    holder_id: int


class SociolectTarget(Command):
    sociolect_id: int


class SociolectEdit(Edited):
    sociolect_id: int


class SignOriginTarget(Command):
    language_id: int


class SignOriginEdit(Edited):
    language_id: int


class CarrionTarget(Command):
    region_id: int


class CarrionEdit(Edited):
    region_id: int


class TeachingTarget(Command):
    teaching_id: int


class TeachingEdit(Edited):
    teaching_id: int


class FieldAgreementTarget(Command):
    agreement_id: int


class FieldAgreementEdit(Edited):
    agreement_id: int


class DeepSealTarget(Command):
    seal_id: int


class DeepSealEdit(Edited):
    seal_id: int


class NoveltyTarget(Command):
    holder_id: int


class NoveltyEdit(Edited):
    holder_id: int


@player_action("rite_component:set", ActionKind.EDIT_RECORD)
async def rite_component_set(scope: PlayerScope, command: ComponentChoice) -> Effect:
    await control.set_component(await scope.context("rite_component_set"), command.rite_id, command.component, command.present)
    return Effect("The rite now asks for that part." if command.present else "The rite no longer asks for that part.", target_node_id=command.rite_id)


@player_action("restraint:set", ActionKind.EDIT_RECORD)
async def restraint_set(scope: PlayerScope, command: RestraintChoice) -> Effect:
    await control.set_restraint(await scope.context("restraint_set"), command.captive_id, command.restraint, command.present)
    return Effect("The captive is held so." if command.present else "That hold on the captive is loosed.")


@player_action("sociolect:create", ActionKind.EDIT_RECORD)
async def sociolect_create(scope: PlayerScope, command: SociolectDraft) -> Effect:
    await control.create_sociolect(await scope.context("sociolect_create"), command.holder_id, command.kind)
    return Effect("A way of speaking of its own takes hold.", target_node_id=command.holder_id)


@player_action("sociolect:merge", ActionKind.EDIT_RECORD)
async def sociolect_merge(scope: PlayerScope, command: SociolectMerge) -> Effect:
    row = await control.merge_sociolects(await scope.context("sociolect_merge"), command.kept_id, command.merged_id)
    return Effect("The two ways of speaking become one.", target_node_id=row.holder_entity_id)


@player_action("sign_language:create", ActionKind.EDIT_RECORD)
async def sign_language_create(scope: PlayerScope, command: SignDraft) -> Effect:
    language = await control.create_sign_language(await scope.context("sign_language_create"), command.community_id, command.cause)
    return Effect(f"{language.name} is signed among them.", target_node_id=language.id)


@player_action("carrion:keep", ActionKind.EDIT_RECORD)
async def carrion_keep(scope: PlayerScope, command: CarrionKeep) -> Effect:
    await control.keep_dead(await scope.context("carrion_keep"), command.region_id, command.kept)
    return Effect("The dead are left where they lie." if command.kept else "The living may bury their dead again.", target_node_id=command.region_id)


@player_action("carrion:clear", ActionKind.EDIT_RECORD)
async def carrion_clear(scope: PlayerScope, command: CarrionTarget) -> Effect:
    await control.clear_dead(await scope.context("carrion_clear"), command.region_id)
    return Effect("The dead of the region are cleared away.", target_node_id=command.region_id)


@player_action("teaching:grant", ActionKind.EDIT_RECORD)
async def teaching_grant(scope: PlayerScope, command: TeachingDraft) -> Effect:
    await control.grant_teaching(await scope.context("teaching_grant"), command.teacher_id, command.learner_id, command.kind)
    return Effect("The teaching is given.", target_node_id=command.learner_id)


@player_action("teaching:block", ActionKind.EDIT_RECORD)
async def teaching_block(scope: PlayerScope, command: TeachingBlock) -> Effect:
    await control.block_teaching(await scope.context("teaching_block"), command.teacher_id, command.learner_id)
    return Effect("That teacher teaches them no more.", target_node_id=command.learner_id)


@player_action("beast_lore:grant", ActionKind.EDIT_RECORD)
async def beast_lore_grant(scope: PlayerScope, command: LoreGrant) -> Effect:
    await control.grant_lore(await scope.context("beast_lore_grant"), command.beast_id, command.collection_id)
    return Effect("The beast remembers it now.", target_node_id=command.beast_id)


@player_action("beast_lore:reveal", ActionKind.EDIT_RECORD)
async def beast_lore_reveal(scope: PlayerScope, command: LoreReveal) -> Effect:
    await control.reveal_lore(await scope.context("beast_lore_reveal"), command.beast_id, command.learner_id)
    return Effect("The beast tells what it remembers.", target_node_id=command.learner_id)


@player_action("field_agreement:force", ActionKind.EDIT_RECORD)
async def field_agreement_force(scope: PlayerScope, command: AgreementDraft) -> Effect:
    await control.force_agreement(
        await scope.context("field_agreement_force"),
        command.kind,
        command.war_id,
        commander_id=command.commander_id,
        counterpart_id=command.counterpart_id,
        place_id=command.place_id,
    )
    return Effect("The commanders come to terms in the field.", target_node_id=command.commander_id or command.place_id)


@player_action("field_agreement:void", ActionKind.EDIT_RECORD)
async def field_agreement_void(scope: PlayerScope, command: FieldAgreementTarget) -> Effect:
    await control.void_agreement(await scope.context("field_agreement_void"), command.agreement_id)
    return Effect("The agreement is repudiated, at a cost in honour.")


@player_action("deep_seal:seal", ActionKind.EDIT_RECORD)
async def deep_seal_seal(scope: PlayerScope, command: SealDraft) -> Effect:
    links = SealLinks(oath_id=command.oath_id, power_id=command.power_id, line_id=command.line_id)
    await control.seal(await scope.context("deep_seal_seal"), command.place_id, command.kind, command.strength, links)
    return Effect("The deep is sealed.", target_node_id=command.place_id)


@player_action("deep_seal:unseal", ActionKind.EDIT_RECORD)
async def deep_seal_unseal(scope: PlayerScope, command: DeepSealTarget) -> Effect:
    row = await control.unseal(await scope.context("deep_seal_unseal"), command.seal_id)
    return Effect("The seal is broken; the deep is open.", target_node_id=row.place_entity_id)


@player_action("novelty:set", ActionKind.EDIT_RECORD)
async def novelty_set(scope: PlayerScope, command: NoveltyDraft) -> Effect:
    await control.set_novelty(await scope.context("novelty_set"), command.holder_id, command.values, command.release)
    return Effect("Its fashion is set.", target_node_id=command.holder_id)


@player_action("sociolect:edit", ActionKind.EDIT_RECORD)
async def sociolect_edit(scope: PlayerScope, command: SociolectEdit) -> Effect:
    await control.edit_record(await scope.context("sociolect_edit"), "sociolect", command.sociolect_id, command.values, command.release)
    return Effect("The record of the way of speaking keeps its new values.")


@player_action("sociolect:delete", ActionKind.EDIT_RECORD)
async def sociolect_delete(scope: PlayerScope, command: SociolectTarget) -> Effect:
    await control.remove_record(await scope.context("sociolect_delete"), "sociolect", command.sociolect_id)
    return Effect("The record of the way of speaking is struck out.")


@player_action("sign_origin:edit", ActionKind.EDIT_RECORD)
async def sign_origin_edit(scope: PlayerScope, command: SignOriginEdit) -> Effect:
    await control.edit_record(await scope.context("sign_origin_edit"), "sign_origin", command.language_id, command.values, command.release)
    return Effect("The record of the signed language keeps its new values.")


@player_action("sign_origin:delete", ActionKind.EDIT_RECORD)
async def sign_origin_delete(scope: PlayerScope, command: SignOriginTarget) -> Effect:
    await control.remove_record(await scope.context("sign_origin_delete"), "sign_origin", command.language_id)
    return Effect("The record of the signed language is struck out.")


@player_action("carrion:edit", ActionKind.EDIT_RECORD)
async def carrion_edit(scope: PlayerScope, command: CarrionEdit) -> Effect:
    await control.edit_record(await scope.context("carrion_edit"), "carrion", command.region_id, command.values, command.release)
    return Effect("The record of the carrion of a region keeps its new values.")


@player_action("teaching:edit", ActionKind.EDIT_RECORD)
async def teaching_edit(scope: PlayerScope, command: TeachingEdit) -> Effect:
    await control.edit_record(await scope.context("teaching_edit"), "teaching", command.teaching_id, command.values, command.release)
    return Effect("The record of the teaching keeps its new values.")


@player_action("teaching:delete", ActionKind.EDIT_RECORD)
async def teaching_delete(scope: PlayerScope, command: TeachingTarget) -> Effect:
    await control.remove_record(await scope.context("teaching_delete"), "teaching", command.teaching_id)
    return Effect("The record of the teaching is struck out.")


@player_action("field_agreement:edit", ActionKind.EDIT_RECORD)
async def field_agreement_edit(scope: PlayerScope, command: FieldAgreementEdit) -> Effect:
    await control.edit_record(await scope.context("field_agreement_edit"), "field_agreement", command.agreement_id, command.values, command.release)
    return Effect("The record of the field agreement keeps its new values.")


@player_action("field_agreement:delete", ActionKind.EDIT_RECORD)
async def field_agreement_delete(scope: PlayerScope, command: FieldAgreementTarget) -> Effect:
    await control.remove_record(await scope.context("field_agreement_delete"), "field_agreement", command.agreement_id)
    return Effect("The record of the field agreement is struck out.")


@player_action("deep_seal:edit", ActionKind.EDIT_RECORD)
async def deep_seal_edit(scope: PlayerScope, command: DeepSealEdit) -> Effect:
    await control.edit_record(await scope.context("deep_seal_edit"), "deep_seal", command.seal_id, command.values, command.release)
    return Effect("The record of the seal over the deep keeps its new values.")


@player_action("deep_seal:delete", ActionKind.EDIT_RECORD)
async def deep_seal_delete(scope: PlayerScope, command: DeepSealTarget) -> Effect:
    await control.remove_record(await scope.context("deep_seal_delete"), "deep_seal", command.seal_id)
    return Effect("The record of the seal over the deep is struck out.")


@player_action("novelty:delete", ActionKind.EDIT_RECORD)
async def novelty_delete(scope: PlayerScope, command: NoveltyTarget) -> Effect:
    await control.remove_record(await scope.context("novelty_delete"), "novelty", command.holder_id)
    return Effect("Its fashion is forgotten; it starts again as new.")
