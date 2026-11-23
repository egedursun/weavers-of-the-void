from pydantic import Field

from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.culture import ProphecyPredicate
from aerona.domain.enums.mind import Emotion
from aerona.domain.enums.sacred import (
    AfterlifeModel,
    BureauRank,
    DivinationKind,
    DivinationQuestion,
    ForesightSource,
    GeniusLocusKind,
    OmenVerdict,
    PetitionKind,
    SacramentKind,
    SacramentProtection,
    TheodicyCause,
    VisionKind,
)
from aerona.engine.sacred import control
from aerona.services.player.cosmography import Edited
from aerona.services.player.scope import Command, Effect, PlayerScope, player_action

SPAN = 100
MANY = 1_000_000


class GeniusDraft(Command):
    place_id: int
    kind: GeniusLocusKind | None = None
    community_id: int | None = None


class SpiritTarget(Command):
    spirit_id: int


class SpiritEdit(Edited):
    spirit_id: int


class OfficeDraft(Command):
    spirit_id: int
    rank: BureauRank = BureauRank.LOCAL
    superior_id: int | None = None
    overseer_id: int | None = None
    jurisdiction_id: int | None = None


class PetitionDraft(Command):
    petitioner_id: int
    office_id: int
    kind: PetitionKind = PetitionKind.HEALING
    defendant_id: int | None = None
    target_id: int | None = None
    bribe: int = Field(default=0, ge=0, le=MANY)


class PetitionTarget(Command):
    petition_id: int


class PetitionJudgement(Command):
    petition_id: int
    granted: bool = True


class PetitionEdit(Edited):
    petition_id: int


class MysticDraft(Command):
    mortal_id: int
    sender_id: int | None = None


class MysticTarget(Command):
    mortal_id: int


class MysticEdit(Edited):
    mortal_id: int


class VisionDraft(Command):
    mystic_id: int
    sender_id: int | None = None
    kind: VisionKind | None = None


class VisionTarget(Command):
    vision_id: int


class VisionEdit(Edited):
    vision_id: int


class MillenarianDraft(Command):
    town_id: int
    prophet_id: int | None = None
    prophecy_id: int | None = None


class MillenarianTarget(Command):
    movement_id: int


class MillenarianEdit(Edited):
    movement_id: int


class CrisisDraft(Command):
    town_id: int
    cause: TheodicyCause = TheodicyCause.PLAGUE
    suffering: int = Field(default=50, ge=0, le=SPAN)


class CrisisTarget(Command):
    crisis_id: int


class CrisisAnswer(Command):
    crisis_id: int
    god_id: int | None = None


class CrisisEdit(Edited):
    crisis_id: int


class TeachingDraft(Command):
    cult_id: int
    kind: SacramentKind = SacramentKind.BIRTH_BLESSING
    protection: SacramentProtection | None = None
    strength: int = Field(default=60, ge=0, le=SPAN)


class TeachingTarget(Command):
    cult_id: int
    kind: SacramentKind


class TeachingEdit(Edited):
    cult_id: int
    kind: SacramentKind


class SacramentDraft(Command):
    mortal_id: int
    kind: SacramentKind = SacramentKind.BIRTH_BLESSING
    priest_id: int | None = None


class SacramentTarget(Command):
    sacrament_id: int


class SacramentEdit(Edited):
    sacrament_id: int


class AfterlifeDraft(Command):
    cult_id: int
    model: AfterlifeModel | None = None


class CultTarget(Command):
    cult_id: int


class AfterlifeAlignment(Command):
    cult_id: int
    god_id: int


class AfterlifeEdit(Edited):
    cult_id: int


class ClimateDraft(Command):
    town_id: int


class TownTarget(Command):
    town_id: int


class ClimateEdit(Edited):
    town_id: int


class SystemDraft(Command):
    people_id: int
    kind: DivinationKind = DivinationKind.AUGURY


class SystemTarget(Command):
    system_id: int


class SystemEdit(Edited):
    system_id: int


