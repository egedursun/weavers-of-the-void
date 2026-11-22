from typing import Any

from pydantic import Field
from sqlalchemy import select

from aerona.catalog.life_traits import GATHERING_KIND_TRAITS, having
from aerona.core.grammar import several, spoken
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.gatherings import GatheringRow
from aerona.db.tables.polity import OfficeRow
from aerona.db.tables.sites import ExcavationRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.domain.enums.gathering import AttendanceReason, GatheringKind, GatheringStatus, GuestRole
from aerona.domain.enums.life_traits import GatheringKindTrait
from aerona.domain.enums.mind import SkillKind
from aerona.domain.enums.polity import OfficeKind
from aerona.domain.enums.site import ExcavationStatus
from aerona.engine.gatherings.hold import plan
from aerona.engine.gatherings.occasions import Guest, Occasion
from aerona.engine.mind.book import skill_level
from aerona.engine.renown.currencies import realm_of_community
from aerona.engine.sites.digs import begin, diggable, wrecked
from aerona.engine.sites.rooms import delve, layout_of, rooms_of
from aerona.prompts import MortalToolId
from aerona.prompts.tools.results import MortalResult, result
from aerona.tools.framework.call import MortalCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, mortal_standard_action
from aerona.tools.framework.validation import fail, require_canon

GUESTS_MAX = 12
RULER_KINDS = having(GATHERING_KIND_TRAITS, GatheringKindTrait.RULER_KINDS)
ENGINE_KINDS = having(GATHERING_KIND_TRAITS, GatheringKindTrait.ENGINE_KINDS)


class HoldGatheringInput(ToolInput):
    kind: GatheringKind
    guest_ids: list[int] = Field(default_factory=list, max_length=GUESTS_MAX)


class SiteInput(ToolInput):
    site_id: int


async def hold_gathering(call: MortalCall, args: HoldGatheringInput) -> str:
    if args.kind in ENGINE_KINDS:
        fail(MortalResult.GATHERING_REFUSED, why="that gathering comes only when the world calls for it")
    if args.kind in RULER_KINDS:
        rules = await call.session.scalar(
            select(OfficeRow.polity_entity_id).where(OfficeRow.holder_entity_id == call.me.id, OfficeRow.kind == OfficeKind.RULER).limit(1)
        )
        if rules is None:
            fail(MortalResult.GATHERING_REFUSED, why="only a ruler calls that")
    planned = await call.session.scalar(
        select(GatheringRow.id).where(GatheringRow.host_node_id == call.me.id, GatheringRow.status == GatheringStatus.PLANNED).limit(1)
    )
    if planned is not None:
        fail(MortalResult.GATHERING_REFUSED, why="you already have a gathering planned")
    guests = [Guest((await require_canon(call.session, guest)).id, GuestRole.GUEST, AttendanceReason.FRIEND) for guest in args.guest_ids if guest != call.me.id]
    occasion = Occasion(args.kind, call.me.id, call.me.world_id, call.me.location_id, guests=guests)
    row = await plan(call.tick, occasion)
    if row is None:
        fail(MortalResult.GATHERING_REFUSED, why="a god holds you against change")
    return result(MortalResult.GATHERING_PLANNED, kind=spoken(args.kind), guests=len(guests))


async def delve_site(call: MortalCall, args: SiteInput) -> str:
    site = await require_canon(call.session, args.site_id)
    if await layout_of(call.tick, site) is None and not await rooms_of(call.tick, site.id):
        fail(MortalResult.DELVE_REFUSED, why=f"{site.name} has no rooms to walk")
    walk = await delve(call.tick, call.me, site)
    call.target(site.id)
    told = "you reached its heart" if walk.reached_heart else f"you cleared {several(walk.cleared, 'room', 'rooms')}"
    return result(MortalResult.SITE_DELVED, site=site.name, told=told, found=len(walk.loot))


async def dig_site(call: MortalCall, args: SiteInput) -> str:
    found = await call.session.get(EntityRow, args.site_id)
    site = found if found is not None and await wrecked(call.session, found.id) else await require_canon(call.session, args.site_id)
    if not await diggable(call.session, site):
        fail(MortalResult.DIG_REFUSED, why=f"{site.name} holds nothing old enough to dig")
    lore = await skill_level(call.session, call.me.id, SkillKind.LORE)
    if lore < call.rules.excavations.start_lore:
        fail(MortalResult.DIG_REFUSED, why=f"you need lore of {call.rules.excavations.start_lore} to lead a dig")
    open_dig = await call.session.scalar(
        select(ExcavationRow.id)
        .where(ExcavationRow.site_entity_id == site.id, ExcavationRow.status.in_([ExcavationStatus.OPEN, ExcavationStatus.STALLED]))
        .limit(1)
    )
    if open_dig is not None:
        fail(MortalResult.DIG_REFUSED, why=f"a dig is already open at {site.name}")
    sponsor = await realm_of_community(call.session, call.me.location_id) if call.me.location_id is not None else None
    dig = await begin(call.tick, site, call.me, sponsor)
    call.target(site.id)
    return result(MortalResult.DIG_BEGUN, site=site.name, id=dig.id)


def specs() -> list[ToolSpec[MortalCall, Any]]:
    return [
        ToolSpec(MortalToolId.HOLD_GATHERING, AgentKind.MORTAL, HoldGatheringInput, ToolMeta(ActionKind.INFLUENCE, mortal_standard_action), hold_gathering),
        ToolSpec(MortalToolId.DELVE_SITE, AgentKind.MORTAL, SiteInput, ToolMeta(ActionKind.INFLUENCE, mortal_standard_action), delve_site),
        ToolSpec(MortalToolId.DIG_SITE, AgentKind.MORTAL, SiteInput, ToolMeta(ActionKind.INFLUENCE, mortal_standard_action), dig_site),
    ]
