from pydantic import Field

from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.polity import ClaimBasis, ClauseKind, LawKind, LegitimacyBasis, OathKind, OfficeKind, PartyRole, TreatyKind, TreatyStatus
from aerona.engine.polity import control
from aerona.services.player.scope import Command, Effect, PlayerScope, player_action


class EditPolity(Command):
    polity_id: int
    values: dict[str, int | str | bool | None] = Field(default_factory=dict)
    release: list[str] = Field(default_factory=list)


class Appoint(Command):
    polity_id: int
    office: OfficeKind
    mortal_id: int | None = None
    region_id: int | None = None


class PolityTarget(Command):
    polity_id: int


class Split(Command):
    polity_id: int
    member_ids: list[int] = Field(min_length=1)


class Merge(Command):
    polity_id: int
    into_id: int


class EnactLaw(Command):
    holder_id: int
    kind: LawKind
    params: dict[str, int | str | bool] = Field(default_factory=dict)
    name: str | None = Field(default=None, max_length=120)
    enforcement: int | None = Field(default=None, ge=0, le=100)
    basis: LegitimacyBasis | None = None
    hold: list[str] = Field(default_factory=list)


class LawTarget(Command):
    law_id: int


class EditLaw(Command):
    law_id: int
    params: dict[str, int | str | bool] = Field(default_factory=dict)
    enforcement: int | None = Field(default=None, ge=0, le=100)
    basis: LegitimacyBasis | None = None
    name: str | None = Field(default=None, max_length=120)
    holder_ids: list[int] | None = None
    release: list[str] = Field(default_factory=list)
    kind: LawKind | None = None
    conflict: int | None = Field(default=None, ge=0, le=100)


class ProtectLaw(Command):
    law_id: int
    hold: list[str] = Field(default_factory=list)
    release: list[str] = Field(default_factory=list)


class FoundHouse(Command):
    mortal_id: int


class MergeHouse(Command):
    house_id: int
    into_id: int


class HouseTarget(Command):
    house_id: int


class GrantClaim(Command):
    mortal_id: int
    polity_id: int
    strength: int = Field(default=50, ge=0, le=100)
    basis: ClaimBasis = ClaimBasis.DIVINE


class TreatyParty(Command):
    party_id: int
    role: PartyRole = PartyRole.SIGNATORY


class TreatyClause(Command):
    kind: ClauseKind
    obligor_id: int | None = None
    beneficiary_id: int | None = None
    params: dict[str, int | str | bool] = Field(default_factory=dict)


class SignTreaty(Command):
    kind: TreatyKind
    parties: list[TreatyParty] = Field(min_length=2)
    clauses: list[TreatyClause] = Field(default_factory=list)
    epochs: int | None = Field(default=None, ge=1, le=1000)


class BreakTreaty(Command):
    treaty_id: int
    breaker_id: int


class EditTreaty(Command):
    treaty_id: int
    until_epoch: int | None = None
    status: TreatyStatus | None = None


class SwearOath(Command):
    swearer_id: int
    kind: OathKind
    recipient_id: int | None = None


class OathTarget(Command):
    oath_id: int


@player_action("polity:edit", ActionKind.EDIT_RECORD)
async def edit_polity(scope: PlayerScope, command: EditPolity) -> Effect:
    found = await control.edit_polity(await scope.context("polity_edit"), command.polity_id, command.values, release=command.release)
    return Effect(f"{found.entity.name}: a {found.profile.government.value.replace('_', ' ')}, legitimacy {found.profile.legitimacy}.", command.polity_id)


@player_action("polity:appoint", ActionKind.EDIT_RECORD)
async def appoint(scope: PlayerScope, command: Appoint) -> Effect:
    await control.appoint_office(await scope.context("polity_appoint"), command.polity_id, command.office, command.mortal_id, region_id=command.region_id)
    label = command.office.value.replace("_", " ")
    return Effect(f"The {label} is appointed." if command.mortal_id is not None else f"The {label}'s seat stands empty.", command.polity_id)


@player_action("polity:depose", ActionKind.OTHER)
async def depose(scope: PlayerScope, command: PolityTarget) -> Effect:
    heir = await control.depose(await scope.context("polity_depose"), command.polity_id)
    return Effect(f"The ruler was cast down; {heir.name} takes the throne." if heir is not None else "The ruler was cast down.", command.polity_id)


@player_action("polity:split", ActionKind.OTHER)
async def split(scope: PlayerScope, command: Split) -> Effect:
    moved = await control.split(await scope.context("polity_split"), command.polity_id, command.member_ids)
    return Effect(f"{moved} lands broke from the realm and stand alone.", command.polity_id)


@player_action("polity:merge", ActionKind.OTHER)
async def merge(scope: PlayerScope, command: Merge) -> Effect:
    await control.merge(await scope.context("polity_merge"), command.polity_id, command.into_id)
    return Effect("The two realms are one.", command.into_id)


@player_action("polity:independence", ActionKind.OTHER)
async def independence(scope: PlayerScope, command: PolityTarget) -> Effect:
    await control.grant_independence(await scope.context("polity_independence"), command.polity_id)
    return Effect("The realm owes no one tribute or fealty now.", command.polity_id)


