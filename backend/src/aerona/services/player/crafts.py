from aerona.core.grammar import several
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.crafts import (
    AffinityMode,
    AssistiveAid,
    CatchGround,
    CatchRight,
    ChemicalProduct,
    ClockKind,
    GameKind,
    GameRule,
    Gear,
    InsuranceCover,
    LinkToken,
    Notation,
    RightAcquired,
    RightKind,
)
from aerona.domain.enums.culture import MagicSchool
from aerona.domain.enums.mind import Emotion
from aerona.engine.crafts import control
from aerona.services.player.cosmography import Edited
from aerona.services.player.scope import Command, Effect, PlayerScope, player_action


class RunNow(Command):
    pass


class CatchGroundDraft(Command):
    source_id: int
    region_id: int
    ground: CatchGround = CatchGround.FISHERY
    gear: Gear = Gear.NETS
    right: CatchRight = CatchRight.COMMONS
    owner_node_id: int | None = None
    effort: int = 50


class CatchGroundTarget(Command):
    source_id: int
    region_id: int


class CatchGroundEdit(Edited):
    source_id: int
    region_id: int


class ChemicalWorksDraft(Command):
    settlement_id: int
    product: ChemicalProduct
    output: int = 20
    hazard: int = 10
    pollution: int = 10


class ChemicalWorksTarget(Command):
    settlement_id: int
    product: ChemicalProduct


class ChemicalWorksEdit(Edited):
    settlement_id: int
    product: ChemicalProduct


class InsurerDraft(Command):
    insurer_id: int
    pool: int = 30
    risk_belief: int = 20
    premium_pct: int = 5


class InsurerTarget(Command):
    insurer_id: int


class InsurerEdit(Edited):
    insurer_id: int


class InsurancePolicyDraft(Command):
    insurer_entity_id: int
    holder_node_id: int
    cover: InsuranceCover = InsuranceCover.CARGO
    premium: int = 1
    sum_insured: int = 20


class InsurancePolicyTarget(Command):
    record_id: int


class InsurancePolicyEdit(Edited):
    record_id: int


class IncorporealRightDraft(Command):
    holder_node_id: int
    kind: RightKind = RightKind.SONG
    subject_node_id: int | None = None
    name: str
    acquired: RightAcquired = RightAcquired.GRANTED
    licensed_to_node_id: int | None = None


class IncorporealRightTarget(Command):
    record_id: int


class IncorporealRightEdit(Edited):
    record_id: int


class AssistiveAidDraft(Command):
    holder_id: int
    kind: AssistiveAid
    quality: int = 50


class AssistiveAidTarget(Command):
    holder_id: int
    kind: AssistiveAid


class AssistiveAidEdit(Edited):
    holder_id: int
    kind: AssistiveAid


class PublicClockDraft(Command):
    settlement_id: int
    kind: ClockKind = ClockKind.SUNDIAL
    precision: int = 30


class PublicClockTarget(Command):
    settlement_id: int


class PublicClockEdit(Edited):
    settlement_id: int


class GameDraft(Command):
    name: str
    kind: GameKind = GameKind.BOARD
    rule: GameRule = GameRule.STRATEGY
    origin_entity_id: int | None = None


class GameTarget(Command):
    record_id: int


class GameEdit(Edited):
    record_id: int


class GameFollowingDraft(Command):
    people_id: int
    game_id: int
    popularity: int = 30


class GameFollowingTarget(Command):
    people_id: int
    game_id: int


class GameFollowingEdit(Edited):
    people_id: int
    game_id: int


class NumberSystemDraft(Command):
    people_id: int
    base: int = 10
    notation: Notation = Notation.ADDITIVE
    zero: bool = False
    numeracy: int = 20


class NumberSystemTarget(Command):
    people_id: int


class NumberSystemEdit(Edited):
    people_id: int


class MaterialAffinityDraft(Command):
    material_id: int
    school: MagicSchool
    mode: AffinityMode = AffinityMode.WORN
    power: int = 30


class MaterialAffinityTarget(Command):
    material_id: int
    school: MagicSchool


class MaterialAffinityEdit(Edited):
    material_id: int
    school: MagicSchool


class SympatheticLinkDraft(Command):
    holder_node_id: int
    target_node_id: int
    token: LinkToken = LinkToken.HAIR
    strength: int = 50


class SympatheticLinkTarget(Command):
    record_id: int