class ReadingDraft(Command):
    realm_id: int
    question: DivinationQuestion = DivinationQuestion.HARVEST
    verdict: OmenVerdict | None = None
    system_id: int | None = None


class ReadingTarget(Command):
    reading_id: int


class ReadingEdit(Edited):
    reading_id: int


class ForesightDraft(Command):
    seer_id: int
    subject_id: int
    predicate: ProphecyPredicate = ProphecyPredicate.DIES
    certainty: int = Field(default=60, ge=0, le=SPAN)
    source: ForesightSource = ForesightSource.POWER
    proclaimed: bool = False


class ForesightTarget(Command):
    foresight_id: int


class ForesightEdit(Edited):
    foresight_id: int


class ModelDraft(Command):
    order_id: int
    realm_id: int | None = None


class ModelTarget(Command):
    model_id: int


class ModelEdit(Edited):
    model_id: int


class FeedingDraft(Command):
    god_id: int
    emotion: Emotion = Emotion.AWE
    weight: int = Field(default=50, ge=0, le=SPAN)


class FeedingTarget(Command):
    god_id: int
    emotion: Emotion


class FeedingEdit(Edited):
    god_id: int
    emotion: Emotion


@player_action("genius_locus:create", ActionKind.EDIT_RECORD)
async def genius_locus_create(scope: PlayerScope, command: GeniusDraft) -> Effect:
    row = await control.raise_spirit(await scope.context("genius_locus_create"), command.place_id, command.kind, command.community_id, None)
    return Effect("A spirit comes to dwell in the place.", command.place_id, values={"spirit_id": row.spirit_entity_id})


@player_action("genius_locus:edit", ActionKind.EDIT_RECORD)
async def genius_locus_edit(scope: PlayerScope, command: SpiritEdit) -> Effect:
    await control.edit_record(await scope.context("genius_locus_edit"), "genius_locus", command.spirit_id, command.values, command.release)
    return Effect("The place spirit is set so.", command.spirit_id)


@player_action("genius_locus:delete", ActionKind.EDIT_RECORD)
async def genius_locus_delete(scope: PlayerScope, command: SpiritTarget) -> Effect:
    await control.delete_record(await scope.context("genius_locus_delete"), "genius_locus", command.spirit_id)
    return Effect("The spirit no longer keeps the place.", command.spirit_id)


@player_action("spirit_office:set", ActionKind.EDIT_RECORD)
async def spirit_office_set(scope: PlayerScope, command: OfficeDraft) -> Effect:
    await control.set_office(
        await scope.context("spirit_office_set"),
        command.spirit_id,
        command.rank,
        superior_id=command.superior_id,
        overseer_id=command.overseer_id,
        jurisdiction_id=command.jurisdiction_id,
    )
    return Effect("The spirit holds its office.", command.spirit_id)


@player_action("spirit_office:edit", ActionKind.EDIT_RECORD)
async def spirit_office_edit(scope: PlayerScope, command: SpiritEdit) -> Effect:
    await control.edit_record(await scope.context("spirit_office_edit"), "spirit_office", command.spirit_id, command.values, command.release)
    return Effect("The spirit office is set so.", command.spirit_id)


@player_action("spirit_office:delete", ActionKind.EDIT_RECORD)
async def spirit_office_delete(scope: PlayerScope, command: SpiritTarget) -> Effect:
    await control.delete_record(await scope.context("spirit_office_delete"), "spirit_office", command.spirit_id)
    return Effect("The spirit holds no office.", command.spirit_id)


@player_action("petition:create", ActionKind.EDIT_RECORD)
async def petition_create(scope: PlayerScope, command: PetitionDraft) -> Effect:
    row = await control.lodge_petition(
        await scope.context("petition_create"),
        command.petitioner_id,
        command.office_id,
        command.kind,
        defendant_id=command.defendant_id,
        bribe=command.bribe,
        target_id=command.target_id,
    )
    return Effect("The petition is filed with the office.", command.office_id, values={"petition_id": row.id})


