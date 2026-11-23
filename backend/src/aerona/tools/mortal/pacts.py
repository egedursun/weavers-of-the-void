from typing import Any

from sqlalchemy import select

from aerona.catalog.pacts import CONTESTABLE_CLAIMS, ENVOY_FATES, PRINCIPAL_ROLES, RESOLUTIONS
from aerona.catalog.statecraft import RESOLUTION_TEXT
from aerona.core.grammar import spoken
from aerona.db.tables.affairs import ResolutionRow
from aerona.db.tables.communication import SignalLinkRow
from aerona.db.tables.lore import MessageRow
from aerona.db.tables.polity import TreatyProfileRow
from aerona.db.tables.renown import DeedClaimRow, DeedRow
from aerona.db.tables.statecraft import CrisisRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.modifier import IncidentRole
from aerona.domain.enums.renown import ClaimKind, ClaimStatus
from aerona.domain.enums.statecraft import ResolutionKind
from aerona.engine.communication.dispatches import expel
from aerona.engine.communication.signals import jam
from aerona.engine.polity.accords import parties_of
from aerona.engine.polity.assembly import assemblies, members_of
from aerona.engine.polity.book import Realm, RealmBook
from aerona.engine.polity.mediation import declare_neutral, join_as_mediator, mediate_crisis, suspend_treaty
from aerona.engine.primitives.distance import RegionAtlas
from aerona.engine.renown.claims import dispute, lay_claim
from aerona.prompts import MortalToolId
from aerona.prompts.tools.results import MortalResult, result
from aerona.tools.framework.call import MortalCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, mortal_standard_action
from aerona.tools.framework.validation import fail
from aerona.tools.mortal.ruler import throne_of


class MediateInput(ToolInput):
    treaty_id: int | None = None
    crisis_id: int | None = None


class TreatyInput(ToolInput):
    treaty_id: int


class NeutralInput(ToolInput):
    pass


class ResolutionInput(ToolInput):
    kind: ResolutionKind
    target_id: int | None = None


class EnvoyInput(ToolInput):
    envoy_id: int


class JamInput(ToolInput):
    link_id: int


class ClaimDeedInput(ToolInput):
    deed_id: int
    kind: ClaimKind = ClaimKind.SHARED
    contest: bool = False


def seat_of(realm: Realm) -> int:
    return realm.profile.core_entity_id or realm.entity.id


async def mediate(call: MortalCall, args: MediateInput) -> str:
    realm = await throne_of(call)
    book = await RealmBook.load(call.session)
    if args.crisis_id is not None:
        crisis = await call.session.get(CrisisRow, args.crisis_id)
        if crisis is None or not await mediate_crisis(call.tick, book, crisis, realm.entity.id):
            fail(MortalResult.MEDIATION_REFUSED, why="there is no open crisis between two other realms that you can settle, or it is held")
        call.target(crisis.demander_entity_id)
        await call.record("tools.mortal.mediate", roles={IncidentRole.ACTOR: call.me.id, IncidentRole.SUBJECT: crisis.demander_entity_id})
        return result(MortalResult.MEDIATED, what="the crisis")
    profile = await call.session.get(TreatyProfileRow, args.treaty_id) if args.treaty_id is not None else None
    if profile is None or not await join_as_mediator(call.tick, profile, seat_of(realm)):
        fail(MortalResult.MEDIATION_REFUSED, why="there is no treaty in force between others that you can stand behind, or it is held")
    call.target(profile.treaty_entity_id)
    await call.record("tools.mortal.mediate", roles={IncidentRole.ACTOR: call.me.id, IncidentRole.SUBJECT: profile.treaty_entity_id})
    return result(MortalResult.MEDIATED, what="the treaty")


async def suspend(call: MortalCall, args: TreatyInput) -> str:
    realm = await throne_of(call)
    profile = await call.session.get(TreatyProfileRow, args.treaty_id)
    mine = {seat_of(realm), realm.entity.id}
    parties = await parties_of(call.session, args.treaty_id) if profile is not None else []
    party = next((row.party_node_id for row in parties if row.party_node_id in mine and row.role in PRINCIPAL_ROLES), None)
    if profile is None or party is None:
        fail(MortalResult.SUSPENSION_REFUSED, why="your realm is not a party to that treaty")
    if not await suspend_treaty(call.tick, profile, party, "its ruler held it in abeyance"):
        fail(MortalResult.SUSPENSION_REFUSED, why="the treaty is not in force, or it is held")
    call.target(profile.treaty_entity_id)
    await call.record("tools.mortal.suspend_treaty", roles={IncidentRole.ACTOR: call.me.id, IncidentRole.SUBJECT: profile.treaty_entity_id})
    return result(MortalResult.TREATY_SUSPENDED, loss=call.rules.treaties.suspension_trust_loss)


async def go_neutral(call: MortalCall, args: NeutralInput) -> str:
    realm = await throne_of(call)
    if not await declare_neutral(call.tick, realm):
        fail(MortalResult.NEUTRALITY_REFUSED, why="your realm is neutral already, or its standing is held")
    call.target(realm.entity.id)
    await call.record("tools.mortal.declare_neutral", roles={IncidentRole.ACTOR: call.me.id, IncidentRole.SUBJECT: realm.entity.id})
    return result(MortalResult.NEUTRALITY_DECLARED, realm=realm.entity.name)