class SympatheticLinkEdit(Edited):
    record_id: int


class EmotionSpiritDraft(Command):
    region_entity_id: int
    emotion: Emotion = Emotion.JOY
    strength: int = 30
    lifetime: int = 3
    bound_by_node_id: int | None = None


class EmotionSpiritTarget(Command):
    record_id: int


class EmotionSpiritEdit(Edited):
    record_id: int


@player_action("catch_ground:set", ActionKind.EDIT_RECORD)
async def catch_ground_set(scope: PlayerScope, command: CatchGroundDraft) -> Effect:
    row = await control.set_record(
        await scope.context("catch_ground_set"),
        "catch_ground",
        {"source_entity_id": command.source_id, "region_entity_id": command.region_id},
        {"ground": command.ground, "gear": command.gear, "right": command.right, "owner_node_id": command.owner_node_id, "effort": command.effort},
    )
    return Effect("The ground is worked so.", values={"record_id": getattr(row, "id", 0)})


@player_action("catch_ground:edit", ActionKind.EDIT_RECORD)
async def catch_ground_edit(scope: PlayerScope, command: CatchGroundEdit) -> Effect:
    await control.edit_record(await scope.context("catch_ground_edit"), "catch_ground", (command.source_id, command.region_id), command.values, command.release)
    return Effect("The ground is set so.")


@player_action("catch_ground:delete", ActionKind.EDIT_RECORD)
async def catch_ground_delete(scope: PlayerScope, command: CatchGroundTarget) -> Effect:
    await control.delete_record(await scope.context("catch_ground_delete"), "catch_ground", (command.source_id, command.region_id))
    return Effect("The ground is struck from the record.")


@player_action("chemical_works:set", ActionKind.EDIT_RECORD)
async def chemical_works_set(scope: PlayerScope, command: ChemicalWorksDraft) -> Effect:
    row = await control.set_record(
        await scope.context("chemical_works_set"),
        "chemical_works",
        {"settlement_entity_id": command.settlement_id, "product": command.product},
        {"output": command.output, "hazard": command.hazard, "pollution": command.pollution},
    )
    return Effect("The works are set up.", values={"record_id": getattr(row, "id", 0)})


@player_action("chemical_works:edit", ActionKind.EDIT_RECORD)
async def chemical_works_edit(scope: PlayerScope, command: ChemicalWorksEdit) -> Effect:
    await control.edit_record(
        await scope.context("chemical_works_edit"), "chemical_works", (command.settlement_id, command.product), command.values, command.release
    )
    return Effect("The works are set so.")


@player_action("chemical_works:delete", ActionKind.EDIT_RECORD)
async def chemical_works_delete(scope: PlayerScope, command: ChemicalWorksTarget) -> Effect:
    await control.delete_record(await scope.context("chemical_works_delete"), "chemical_works", (command.settlement_id, command.product))
    return Effect("The works are pulled down.")


@player_action("insurer:set", ActionKind.EDIT_RECORD)
async def insurer_set(scope: PlayerScope, command: InsurerDraft) -> Effect:
    row = await control.set_record(
        await scope.context("insurer_set"),
        "insurer",
        {"insurer_entity_id": command.insurer_id},
        {"pool": command.pool, "risk_belief": command.risk_belief, "premium_pct": command.premium_pct},
    )
    return Effect("It insures from now on.", values={"record_id": getattr(row, "id", 0)})


@player_action("insurer:edit", ActionKind.EDIT_RECORD)
async def insurer_edit(scope: PlayerScope, command: InsurerEdit) -> Effect:
    await control.edit_record(await scope.context("insurer_edit"), "insurer", command.insurer_id, command.values, command.release)
    return Effect("The insurer is set so.")


@player_action("insurer:delete", ActionKind.EDIT_RECORD)
async def insurer_delete(scope: PlayerScope, command: InsurerTarget) -> Effect:
    await control.delete_record(await scope.context("insurer_delete"), "insurer", command.insurer_id)
    return Effect("It insures no more.")


@player_action("insurance_policy:create", ActionKind.EDIT_RECORD)
async def insurance_policy_create(scope: PlayerScope, command: InsurancePolicyDraft) -> Effect:
    row = await control.set_record(
        await scope.context("insurance_policy_create"),
        "insurance_policy",
        {},
        {
            "insurer_entity_id": command.insurer_entity_id,
            "holder_node_id": command.holder_node_id,
            "cover": command.cover,
            "premium": command.premium,
            "sum_insured": command.sum_insured,
        },
    )
    return Effect("The policy is written.", values={"record_id": getattr(row, "id", 0)})