@player_action("petition:judge", ActionKind.EDIT_RECORD)
async def petition_judge(scope: PlayerScope, command: PetitionJudgement) -> Effect:
    row = await control.judge(await scope.context("petition_judge"), command.petition_id, command.granted, None)
    return Effect("The petition is granted." if command.granted else "The petition is denied.", row.office_spirit_id)


@player_action("petition:edit", ActionKind.EDIT_RECORD)
async def petition_edit(scope: PlayerScope, command: PetitionEdit) -> Effect:
    row = await control.edit_record(await scope.context("petition_edit"), "petition", command.petition_id, command.values, command.release)
    return Effect("The petition is set so.", getattr(row, "office_spirit_id", None))


@player_action("petition:delete", ActionKind.EDIT_RECORD)
async def petition_delete(scope: PlayerScope, command: PetitionTarget) -> Effect:
    await control.delete_record(await scope.context("petition_delete"), "petition", command.petition_id)
    return Effect("The petition is struck from the rolls.")


@player_action("mystic:create", ActionKind.EDIT_RECORD)
async def mystic_create(scope: PlayerScope, command: MysticDraft) -> Effect:
    await control.make_mystic(await scope.context("mystic_create"), command.mortal_id, command.sender_id)
    return Effect("A vision comes to the mortal.", command.mortal_id)


@player_action("mystic:edit", ActionKind.EDIT_RECORD)
async def mystic_edit(scope: PlayerScope, command: MysticEdit) -> Effect:
    await control.edit_record(await scope.context("mystic_edit"), "mystic", command.mortal_id, command.values, command.release)
    return Effect("The mystic is set so.", command.mortal_id)


@player_action("mystic:delete", ActionKind.EDIT_RECORD)
async def mystic_delete(scope: PlayerScope, command: MysticTarget) -> Effect:
    await control.delete_record(await scope.context("mystic_delete"), "mystic", command.mortal_id)
    return Effect("The mortal is a mystic no more.", command.mortal_id)


@player_action("vision:create", ActionKind.EDIT_RECORD)
async def vision_create(scope: PlayerScope, command: VisionDraft) -> Effect:
    row = await control.send_vision(await scope.context("vision_create"), command.mystic_id, command.sender_id, command.kind)
    return Effect("The mystic sees another vision.", command.mystic_id, values={"vision_id": row.id})


@player_action("vision:edit", ActionKind.EDIT_RECORD)
async def vision_edit(scope: PlayerScope, command: VisionEdit) -> Effect:
    row = await control.edit_record(await scope.context("vision_edit"), "vision", command.vision_id, command.values, command.release)
    return Effect("The vision is set so.", getattr(row, "mystic_entity_id", None))


@player_action("vision:delete", ActionKind.EDIT_RECORD)
async def vision_delete(scope: PlayerScope, command: VisionTarget) -> Effect:
    await control.delete_record(await scope.context("vision_delete"), "vision", command.vision_id)
    return Effect("The vision is struck from the record.")


@player_action("millenarian:create", ActionKind.EDIT_RECORD)
async def millenarian_create(scope: PlayerScope, command: MillenarianDraft) -> Effect:
    row = await control.stir_movement(await scope.context("millenarian_create"), command.town_id, command.prophet_id, command.prophecy_id)
    return Effect("The faithful of the town begin to await the end.", command.town_id, values={"movement_id": row.id})


@player_action("millenarian:edit", ActionKind.EDIT_RECORD)
async def millenarian_edit(scope: PlayerScope, command: MillenarianEdit) -> Effect:
    row = await control.edit_record(await scope.context("millenarian_edit"), "millenarian", command.movement_id, command.values, command.release)
    return Effect("The movement is set so.", getattr(row, "settlement_entity_id", None))


@player_action("millenarian:delete", ActionKind.EDIT_RECORD)
async def millenarian_delete(scope: PlayerScope, command: MillenarianTarget) -> Effect:
    await control.delete_record(await scope.context("millenarian_delete"), "millenarian", command.movement_id)
    return Effect("The movement is struck from the record.")


