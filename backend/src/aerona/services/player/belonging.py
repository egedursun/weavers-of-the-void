from aerona.core.grammar import several
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.belonging import FugitiveKind, IdentityLayer, PlayKind, SalienceDriver, SanctuaryKind, SanctuaryState, SatireSource
from aerona.domain.enums.society import SocialClass
from aerona.engine.belonging import control
from aerona.services.player.cosmography import Edited
from aerona.services.player.scope import Command, Effect, PlayerScope, player_action


class RunNow(Command):
    pass


class HeldIdentityDraft(Command):
    holder_id: int
    layer: IdentityLayer
    value_node_id: int | None = None
    value_label: str | None = None
    strength: int = 50
    salience: int = 30
    driver: SalienceDriver = SalienceDriver.GOD


class HeldIdentityTarget(Command):
    holder_id: int
    layer: IdentityLayer


class HeldIdentityEdit(Edited):
    holder_id: int
    layer: IdentityLayer


class PeerGroupDraft(Command):
    settlement_entity_id: int
    social_class: SocialClass = SocialClass.FARMER
    play: PlayKind = PlayKind.GAMES
    children: int = 0
    cohesion: int = 40
    deprived: bool = False


class PeerGroupTarget(Command):
    record_id: int


class PeerGroupEdit(Edited):
    record_id: int


class PeerMemberDraft(Command):
    group_id: int
    mortal_id: int
    deprived_epochs: int = 0


class PeerMemberTarget(Command):
    group_id: int
    mortal_id: int


class PeerMemberEdit(Edited):
    group_id: int
    mortal_id: int


class FugitiveDraft(Command):
    mortal_entity_id: int
    kind: FugitiveKind = FugitiveKind.OUTLAW
    pursuer_entity_id: int | None = None


class FugitiveTarget(Command):
    record_id: int


class FugitiveEdit(Edited):
    record_id: int


class SanctuaryDraft(Command):
    fugitive_entity_id: int
    host_entity_id: int
    kind: SanctuaryKind = SanctuaryKind.TEMPLE
    fugitive_kind: FugitiveKind = FugitiveKind.OUTLAW
    pursuer_entity_id: int | None = None
    state: SanctuaryState = SanctuaryState.SHELTERED
    fee: int = 0
    siege_epochs: int = 0


class SanctuaryTarget(Command):
    record_id: int


class SanctuaryEdit(Edited):
    record_id: int


class SanctuaryLawDraft(Command):
    polity_id: int
    restricted: bool = False
    fee_pct: int = 0


class SanctuaryLawTarget(Command):
    polity_id: int


class SanctuaryLawEdit(Edited):
    polity_id: int


class SatireDraft(Command):
    satirist_entity_id: int | None = None
    target_entity_id: int
    polity_entity_id: int | None = None
    work_entity_id: int | None = None
    source: SatireSource = SatireSource.GOD
    bite: int = 20
    tolerated: bool = True
    punished: bool = False


class SatireTarget(Command):
    record_id: int


class SatireEdit(Edited):
    record_id: int


@player_action("held_identity:set", ActionKind.EDIT_RECORD)
async def held_identity_set(scope: PlayerScope, command: HeldIdentityDraft) -> Effect:
    row = await control.set_record(
        await scope.context("held_identity_set"),
        "held_identity",
        {"holder_entity_id": command.holder_id, "layer": command.layer},
        {
            "value_node_id": command.value_node_id,
            "value_label": command.value_label,
            "strength": command.strength,
            "salience": command.salience,
            "driver": command.driver,
        },
    )
    return Effect("The identity is held so.", values={"record_id": getattr(row, "id", 0)})


@player_action("held_identity:edit", ActionKind.EDIT_RECORD)
async def held_identity_edit(scope: PlayerScope, command: HeldIdentityEdit) -> Effect:
    await control.edit_record(await scope.context("held_identity_edit"), "held_identity", (command.holder_id, command.layer), command.values, command.release)
    return Effect("The identity is set so.")


@player_action("held_identity:delete", ActionKind.EDIT_RECORD)
async def held_identity_delete(scope: PlayerScope, command: HeldIdentityTarget) -> Effect:
    await control.delete_record(await scope.context("held_identity_delete"), "held_identity", (command.holder_id, command.layer))
    return Effect("The identity is let go.")