@player_action("insurance_policy:edit", ActionKind.EDIT_RECORD)
async def insurance_policy_edit(scope: PlayerScope, command: InsurancePolicyEdit) -> Effect:
    await control.edit_record(await scope.context("insurance_policy_edit"), "insurance_policy", command.record_id, command.values, command.release)
    return Effect("The policy is set so.")


@player_action("insurance_policy:delete", ActionKind.EDIT_RECORD)
async def insurance_policy_delete(scope: PlayerScope, command: InsurancePolicyTarget) -> Effect:
    await control.delete_record(await scope.context("insurance_policy_delete"), "insurance_policy", command.record_id)
    return Effect("The policy is torn up.")


@player_action("incorporeal_right:create", ActionKind.EDIT_RECORD)
async def incorporeal_right_create(scope: PlayerScope, command: IncorporealRightDraft) -> Effect:
    row = await control.set_record(
        await scope.context("incorporeal_right_create"),
        "incorporeal_right",
        {},
        {
            "holder_node_id": command.holder_node_id,
            "kind": command.kind,
            "subject_node_id": command.subject_node_id,
            "name": command.name,
            "acquired": command.acquired,
            "licensed_to_node_id": command.licensed_to_node_id,
        },
    )
    return Effect("The right is held.", values={"record_id": getattr(row, "id", 0)})


@player_action("incorporeal_right:edit", ActionKind.EDIT_RECORD)
async def incorporeal_right_edit(scope: PlayerScope, command: IncorporealRightEdit) -> Effect:
    await control.edit_record(await scope.context("incorporeal_right_edit"), "incorporeal_right", command.record_id, command.values, command.release)
    return Effect("The right is set so.")


@player_action("incorporeal_right:delete", ActionKind.EDIT_RECORD)
async def incorporeal_right_delete(scope: PlayerScope, command: IncorporealRightTarget) -> Effect:
    await control.delete_record(await scope.context("incorporeal_right_delete"), "incorporeal_right", command.record_id)
    return Effect("The right is struck.")


@player_action("assistive_aid:set", ActionKind.EDIT_RECORD)
async def assistive_aid_set(scope: PlayerScope, command: AssistiveAidDraft) -> Effect:
    row = await control.set_record(
        await scope.context("assistive_aid_set"), "assistive_aid", {"holder_node_id": command.holder_id, "kind": command.kind}, {"quality": command.quality}
    )
    return Effect("The aid is given.", values={"record_id": getattr(row, "id", 0)})


@player_action("assistive_aid:edit", ActionKind.EDIT_RECORD)
async def assistive_aid_edit(scope: PlayerScope, command: AssistiveAidEdit) -> Effect:
    await control.edit_record(await scope.context("assistive_aid_edit"), "assistive_aid", (command.holder_id, command.kind), command.values, command.release)
    return Effect("The aid is set so.")


@player_action("assistive_aid:delete", ActionKind.EDIT_RECORD)
async def assistive_aid_delete(scope: PlayerScope, command: AssistiveAidTarget) -> Effect:
    await control.delete_record(await scope.context("assistive_aid_delete"), "assistive_aid", (command.holder_id, command.kind))
    return Effect("The aid is taken away.")


@player_action("public_clock:set", ActionKind.EDIT_RECORD)
async def public_clock_set(scope: PlayerScope, command: PublicClockDraft) -> Effect:
    row = await control.set_record(
        await scope.context("public_clock_set"),
        "public_clock",
        {"settlement_entity_id": command.settlement_id},
        {"kind": command.kind, "precision": command.precision},
    )
    return Effect("The town keeps its hours.", values={"record_id": getattr(row, "id", 0)})


@player_action("public_clock:edit", ActionKind.EDIT_RECORD)
async def public_clock_edit(scope: PlayerScope, command: PublicClockEdit) -> Effect:
    await control.edit_record(await scope.context("public_clock_edit"), "public_clock", command.settlement_id, command.values, command.release)
    return Effect("The clock is set so.")