@player_action("law:enact", ActionKind.CREATE_ENTITY)
async def enact_law(scope: PlayerScope, command: EnactLaw) -> Effect:
    law = await control.enact_law(
        await scope.context("law_enact"),
        command.holder_id,
        command.kind,
        command.params,
        name=command.name,
        enforcement=command.enforcement,
        basis=command.basis,
        hold=command.hold,
    )
    return Effect(f"{law.name} is the law.", command.holder_id, created_ids=(law.id,))


@player_action("law:protect", ActionKind.EDIT_RECORD)
async def protect_law(scope: PlayerScope, command: ProtectLaw) -> Effect:
    profile = await control.protect_law(await scope.context("law_protect"), command.law_id, hold=command.hold, release=command.release)
    held = ", ".join(profile.locked) or "nothing"
    return Effect(f"The law now holds fast on: {held}.", command.law_id)


@player_action("law:repeal", ActionKind.OTHER)
async def repeal_law(scope: PlayerScope, command: LawTarget) -> Effect:
    law = await control.repeal_law(await scope.context("law_repeal"), command.law_id)
    return Effect(f"{law.name} is repealed.", law.id)


@player_action("law:edit", ActionKind.EDIT_RECORD)
async def edit_law(scope: PlayerScope, command: EditLaw) -> Effect:
    profile = await control.change_law(
        await scope.context("law_edit"),
        command.law_id,
        command.params,
        enforcement=command.enforcement,
        basis=command.basis,
        name=command.name,
        holder_ids=command.holder_ids,
        release=command.release,
        kind=command.kind,
        conflict=command.conflict,
    )
    return Effect(f"The law now reads as you set it, enforced at {profile.enforcement}.", command.law_id)


@player_action("house:found", ActionKind.CREATE_ENTITY)
async def found_house(scope: PlayerScope, command: FoundHouse) -> Effect:
    house = await control.found_house_by_hand(await scope.context("house_found"), command.mortal_id)
    return Effect(f"{house.name} is founded.", command.mortal_id, created_ids=(house.id,))


@player_action("house:merge", ActionKind.OTHER)
async def merge_house(scope: PlayerScope, command: MergeHouse) -> Effect:
    moved = await control.merge_houses(await scope.context("house_merge"), command.house_id, command.into_id)
    return Effect(f"{moved} kin joined the greater house.", command.into_id)


@player_action("house:extinguish", ActionKind.OTHER)
async def extinguish_house(scope: PlayerScope, command: HouseTarget) -> Effect:
    await control.end_house(await scope.context("house_extinguish"), command.house_id)
    return Effect("The house's name is struck from memory.", command.house_id)


@player_action("claim:grant", ActionKind.OTHER)
async def grant_claim(scope: PlayerScope, command: GrantClaim) -> Effect:
    await control.grant_claim(await scope.context("claim_grant"), command.mortal_id, command.polity_id, strength=command.strength, basis=command.basis)
    return Effect("A claim to the throne is granted.", command.mortal_id)


@player_action("treaty:sign", ActionKind.CREATE_ENTITY)
async def sign_treaty(scope: PlayerScope, command: SignTreaty) -> Effect:
    treaty = await control.sign_treaty(
        await scope.context("treaty_sign"),
        command.kind,
        [(party.party_id, party.role) for party in command.parties],
        [(clause.kind, clause.obligor_id, clause.beneficiary_id, clause.params) for clause in command.clauses],
        epochs=command.epochs,
    )
    return Effect(f"{treaty.name} is sealed.", command.parties[0].party_id, created_ids=(treaty.id,))


@player_action("treaty:break", ActionKind.OTHER)
async def break_treaty(scope: PlayerScope, command: BreakTreaty) -> Effect:
    await control.break_treaty(await scope.context("treaty_break"), command.treaty_id, command.breaker_id)
    return Effect("The treaty is broken.", command.treaty_id)


@player_action("treaty:edit", ActionKind.EDIT_RECORD)
async def edit_treaty(scope: PlayerScope, command: EditTreaty) -> Effect:
    profile = await control.edit_treaty(await scope.context("treaty_edit"), command.treaty_id, until_epoch=command.until_epoch, status=command.status)
    return Effect(f"The treaty is {profile.status.value.replace('_', ' ')}.", command.treaty_id)


@player_action("oath:swear", ActionKind.OTHER)
async def swear_oath(scope: PlayerScope, command: SwearOath) -> Effect:
    await control.swear_oath(await scope.context("oath_swear"), command.swearer_id, command.kind, command.recipient_id)
    return Effect(f"The {command.kind.value.replace('_', ' ')} oath is sworn.", command.swearer_id)


@player_action("oath:break", ActionKind.OTHER)
async def break_oath(scope: PlayerScope, command: OathTarget) -> Effect:
    oath = await control.break_oath_by_hand(await scope.context("oath_break"), command.oath_id)
    return Effect("The oath is broken.", oath.swearer_entity_id)