@player_action("peer_group:create", ActionKind.EDIT_RECORD)
async def peer_group_create(scope: PlayerScope, command: PeerGroupDraft) -> Effect:
    row = await control.set_record(
        await scope.context("peer_group_create"),
        "peer_group",
        {},
        {
            "settlement_entity_id": command.settlement_entity_id,
            "social_class": command.social_class,
            "play": command.play,
            "children": command.children,
            "cohesion": command.cohesion,
            "deprived": command.deprived,
        },
    )
    return Effect("The children of the town gather to play.", values={"record_id": getattr(row, "id", 0)})


@player_action("peer_group:edit", ActionKind.EDIT_RECORD)
async def peer_group_edit(scope: PlayerScope, command: PeerGroupEdit) -> Effect:
    await control.edit_record(await scope.context("peer_group_edit"), "peer_group", command.record_id, command.values, command.release)
    return Effect("The peer group is set so.")


@player_action("peer_group:delete", ActionKind.EDIT_RECORD)
async def peer_group_delete(scope: PlayerScope, command: PeerGroupTarget) -> Effect:
    await control.delete_record(await scope.context("peer_group_delete"), "peer_group", command.record_id)
    return Effect("The peer group breaks up.")


@player_action("peer_member:set", ActionKind.EDIT_RECORD)
async def peer_member_set(scope: PlayerScope, command: PeerMemberDraft) -> Effect:
    row = await control.set_record(
        await scope.context("peer_member_set"),
        "peer_member",
        {"group_id": command.group_id, "mortal_entity_id": command.mortal_id},
        {"deprived_epochs": command.deprived_epochs},
    )
    return Effect("The child joins the group.", values={"record_id": getattr(row, "id", 0)})


@player_action("peer_member:edit", ActionKind.EDIT_RECORD)
async def peer_member_edit(scope: PlayerScope, command: PeerMemberEdit) -> Effect:
    await control.edit_record(await scope.context("peer_member_edit"), "peer_member", (command.group_id, command.mortal_id), command.values, command.release)
    return Effect("The member is set so.")


@player_action("peer_member:delete", ActionKind.EDIT_RECORD)
async def peer_member_delete(scope: PlayerScope, command: PeerMemberTarget) -> Effect:
    await control.delete_record(await scope.context("peer_member_delete"), "peer_member", (command.group_id, command.mortal_id))
    return Effect("The child leaves the group.")


@player_action("fugitive:create", ActionKind.EDIT_RECORD)
async def fugitive_create(scope: PlayerScope, command: FugitiveDraft) -> Effect:
    ctx = await scope.context("fugitive_create")
    row = await control.set_record(
        ctx,
        "fugitive",
        {},
        {"mortal_entity_id": command.mortal_entity_id, "kind": command.kind, "pursuer_entity_id": command.pursuer_entity_id, "fled_epoch": ctx.epoch},
    )
    return Effect("The mortal flees.", values={"record_id": getattr(row, "id", 0)})


@player_action("fugitive:edit", ActionKind.EDIT_RECORD)
async def fugitive_edit(scope: PlayerScope, command: FugitiveEdit) -> Effect:
    await control.edit_record(await scope.context("fugitive_edit"), "fugitive", command.record_id, command.values, command.release)
    return Effect("The flight is set so.")


@player_action("fugitive:delete", ActionKind.EDIT_RECORD)
async def fugitive_delete(scope: PlayerScope, command: FugitiveTarget) -> Effect:
    await control.delete_record(await scope.context("fugitive_delete"), "fugitive", command.record_id)
    return Effect("No one hunts them any more.")


@player_action("sanctuary:create", ActionKind.EDIT_RECORD)
async def sanctuary_create(scope: PlayerScope, command: SanctuaryDraft) -> Effect:
    row = await control.set_record(
        await scope.context("sanctuary_create"),
        "sanctuary",
        {},
        {
            "fugitive_entity_id": command.fugitive_entity_id,
            "host_entity_id": command.host_entity_id,
            "kind": command.kind,
            "fugitive_kind": command.fugitive_kind,
            "pursuer_entity_id": command.pursuer_entity_id,
            "state": command.state,
            "fee": command.fee,
            "siege_epochs": command.siege_epochs,
        },
    )
    return Effect("The fugitive is sheltered.", values={"record_id": getattr(row, "id", 0)})


@player_action("sanctuary:edit", ActionKind.EDIT_RECORD)
async def sanctuary_edit(scope: PlayerScope, command: SanctuaryEdit) -> Effect:
    await control.edit_record(await scope.context("sanctuary_edit"), "sanctuary", command.record_id, command.values, command.release)
    return Effect("The sanctuary is set so.")


