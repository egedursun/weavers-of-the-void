from aerona.engine.context import TickContext
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.phase import Phase
from aerona.engine.polity.titles import TitleTally, tend_titles


@reads(
    "table.bonds",
    "table.de_jure_links",
    "table.epoch_year_cursors",
    "table.item_profiles",
    "table.law_jurisdictions",
    "table.name_registry",
    "table.offices",
    "table.polity_members",
    "table.polity_profiles",
    "table.polity_territories",
    "table.ruler_currencies",
    "table.title_holders",
    "table.title_profiles",
    "table.vassalages",
    "table.world_maps",
)
@writes(
    "table.chronicle",
    "table.chronicle_entities",
    "table.claims",
    "table.de_jure_links",
    "table.entities",
    "table.epoch_year_cursors",
    "table.incident_participants",
    "table.incidents",
    "table.name_registry",
    "table.offices",
    "table.polity_members",
    "table.polity_profiles",
    "table.polity_territories",
    "table.ruler_currencies",
    "table.title_holders",
    "table.title_profiles",
)
async def titles(ctx: TickContext) -> None:
    tally = TitleTally()
    await tend_titles(ctx, tally)
    for key, value in vars(tally).items():
        ctx.count(f"titles_{key}", value)


PHASES = (Phase("titles", titles),)