@player_action("theodicy:create", ActionKind.EDIT_RECORD)
async def theodicy_create(scope: PlayerScope, command: CrisisDraft) -> Effect:
    row = await control.test_faith(await scope.context("theodicy_create"), command.town_id, command.cause, command.suffering)
    return Effect("The teaching of the town's church is put to the test.", command.town_id, values={"crisis_id": row.id})


@player_action("theodicy:answer", ActionKind.EDIT_RECORD)
async def theodicy_answer(scope: PlayerScope, command: CrisisAnswer) -> Effect:
    row = await control.answer_crisis(await scope.context("theodicy_answer"), command.crisis_id, command.god_id)
    return Effect("The god answers the suffering, and the faithful see it.", row.community_entity_id)


@player_action("theodicy:edit", ActionKind.EDIT_RECORD)
async def theodicy_edit(scope: PlayerScope, command: CrisisEdit) -> Effect:
    row = await control.edit_record(await scope.context("theodicy_edit"), "theodicy", command.crisis_id, command.values, command.release)
    return Effect("The crisis of faith is set so.", getattr(row, "community_entity_id", None))


@player_action("theodicy:delete", ActionKind.EDIT_RECORD)
async def theodicy_delete(scope: PlayerScope, command: CrisisTarget) -> Effect:
    await control.delete_record(await scope.context("theodicy_delete"), "theodicy", command.crisis_id)
    return Effect("The crisis of faith is struck from the record.")


@player_action("doctrine_sacrament:set", ActionKind.EDIT_RECORD)
async def doctrine_sacrament_set(scope: PlayerScope, command: TeachingDraft) -> Effect:
    await control.teach(await scope.context("doctrine_sacrament_set"), command.cult_id, command.kind, command.protection, command.strength)
    return Effect("The church teaches the sacrament.", command.cult_id)


@player_action("doctrine_sacrament:edit", ActionKind.EDIT_RECORD)
async def doctrine_sacrament_edit(scope: PlayerScope, command: TeachingEdit) -> Effect:
    key = (command.cult_id, command.kind)
    await control.edit_record(await scope.context("doctrine_sacrament_edit"), "doctrine_sacrament", key, command.values, command.release)
    return Effect("The taught sacrament is set so.", command.cult_id)


@player_action("doctrine_sacrament:delete", ActionKind.EDIT_RECORD)
async def doctrine_sacrament_delete(scope: PlayerScope, command: TeachingTarget) -> Effect:
    await control.delete_record(await scope.context("doctrine_sacrament_delete"), "doctrine_sacrament", (command.cult_id, command.kind))
    return Effect("The church no longer teaches the sacrament.", command.cult_id)


@player_action("sacrament:create", ActionKind.EDIT_RECORD)
async def sacrament_create(scope: PlayerScope, command: SacramentDraft) -> Effect:
    row = await control.give_sacrament(await scope.context("sacrament_create"), command.mortal_id, command.kind, command.priest_id)
    return Effect("The sacrament was missed." if row.missed else "The sacrament is given.", command.mortal_id, values={"sacrament_id": row.id})


@player_action("sacrament:edit", ActionKind.EDIT_RECORD)
async def sacrament_edit(scope: PlayerScope, command: SacramentEdit) -> Effect:
    row = await control.edit_record(await scope.context("sacrament_edit"), "sacrament", command.sacrament_id, command.values, command.release)
    return Effect("The sacrament is set so.", getattr(row, "mortal_entity_id", None))


@player_action("sacrament:delete", ActionKind.EDIT_RECORD)
async def sacrament_delete(scope: PlayerScope, command: SacramentTarget) -> Effect:
    await control.delete_record(await scope.context("sacrament_delete"), "sacrament", command.sacrament_id)
    return Effect("The sacrament is struck from the record.")


@player_action("doctrine_afterlife:set", ActionKind.EDIT_RECORD)
async def doctrine_afterlife_set(scope: PlayerScope, command: AfterlifeDraft) -> Effect:
    await control.teach_afterlife(await scope.context("doctrine_afterlife_set"), command.cult_id, command.model)
    return Effect("The church teaches its afterlife.", command.cult_id)