@player_action("public_clock:delete", ActionKind.EDIT_RECORD)
async def public_clock_delete(scope: PlayerScope, command: PublicClockTarget) -> Effect:
    await control.delete_record(await scope.context("public_clock_delete"), "public_clock", command.settlement_id)
    return Effect("The clock is taken down.")


@player_action("game:create", ActionKind.EDIT_RECORD)
async def game_create(scope: PlayerScope, command: GameDraft) -> Effect:
    row = await control.set_record(
        await scope.context("game_create"),
        "game",
        {},
        {"name": command.name, "kind": command.kind, "rule": command.rule, "origin_entity_id": command.origin_entity_id},
    )
    return Effect("The game is played.", values={"record_id": getattr(row, "id", 0)})


@player_action("game:edit", ActionKind.EDIT_RECORD)
async def game_edit(scope: PlayerScope, command: GameEdit) -> Effect:
    await control.edit_record(await scope.context("game_edit"), "game", command.record_id, command.values, command.release)
    return Effect("The game is set so.")


@player_action("game:delete", ActionKind.EDIT_RECORD)
async def game_delete(scope: PlayerScope, command: GameTarget) -> Effect:
    await control.delete_record(await scope.context("game_delete"), "game", command.record_id)
    return Effect("The game is forgotten.")


@player_action("game_following:set", ActionKind.EDIT_RECORD)
async def game_following_set(scope: PlayerScope, command: GameFollowingDraft) -> Effect:
    row = await control.set_record(
        await scope.context("game_following_set"),
        "game_following",
        {"people_entity_id": command.people_id, "game_id": command.game_id},
        {"popularity": command.popularity},
    )
    return Effect("The people take up the game.", values={"record_id": getattr(row, "id", 0)})


@player_action("game_following:edit", ActionKind.EDIT_RECORD)
async def game_following_edit(scope: PlayerScope, command: GameFollowingEdit) -> Effect:
    await control.edit_record(
        await scope.context("game_following_edit"), "game_following", (command.people_id, command.game_id), command.values, command.release
    )
    return Effect("The following is set so.")


@player_action("game_following:delete", ActionKind.EDIT_RECORD)
async def game_following_delete(scope: PlayerScope, command: GameFollowingTarget) -> Effect:
    await control.delete_record(await scope.context("game_following_delete"), "game_following", (command.people_id, command.game_id))
    return Effect("The people leave the game.")


@player_action("number_system:set", ActionKind.EDIT_RECORD)
async def number_system_set(scope: PlayerScope, command: NumberSystemDraft) -> Effect:
    row = await control.set_record(
        await scope.context("number_system_set"),
        "number_system",
        {"people_entity_id": command.people_id},
        {"base": command.base, "notation": command.notation, "zero": command.zero, "numeracy": command.numeracy},
    )
    return Effect("The people count so.", values={"record_id": getattr(row, "id", 0)})


@player_action("number_system:edit", ActionKind.EDIT_RECORD)
async def number_system_edit(scope: PlayerScope, command: NumberSystemEdit) -> Effect:
    await control.edit_record(await scope.context("number_system_edit"), "number_system", command.people_id, command.values, command.release)
    return Effect("The number system is set so.")


@player_action("number_system:delete", ActionKind.EDIT_RECORD)
async def number_system_delete(scope: PlayerScope, command: NumberSystemTarget) -> Effect:
    await control.delete_record(await scope.context("number_system_delete"), "number_system", command.people_id)
    return Effect("The number system is struck.")


@player_action("material_affinity:set", ActionKind.EDIT_RECORD)
async def material_affinity_set(scope: PlayerScope, command: MaterialAffinityDraft) -> Effect:
    row = await control.set_record(
        await scope.context("material_affinity_set"),
        "material_affinity",
        {"material_id": command.material_id, "school": command.school},
        {"mode": command.mode, "power": command.power},
    )
    return Effect("The material carries the affinity.", values={"record_id": getattr(row, "id", 0)})


@player_action("material_affinity:edit", ActionKind.EDIT_RECORD)
async def material_affinity_edit(scope: PlayerScope, command: MaterialAffinityEdit) -> Effect:
    await control.edit_record(
        await scope.context("material_affinity_edit"), "material_affinity", (command.material_id, command.school), command.values, command.release
    )
    return Effect("The affinity is set so.")


