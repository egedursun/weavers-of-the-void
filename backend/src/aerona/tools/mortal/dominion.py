from typing import Any

from sqlalchemy import select

from aerona.db.tables.dominion import MagicSiteRow
from aerona.domain.enums.action import ActionKind
from aerona.domain.enums.agent import AgentKind
from aerona.engine.dominion.sites import SiteTally, can_search, reveal, search_chance
from aerona.engine.primitives.distance import RegionAtlas
from aerona.prompts import MortalToolId
from aerona.prompts.tools.results import MortalResult, result
from aerona.tools.framework.call import MortalCall
from aerona.tools.framework.inputs import ToolInput
from aerona.tools.framework.spec import ToolMeta, ToolSpec, mortal_standard_action
from aerona.tools.framework.validation import fail


class SearchInput(ToolInput):
    pass


async def search_magic_sites(call: MortalCall, args: SearchInput) -> str:
    table = call.rules.magic_sites
    if not await can_search(call.tick, call.me):
        need = table.search_skill
        fail(MortalResult.SEARCH_REFUSED, why=f"you need spellcraft of {need}, or an explorer's tracking of {need}, to search for hidden magic")
    atlas = await RegionAtlas.load(call.session)
    region = atlas.top_region(call.me.id)
    hidden = [
        site
        for site in await call.session.scalars(select(MagicSiteRow).where(MagicSiteRow.found_epoch.is_(None)).order_by(MagicSiteRow.id))
        if atlas.top_region(site.place_entity_id) == region
    ]
    chances = [(await search_chance(call.tick, call.me, site), site) for site in hidden]
    seekable = [(chance, site) for chance, site in chances if chance > 0]
    if not seekable:
        return result(MortalResult.SEARCH_EMPTY)
    chance, site = max(seekable, key=lambda pair: (pair[0], -pair[1].id))
    if not call.tick.rng(f"magic_site.seek.{site.id}.{call.me.id}.{call.epoch}").chance(chance * 2):
        return result(MortalResult.SEARCH_EMPTY)
    await reveal(call.tick, site, call.me, SiteTally())
    call.target(site.place_entity_id)
    return result(MortalResult.SITE_FOUND, kind=site.kind.value.replace("_", " "), school=site.school.value.replace("_", " "), id=site.id)


def specs() -> list[ToolSpec[MortalCall, Any]]:
    return [
        ToolSpec(MortalToolId.SEARCH_MAGIC_SITES, AgentKind.MORTAL, SearchInput, ToolMeta(ActionKind.INFLUENCE, mortal_standard_action), search_magic_sites),
    ]