@player_action("doctrine_afterlife:align", ActionKind.EDIT_RECORD)
async def doctrine_afterlife_align(scope: PlayerScope, command: AfterlifeAlignment) -> Effect:
    await control.align(await scope.context("doctrine_afterlife_align"), command.cult_id, command.god_id, charge=False)
    return Effect("The afterlife is made to match the teaching.", command.cult_id)


@player_action("doctrine_afterlife:edit", ActionKind.EDIT_RECORD)
async def doctrine_afterlife_edit(scope: PlayerScope, command: AfterlifeEdit) -> Effect:
    await control.edit_record(await scope.context("doctrine_afterlife_edit"), "doctrine_afterlife", command.cult_id, command.values, command.release)
    return Effect("The taught afterlife is set so.", command.cult_id)


@player_action("doctrine_afterlife:delete", ActionKind.EDIT_RECORD)
async def doctrine_afterlife_delete(scope: PlayerScope, command: CultTarget) -> Effect:
    await control.delete_record(await scope.context("doctrine_afterlife_delete"), "doctrine_afterlife", command.cult_id)
    return Effect("The church's afterlife will be read anew.", command.cult_id)


@player_action("faith_climate:set", ActionKind.EDIT_RECORD)
async def faith_climate_set(scope: PlayerScope, command: ClimateDraft) -> Effect:
    await control.weigh_climate(await scope.context("faith_climate_set"), command.town_id)
    return Effect("The town's faith is weighed.", command.town_id)


@player_action("faith_climate:edit", ActionKind.EDIT_RECORD)
async def faith_climate_edit(scope: PlayerScope, command: ClimateEdit) -> Effect:
    await control.edit_record(await scope.context("faith_climate_edit"), "faith_climate", command.town_id, command.values, command.release)
    return Effect("The town's faith is set so.", command.town_id)


@player_action("faith_climate:delete", ActionKind.EDIT_RECORD)
async def faith_climate_delete(scope: PlayerScope, command: TownTarget) -> Effect:
    await control.delete_record(await scope.context("faith_climate_delete"), "faith_climate", command.town_id)
    return Effect("The town's faith will be weighed anew.", command.town_id)


@player_action("divination_system:create", ActionKind.EDIT_RECORD)
async def divination_system_create(scope: PlayerScope, command: SystemDraft) -> Effect:
    row = await control.found_system(await scope.context("divination_system_create"), command.people_id, command.kind)
    return Effect("The people take up a way of reading what is to come.", command.people_id, values={"system_id": row.id})


@player_action("divination_system:read", ActionKind.EDIT_RECORD)
async def divination_system_read(scope: PlayerScope, command: SystemTarget) -> Effect:
    row = await control.refresh_validity(await scope.context("divination_system_read"), command.system_id)
    return Effect("The way of reading is tested against the world.", row.people_entity_id)


@player_action("divination_system:edit", ActionKind.EDIT_RECORD)
async def divination_system_edit(scope: PlayerScope, command: SystemEdit) -> Effect:
    row = await control.edit_record(await scope.context("divination_system_edit"), "divination_system", command.system_id, command.values, command.release)
    return Effect("The divination system is set so.", getattr(row, "people_entity_id", None))


@player_action("divination_system:delete", ActionKind.EDIT_RECORD)
async def divination_system_delete(scope: PlayerScope, command: SystemTarget) -> Effect:
    await control.delete_record(await scope.context("divination_system_delete"), "divination_system", command.system_id)
    return Effect("The way of reading is forgotten.")


@player_action("divination:create", ActionKind.EDIT_RECORD)
async def divination_create(scope: PlayerScope, command: ReadingDraft) -> Effect:
    row = await control.read_omens(
        await scope.context("divination_create"), command.realm_id, command.question, verdict=command.verdict, swayed_by=None, system_id=command.system_id
    )
    return Effect("The diviners read the omens for the ruler.", command.realm_id, values={"reading_id": row.id})