async def propose(call: MortalCall, args: ResolutionInput) -> str:
    realm = await throne_of(call)
    mine = {seat_of(realm), realm.entity.id}
    council = None
    for assembly in await assemblies(call.tick):
        if mine & {member.id for member in await members_of(call.tick, assembly.id)}:
            council = assembly
            break
    if council is None:
        fail(MortalResult.RESOLUTION_REFUSED, why="your realm sits on no council of worlds")
    if RESOLUTIONS[args.kind].needs_target and args.target_id is None:
        fail(MortalResult.RESOLUTION_REFUSED, why="that resolution needs what it is about")
    row = ResolutionRow(assembly_entity_id=council.id, kind=args.kind, target_node_id=args.target_id, proposed_epoch=call.epoch, locked=[])
    call.session.add(row)
    await call.session.flush()
    call.target(council.id)
    await call.record(
        "tools.mortal.propose_resolution",
        roles={IncidentRole.ACTOR: call.me.id, IncidentRole.AUTHORITY: council.id, IncidentRole.TARGET: args.target_id},
        facts={"kind": args.kind},
    )
    return result(MortalResult.RESOLUTION_PROPOSED, council=council.name, resolution=RESOLUTION_TEXT[args.kind])


async def expel_envoy(call: MortalCall, args: EnvoyInput) -> str:
    realm = await throne_of(call)
    book = await RealmBook.load(call.session)
    rows = await call.session.scalars(
        select(MessageRow).where(MessageRow.envoy_node_id == args.envoy_id, MessageRow.envoy_fate.is_not(None)).order_by(MessageRow.id.desc())
    )
    staying = [row for row in rows if row.envoy_fate is not None and not ENVOY_FATES[row.envoy_fate].harmed and ENVOY_FATES[row.envoy_fate].goes_home]
    found = next((row for row in staying if (host := book.realm_for(row.recipient_node_id)) is not None and host.entity.id == realm.entity.id), None)
    if found is None or not await expel(call.tick, found, call.me.id):
        fail(MortalResult.EXPULSION_REFUSED, why="no envoy of that name stays at your court, or it is held")
    call.target(args.envoy_id)
    await call.record("tools.mortal.expel_envoy", roles={IncidentRole.ACTOR: call.me.id, IncidentRole.ENVOY: args.envoy_id})
    return result(MortalResult.ENVOY_EXPELLED)


async def jam_signal(call: MortalCall, args: JamInput) -> str:
    link = await call.session.get(SignalLinkRow, args.link_id)
    atlas = await RegionAtlas.load(call.session)
    here = atlas.top_region(call.me.id)
    if link is None or here not in (link.from_region_id, link.to_region_id):
        fail(MortalResult.JAMMING_REFUSED, why="no such station stands in your land")
    if not await jam(call.tick, link, call.me.id):
        fail(MortalResult.JAMMING_REFUSED, why="that station carries nothing now, or it is held")
    call.target(link.owner_node_id)
    await call.record("tools.mortal.jam_signal", roles={IncidentRole.ACTOR: call.me.id, IncidentRole.OWNER: link.owner_node_id})
    return result(MortalResult.SIGNAL_JAMMED, station=spoken(link.kind))


async def claim_deed(call: MortalCall, args: ClaimDeedInput) -> str:
    deed = await call.session.get(DeedRow, args.deed_id)
    if deed is None:
        fail(MortalResult.CLAIM_REFUSED, why="there is no such deed")
    if args.contest:
        rival = await call.session.scalar(
            select(DeedClaimRow)
            .where(
                DeedClaimRow.deed_id == deed.id,
                DeedClaimRow.claimant_node_id != call.me.id,
                DeedClaimRow.kind.in_(list(CONTESTABLE_CLAIMS)),
                DeedClaimRow.status == ClaimStatus.STANDING,
            )
            .order_by(DeedClaimRow.id)
            .limit(1)
        )
        if rival is None or not await dispute(call.tick, rival, call.me.id):
            fail(MortalResult.CLAIM_REFUSED, why="no claim to that deed stands for you to dispute, or it is held")
        kind = rival.kind
    else:
        row = await lay_claim(call.tick, deed, call.me.id, args.kind)
        if row is None:
            fail(MortalResult.CLAIM_REFUSED, why="your claim to that deed stands already, or your own course is held")
        kind = args.kind
    call.target(deed.doer_node_id)
    await call.record("tools.mortal.claim_deed", roles={IncidentRole.ACTOR: call.me.id, IncidentRole.VICTIM: deed.doer_node_id}, facts={"claim": kind})
    return result(MortalResult.DEED_CLAIMED, claim=spoken(kind), contested=args.contest)


def specs() -> list[ToolSpec[MortalCall, Any]]:
    meta = ToolMeta(ActionKind.INFLUENCE, mortal_standard_action)
    return [
        ToolSpec(MortalToolId.MEDIATE, AgentKind.MORTAL, MediateInput, meta, mediate),
        ToolSpec(MortalToolId.SUSPEND_TREATY, AgentKind.MORTAL, TreatyInput, meta, suspend),
        ToolSpec(MortalToolId.DECLARE_NEUTRAL, AgentKind.MORTAL, NeutralInput, meta, go_neutral),
        ToolSpec(MortalToolId.PROPOSE_RESOLUTION, AgentKind.MORTAL, ResolutionInput, meta, propose),
        ToolSpec(MortalToolId.EXPEL_ENVOY, AgentKind.MORTAL, EnvoyInput, meta, expel_envoy),
        ToolSpec(MortalToolId.JAM_SIGNAL, AgentKind.MORTAL, JamInput, meta, jam_signal),
        ToolSpec(MortalToolId.CLAIM_DEED, AgentKind.MORTAL, ClaimDeedInput, meta, claim_deed),
    ]