@player_action("sanctuary:delete", ActionKind.EDIT_RECORD)
async def sanctuary_delete(scope: PlayerScope, command: SanctuaryTarget) -> Effect:
    await control.delete_record(await scope.context("sanctuary_delete"), "sanctuary", command.record_id)
    return Effect("The sanctuary ends.")


@player_action("sanctuary_law:set", ActionKind.EDIT_RECORD)
async def sanctuary_law_set(scope: PlayerScope, command: SanctuaryLawDraft) -> Effect:
    row = await control.set_record(
        await scope.context("sanctuary_law_set"),
        "sanctuary_law",
        {"polity_entity_id": command.polity_id},
        {"restricted": command.restricted, "fee_pct": command.fee_pct},
    )
    return Effect("The realm's law of sanctuary is set.", values={"record_id": getattr(row, "id", 0)})


@player_action("sanctuary_law:edit", ActionKind.EDIT_RECORD)
async def sanctuary_law_edit(scope: PlayerScope, command: SanctuaryLawEdit) -> Effect:
    await control.edit_record(await scope.context("sanctuary_law_edit"), "sanctuary_law", command.polity_id, command.values, command.release)
    return Effect("The law of sanctuary is set so.")


@player_action("sanctuary_law:delete", ActionKind.EDIT_RECORD)
async def sanctuary_law_delete(scope: PlayerScope, command: SanctuaryLawTarget) -> Effect:
    await control.delete_record(await scope.context("sanctuary_law_delete"), "sanctuary_law", command.polity_id)
    return Effect("The law of sanctuary is struck.")


@player_action("satire:create", ActionKind.EDIT_RECORD)
async def satire_create(scope: PlayerScope, command: SatireDraft) -> Effect:
    row = await control.set_record(
        await scope.context("satire_create"),
        "satire",
        {},
        {
            "satirist_entity_id": command.satirist_entity_id,
            "target_entity_id": command.target_entity_id,
            "polity_entity_id": command.polity_entity_id,
            "work_entity_id": command.work_entity_id,
            "source": command.source,
            "bite": command.bite,
            "tolerated": command.tolerated,
            "punished": command.punished,
        },
    )
    return Effect("The satire is told.", values={"record_id": getattr(row, "id", 0)})


@player_action("satire:edit", ActionKind.EDIT_RECORD)
async def satire_edit(scope: PlayerScope, command: SatireEdit) -> Effect:
    await control.edit_record(await scope.context("satire_edit"), "satire", command.record_id, command.values, command.release)
    return Effect("The satire is set so.")


@player_action("satire:delete", ActionKind.EDIT_RECORD)
async def satire_delete(scope: PlayerScope, command: SatireTarget) -> Effect:
    await control.delete_record(await scope.context("satire_delete"), "satire", command.record_id)
    return Effect("The satire is forgotten.")


@player_action("belonging:run", ActionKind.EDIT_RECORD)
async def belonging_run(scope: PlayerScope, command: RunNow) -> Effect:
    tally = await control.run_belonging(await scope.context("belonging_run"))
    told = [
        several(tally.identities.communities, "community", "communities") + " read for who they are",
        several(tally.identities.stirred, "identity stirred", "identities stirred"),
        several(tally.peers.groups, "peer group", "peer groups") + " at play",
        several(tally.peers.friendships, "childhood friendship", "childhood friendships"),
    ]
    return Effect("; ".join(told) + ".")


@player_action("sanctuary:run", ActionKind.EDIT_RECORD)
async def sanctuary_run(scope: PlayerScope, command: RunNow) -> Effect:
    tally = await control.run_sanctuary(await scope.context("sanctuary_run"))
    told = [
        several(tally.sought, "fugitive", "fugitives") + " claimed sanctuary",
        several(tally.asylums, "asylum given", "asylums given"),
        several(tally.besieged, "refuge besieged", "refuges besieged"),
        several(tally.violated, "sanctuary broken", "sanctuaries broken"),
    ]
    return Effect("; ".join(told) + ".")


@player_action("satire:run", ActionKind.EDIT_RECORD)
async def satire_run(scope: PlayerScope, command: RunNow) -> Effect:
    tally = await control.run_satire(await scope.context("satire_run"))
    told = [
        several(tally.jests, "jest", "jests") + " at court",
        several(tally.works, "satirical work", "satirical works"),
        several(tally.tolerated, "satire tolerated", "satires tolerated"),
        several(tally.punished, "satirist punished", "satirists punished"),
    ]
    return Effect("; ".join(told) + ".")