@player_action("divination:edit", ActionKind.EDIT_RECORD)
async def divination_edit(scope: PlayerScope, command: ReadingEdit) -> Effect:
    row = await control.edit_record(await scope.context("divination_edit"), "divination", command.reading_id, command.values, command.release)
    return Effect("The reading is set so.", getattr(row, "client_entity_id", None))


@player_action("divination:delete", ActionKind.EDIT_RECORD)
async def divination_delete(scope: PlayerScope, command: ReadingTarget) -> Effect:
    await control.delete_record(await scope.context("divination_delete"), "divination", command.reading_id)
    return Effect("The reading is struck from the record.")


@player_action("foresight:create", ActionKind.EDIT_RECORD)
async def foresight_create(scope: PlayerScope, command: ForesightDraft) -> Effect:
    row = await control.foretell(
        await scope.context("foresight_create"),
        command.seer_id,
        command.predicate,
        command.subject_id,
        certainty=command.certainty,
        source=command.source,
        proclaimed=command.proclaimed,
    )
    return Effect("The seer foresees what is likely to come.", command.seer_id, values={"foresight_id": row.id})


@player_action("foresight:edit", ActionKind.EDIT_RECORD)
async def foresight_edit(scope: PlayerScope, command: ForesightEdit) -> Effect:
    row = await control.edit_record(await scope.context("foresight_edit"), "foresight", command.foresight_id, command.values, command.release)
    return Effect("The foresight is set so.", getattr(row, "seer_node_id", None))


@player_action("foresight:delete", ActionKind.EDIT_RECORD)
async def foresight_delete(scope: PlayerScope, command: ForesightTarget) -> Effect:
    await control.delete_record(await scope.context("foresight_delete"), "foresight", command.foresight_id)
    return Effect("The foresight is struck from the record.")


@player_action("forecast_model:create", ActionKind.EDIT_RECORD)
async def forecast_model_create(scope: PlayerScope, command: ModelDraft) -> Effect:
    row = await control.build_model(await scope.context("forecast_model_create"), command.order_id, command.realm_id)
    return Effect("The order begins to forecast the realm.", command.order_id, values={"model_id": row.id})


@player_action("forecast_model:edit", ActionKind.EDIT_RECORD)
async def forecast_model_edit(scope: PlayerScope, command: ModelEdit) -> Effect:
    row = await control.edit_record(await scope.context("forecast_model_edit"), "forecast_model", command.model_id, command.values, command.release)
    return Effect("The forecast model is set so.", getattr(row, "order_entity_id", None))


@player_action("forecast_model:delete", ActionKind.EDIT_RECORD)
async def forecast_model_delete(scope: PlayerScope, command: ModelTarget) -> Effect:
    await control.delete_record(await scope.context("forecast_model_delete"), "forecast_model", command.model_id)
    return Effect("The forecast model is set aside.")


@player_action("god_feeding:set", ActionKind.EDIT_RECORD)
async def god_feeding_set(scope: PlayerScope, command: FeedingDraft) -> Effect:
    await control.set_feeding(await scope.context("god_feeding_set"), command.god_id, command.emotion, command.weight)
    return Effect("The god feeds on that feeling.", command.god_id)


@player_action("god_feeding:edit", ActionKind.EDIT_RECORD)
async def god_feeding_edit(scope: PlayerScope, command: FeedingEdit) -> Effect:
    key = (command.god_id, command.emotion)
    await control.edit_record(await scope.context("god_feeding_edit"), "god_feeding", key, command.values, command.release)
    return Effect("The feeding is set so.", command.god_id)


@player_action("god_feeding:delete", ActionKind.EDIT_RECORD)
async def god_feeding_delete(scope: PlayerScope, command: FeedingTarget) -> Effect:
    await control.delete_record(await scope.context("god_feeding_delete"), "god_feeding", (command.god_id, command.emotion))
    return Effect("The god no longer feeds on that feeling.", command.god_id)