@player_action("material_affinity:delete", ActionKind.EDIT_RECORD)
async def material_affinity_delete(scope: PlayerScope, command: MaterialAffinityTarget) -> Effect:
    await control.delete_record(await scope.context("material_affinity_delete"), "material_affinity", (command.material_id, command.school))
    return Effect("The affinity is struck.")


@player_action("sympathetic_link:create", ActionKind.EDIT_RECORD)
async def sympathetic_link_create(scope: PlayerScope, command: SympatheticLinkDraft) -> Effect:
    row = await control.set_record(
        await scope.context("sympathetic_link_create"),
        "sympathetic_link",
        {},
        {"holder_node_id": command.holder_node_id, "target_node_id": command.target_node_id, "token": command.token, "strength": command.strength},
    )
    return Effect("The link is made.", values={"record_id": getattr(row, "id", 0)})


@player_action("sympathetic_link:edit", ActionKind.EDIT_RECORD)
async def sympathetic_link_edit(scope: PlayerScope, command: SympatheticLinkEdit) -> Effect:
    await control.edit_record(await scope.context("sympathetic_link_edit"), "sympathetic_link", command.record_id, command.values, command.release)
    return Effect("The link is set so.")


@player_action("sympathetic_link:delete", ActionKind.EDIT_RECORD)
async def sympathetic_link_delete(scope: PlayerScope, command: SympatheticLinkTarget) -> Effect:
    await control.delete_record(await scope.context("sympathetic_link_delete"), "sympathetic_link", command.record_id)
    return Effect("The link is broken.")


@player_action("emotion_spirit:create", ActionKind.EDIT_RECORD)
async def emotion_spirit_create(scope: PlayerScope, command: EmotionSpiritDraft) -> Effect:
    row = await control.set_record(
        await scope.context("emotion_spirit_create"),
        "emotion_spirit",
        {},
        {
            "region_entity_id": command.region_entity_id,
            "emotion": command.emotion,
            "strength": command.strength,
            "lifetime": command.lifetime,
            "bound_by_node_id": command.bound_by_node_id,
        },
    )
    return Effect("The spirit takes shape.", values={"record_id": getattr(row, "id", 0)})


@player_action("emotion_spirit:edit", ActionKind.EDIT_RECORD)
async def emotion_spirit_edit(scope: PlayerScope, command: EmotionSpiritEdit) -> Effect:
    await control.edit_record(await scope.context("emotion_spirit_edit"), "emotion_spirit", command.record_id, command.values, command.release)
    return Effect("The spirit is set so.")


@player_action("emotion_spirit:delete", ActionKind.EDIT_RECORD)
async def emotion_spirit_delete(scope: PlayerScope, command: EmotionSpiritTarget) -> Effect:
    await control.delete_record(await scope.context("emotion_spirit_delete"), "emotion_spirit", command.record_id)
    return Effect("The spirit is dispersed.")


@player_action("trades:run", ActionKind.EDIT_RECORD)
async def trades_run(scope: PlayerScope, command: RunNow) -> Effect:
    tally = await control.run_trades(await scope.context("trades_run"))
    told = [
        several(tally.grounds.read, "ground", "grounds") + " read",
        several(tally.chemistry.founded, "works", "works") + " set up",
        several(tally.insurance.written, "policy", "policies") + " written",
        several(tally.rights.claimed, "right", "rights") + " claimed",
        several(tally.clocks.built, "clock", "clocks") + " set up",
    ]
    return Effect("; ".join(told) + ".")


@player_action("learning_aids:run", ActionKind.EDIT_RECORD)
async def learning_aids_run(scope: PlayerScope, command: RunNow) -> Effect:
    tally = await control.run_learning(await scope.context("learning_aids_run"))
    told = [
        several(tally.aids.fitted, "aid", "aids") + " given",
        several(tally.games.invented, "game", "games") + " invented",
        several(tally.numbers.milestones, "step", "steps") + " in reckoning",
    ]
    return Effect("; ".join(told) + ".")


@player_action("sympathies:run", ActionKind.EDIT_RECORD)
async def sympathies_run(scope: PlayerScope, command: RunNow) -> Effect:
    tally = await control.run_sympathies(await scope.context("sympathies_run"))
    told = [
        several(tally.sympathy.affinities, "affinity", "affinities") + " found",
        several(tally.sympathy.taken, "link", "links") + " taken",
        several(tally.spirits.born, "spirit", "spirits") + " born",
    ]
    return Effect("; ".join(told) + ".")
