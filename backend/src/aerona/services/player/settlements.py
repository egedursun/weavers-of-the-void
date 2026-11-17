from aerona.core.errors import ValidationFailedError
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.chronicle import ChronicleKind
from aerona.domain.enums.entity import EntityStatus
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.society import SocialClass
from aerona.engine.lifecycle.succession import designate_heir
from aerona.engine.phases.births import awaken_species, bless_with_child, crown_ruler, order_village, raise_notable_by_hand, trigger_ethnogenesis
from aerona.engine.phases.ruins import abandon_settlement, protect_from_ruin
from aerona.engine.phases.settlements import order_resettlement
from aerona.engine.phases.spirits import lay_spirit_to_rest
from aerona.engine.recording.record import record
from aerona.engine.records import retire_record
from aerona.services.player import guards
from aerona.services.player.scope import Command, Effect, PlayerScope, player_action
from aerona.services.wiki import designate_capital

RETIRE_REASON = "the Creator's will"


class SettlementTarget(Command):
    settlement_id: int


class RuinShelter(Command):
    settlement_id: int
    protected: bool = True


class Resettle(Command):
    ruin_id: int
    population: int
    source_id: int | None = None


class Parents(Command):
    first_id: int
    second_id: int


class Notable(Command):
    community_id: int
    social_class: SocialClass | None = None
    role_key: str | None = None


class CommunityTarget(Command):
    community_id: int


class PeopleTarget(Command):
    people_id: int


class SpeciesTarget(Command):
    species_id: int


class Heir(Command):
    ruler_id: int
    heir_id: int


class SpiritTarget(Command):
    spirit_id: int


class RetireRecord(Command):
    entity_id: int
    reason: str = ""
    status: EntityStatus = EntityStatus.DEAD


@player_action("settlement:shelter", ActionKind.SHELTER_FROM_RUIN)
async def shelter_from_ruin(scope: PlayerScope, command: RuinShelter) -> Effect:
    changed = await protect_from_ruin(await scope.context("shelter_from_ruin"), command.settlement_id, command.protected)
    state = "sheltered from ruin" if command.protected else "no longer sheltered from ruin"
    message = f"The settlement is {state}." if changed else f"The settlement was already {state}."
    return Effect(message, command.settlement_id, values={"changed": changed})


@player_action("settlement:abandon", ActionKind.ABANDON_SETTLEMENT)
async def abandon(scope: PlayerScope, command: SettlementTarget) -> Effect:
    settlement = await abandon_settlement(await scope.context("abandon_settlement"), command.settlement_id)
    return Effect(f"{settlement.name} was abandoned.", settlement.id)


@player_action("settlement:resettle", ActionKind.RESETTLE_RUIN)
async def resettle(scope: PlayerScope, command: Resettle) -> Effect:
    ruin = await order_resettlement(await scope.context("resettle"), command.ruin_id, command.source_id, command.population)
    return Effect(f"Settlers rebuilt {ruin.name}.", ruin.id)


@player_action("settlement:capital", ActionKind.EDIT_RECORD)
async def seat_capital(scope: PlayerScope, command: SettlementTarget) -> Effect:
    settlement = await guards.entity(scope.session, command.settlement_id)
    ruler = await designate_capital(scope.session, settlement, await scope.epoch())
    ctx = await scope.context("seat_capital")
    text = (
        await record(
            ctx,
            "player.settlement.capital",
            roles={IncidentRole.PLACE: settlement.id, IncidentRole.AUTHORITY: (await scope.creator()).id, IncidentRole.OWNER: ruler.id},
            place=settlement.id,
            kind=ChronicleKind.CREATOR_HAND,
        )
    ).text
    return Effect(text, settlement.id, values={"ruler_id": ruler.id})


@player_action("mortal:child", ActionKind.BEAR_CHILD)
async def bless_child(scope: PlayerScope, command: Parents) -> Effect:
    child = await bless_with_child(await scope.context("bless_child"), command.first_id, command.second_id)
    return Effect(f"{child.name} was born.", child.id, created_ids=(child.id,))


@player_action("community:notable", ActionKind.RAISE_NOTABLE)
async def raise_notable(scope: PlayerScope, command: Notable) -> Effect:
    notable = await raise_notable_by_hand(await scope.context("raise_notable"), command.community_id, command.social_class, command.role_key)
    return Effect(f"{notable.name} rose among the people.", notable.id, created_ids=(notable.id,))


@player_action("community:crown", ActionKind.CROWN_RULER)
async def crown(scope: PlayerScope, command: CommunityTarget) -> Effect:
    ruler = await crown_ruler(await scope.context("crown_ruler"), command.community_id)
    return Effect(f"{ruler.name} was crowned.", ruler.id, created_ids=(ruler.id,))


@player_action("people:village", ActionKind.FOUND_SETTLEMENT)
async def found_village(scope: PlayerScope, command: PeopleTarget) -> Effect:
    village = await order_village(await scope.context("found_village"), command.people_id)
    return Effect(f"{village.name} was founded.", village.id, created_ids=(village.id,))


@player_action("settlement:ethnogenesis", ActionKind.ETHNOGENESIS)
async def ethnogenesis(scope: PlayerScope, command: SettlementTarget) -> Effect:
    people = await trigger_ethnogenesis(await scope.context("ethnogenesis"), command.settlement_id)
    return Effect(f"A new people, {people.name}, was born.", people.id, created_ids=(people.id,))


@player_action("species:awaken", ActionKind.AWAKEN_SPECIES)
async def awaken(scope: PlayerScope, command: SpeciesTarget) -> Effect:
    people = await awaken_species(await scope.context("awaken_species"), command.species_id)
    return Effect(f"{people.name} awoke to speech and thought.", people.id, created_ids=(people.id,))


@player_action("ruler:heir", ActionKind.DESIGNATE_HEIR)
async def name_heir(scope: PlayerScope, command: Heir) -> Effect:
    row = await designate_heir(await scope.context("designate_heir"), command.ruler_id, command.heir_id)
    return Effect("The heir was named.", row.ruler_entity_id, values={"heir_id": row.heir_entity_id})


@player_action("spirit:rest", ActionKind.LAY_SPIRIT_TO_REST)
async def rest_spirit(scope: PlayerScope, command: SpiritTarget) -> Effect:
    spirit = await lay_spirit_to_rest(await scope.context("lay_spirit_to_rest"), command.spirit_id)
    return Effect(f"{spirit.name} was laid to rest.", spirit.id)


@player_action("record:retire", ActionKind.DESTROY)
async def retire(scope: PlayerScope, command: RetireRecord) -> Effect:
    if command.status is EntityStatus.CANON:
        raise ValidationFailedError("A record leaves the living world as dead, destroyed or another closing status.")
    found = await retire_record(await scope.context("retire_record"), command.entity_id, command.reason.strip() or RETIRE_REASON, command.status)
    return Effect(f"{found.name} passed out of the living world.", found.id)
