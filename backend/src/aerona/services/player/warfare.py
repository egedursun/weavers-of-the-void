from pydantic import Field
from sqlalchemy import select

from aerona.core.errors import NotFoundError, ValidationFailedError
from aerona.db.tables.warfare import TributeRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.limits import PERCENT_MAX
from aerona.domain.enums.military import SpyOperation
from aerona.domain.enums.war import TributeStatus, WarEnding
from aerona.engine.phases.diplomacy import decree_alliance, decree_betrayal
from aerona.engine.phases.espionage import order_spy_operation
from aerona.engine.phases.prisoners import free_prisoner, order_ransom
from aerona.engine.phases.tribute import decree_tribute, forgive_tribute
from aerona.engine.phases.warfare import (
    bless_army,
    disband_army,
    end_war_by_decree,
    force_battle,
    grant_victory,
    incite_uprising,
    open_war_now,
    order_duel,
    raise_war_army,
)
from aerona.engine.services.community_relations import end_blood_feud
from aerona.engine.services.war import held_captive
from aerona.services.player import guards
from aerona.services.player.scope import Command, Effect, PlayerScope, player_action

DECREE_REASON = "the Creator's decree"


class WarTarget(Command):
    war_id: int


class OpenWar(Command):
    attacker_id: int
    defender_id: int
    reason: str = ""


class WarArmy(Command):
    war_id: int
    community_id: int


class ArmyTarget(Command):
    army_id: int


class ArmyBlessing(Command):
    army_id: int
    morale: int = Field(default=0, ge=-PERCENT_MAX, le=PERCENT_MAX)
    equipment: int = Field(default=0, ge=-PERCENT_MAX, le=PERCENT_MAX)
    experience: int = Field(default=0, ge=-PERCENT_MAX, le=PERCENT_MAX)


class Duel(Command):
    first_id: int
    second_id: int
    war_id: int | None = None


class Victory(Command):
    war_id: int
    victor_id: int


class EndWar(Command):
    war_id: int
    ending: WarEnding = WarEnding.PEACE


class CommunityTarget(Command):
    community_id: int


class SpyOrder(Command):
    spymaster_id: int
    target_id: int
    operation: SpyOperation


class CaptiveTarget(Command):
    captive_id: int


class Tribute(Command):
    payer_id: int
    receiver_id: int


class TributeTarget(Command):
    bond_id: int


class Betrayal(Command):
    traitor_id: int
    victim_id: int
    war: bool = False


class Marriage(Command):
    first_id: int
    second_id: int


class Feud(Command):
    first_id: int
    second_id: int


@player_action("war:battle", ActionKind.FORCE_BATTLE)
async def battle(scope: PlayerScope, command: WarTarget) -> Effect:
    report = await force_battle(await scope.context("battle"), command.war_id)
    created = (report.record.id,) if report.record is not None else ()
    return Effect(report.summary, report.winner.id, created_ids=created, values={"winner_id": report.winner.id, "loser_id": report.loser.id})


@player_action("war:open", ActionKind.DECLARE_WAR)
async def open_war(scope: PlayerScope, command: OpenWar) -> Effect:
    war = await open_war_now(await scope.context("open_war"), command.attacker_id, command.defender_id, command.reason.strip() or DECREE_REASON)
    return Effect("The war began.", war.event_entity_id, values={"war_id": war.id})


@player_action("war:army", ActionKind.RAISE_ARMY)
async def raise_army(scope: PlayerScope, command: WarArmy) -> Effect:
    army = await raise_war_army(await scope.context("raise_army"), command.war_id, command.community_id)
    return Effect(f"{army.name} was raised.", army.id, created_ids=(army.id,))


@player_action("army:disband", ActionKind.DISBAND_ARMY)
async def disband(scope: PlayerScope, command: ArmyTarget) -> Effect:
    await disband_army(await scope.context("disband_army"), command.army_id)
    return Effect("The army was disbanded.", command.army_id)


@player_action("army:bless", ActionKind.BLESS_ARMY)
async def bless(scope: PlayerScope, command: ArmyBlessing) -> Effect:
    if not (command.morale or command.equipment or command.experience):
        raise ValidationFailedError("Give the army morale, equipment or experience.")
    army = await bless_army(await scope.context("bless_army"), command.army_id, command.morale, command.equipment, command.experience)
    return Effect(f"{army.name} was strengthened by the Creator's hand.", army.id)


@player_action("war:duel", ActionKind.CHALLENGE)
async def duel(scope: PlayerScope, command: Duel) -> Effect:
    return Effect(await order_duel(await scope.context("duel"), command.first_id, command.second_id, command.war_id), command.first_id)


@player_action("war:victory", ActionKind.GRANT_VICTORY)
async def victory(scope: PlayerScope, command: Victory) -> Effect:
    settlement = await grant_victory(await scope.context("victory"), command.war_id, command.victor_id)
    return Effect(" ".join(settlement.notes) or "The war was won.", command.victor_id, values={"ending": settlement.ending.value})


@player_action("war:end", ActionKind.DIPLOMACY)
async def end_war(scope: PlayerScope, command: EndWar) -> Effect:
    settlement = await end_war_by_decree(await scope.context("end_war"), command.war_id, command.ending)
    return Effect(" ".join(settlement.notes) or "The war ended.", values={"ending": settlement.ending.value})


@player_action("community:rise_up", ActionKind.INCITE_UPRISING)
async def uprising(scope: PlayerScope, command: CommunityTarget) -> Effect:
    if not await incite_uprising(await scope.context("uprising"), command.community_id):
        raise ValidationFailedError("The uprising could not begin now.")
    return Effect("The community rose up against its rulers.", command.community_id)


@player_action("faction:spy", ActionKind.SABOTAGE)
async def spy(scope: PlayerScope, command: SpyOrder) -> Effect:
    text = await order_spy_operation(await scope.context("spy"), command.spymaster_id, command.target_id, command.operation)
    return Effect(text, command.target_id)


async def _held_row(scope: PlayerScope, captive_entity_id: int) -> int:
    row = await held_captive(scope.session, captive_entity_id)
    if row is None:
        raise NotFoundError("That record is not a held prisoner.")
    return row.id


async def _tribute_row(scope: PlayerScope, bond_id: int) -> int:
    statement = select(TributeRow.id).where(TributeRow.bond_id == bond_id, TributeRow.status == TributeStatus.ACTIVE)
    found = await scope.session.scalar(statement)
    if found is None:
        raise NotFoundError("That bond carries no active tribute.")
    return int(found)


@player_action("captive:free", ActionKind.RESCUE_CAPTIVE)
async def free(scope: PlayerScope, command: CaptiveTarget) -> Effect:
    row = await free_prisoner(await scope.context("free_prisoner"), await _held_row(scope, command.captive_id))
    return Effect("The captive was freed.", row.captive_entity_id)


@player_action("captive:ransom", ActionKind.PAY_RANSOM)
async def ransom(scope: PlayerScope, command: CaptiveTarget) -> Effect:
    row = await order_ransom(await scope.context("ransom"), await _held_row(scope, command.captive_id))
    return Effect("The ransom was paid.", row.captive_entity_id)


@player_action("tribute:impose", ActionKind.IMPOSE_TRIBUTE)
async def tribute(scope: PlayerScope, command: Tribute) -> Effect:
    row = await decree_tribute(await scope.context("tribute"), command.payer_id, command.receiver_id)
    return Effect("The tribute was imposed.", command.receiver_id, values={"tribute_id": row.id})


@player_action("tribute:forgive", ActionKind.FORGIVE_TRIBUTE)
async def forgive(scope: PlayerScope, command: TributeTarget) -> Effect:
    row = await forgive_tribute(await scope.context("forgive_tribute"), await _tribute_row(scope, command.bond_id))
    return Effect("The tribute was forgiven.", row.payer_entity_id)


@player_action("alliance:betray", ActionKind.BETRAYAL)
async def betray(scope: PlayerScope, command: Betrayal) -> Effect:
    record = await decree_betrayal(await scope.context("betrayal"), command.traitor_id, command.victim_id, command.war)
    return Effect(f"{record.name}: the alliance was betrayed.", record.id, created_ids=(record.id,))


@player_action("alliance:marriage", ActionKind.DIPLOMACY)
async def marriage(scope: PlayerScope, command: Marriage) -> Effect:
    spouses = await decree_alliance(await scope.context("marriage"), command.first_id, command.second_id, marriage=True)
    if spouses is None:
        return Effect("The alliance was sealed, but no ruling houses could be wed.", command.first_id)
    return Effect(f"{spouses[0].name} and {spouses[1].name} were wed to seal the alliance.", command.first_id, values={"spouse_id": spouses[1].id})


@player_action("feud:end", ActionKind.END_BLOOD_FEUD)
async def end_feud(scope: PlayerScope, command: Feud) -> Effect:
    first = await guards.entity(scope.session, command.first_id)
    second = await guards.entity(scope.session, command.second_id)
    if not await end_blood_feud(scope.session, first.id, second.id):
        raise ValidationFailedError(f"{first.name} and {second.name} hold no blood feud.")
    return Effect(f"The blood feud between {first.name} and {second.name} was ended.", first.id)
