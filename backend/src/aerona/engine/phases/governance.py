from sqlalchemy import select

from aerona.db.fast_session import rows_by_id
from aerona.db.tables.entities import EntityRow
from aerona.db.tables.estates import CompanyProfileRow
from aerona.db.tables.governance import OrgGovernanceRow
from aerona.db.write_guard import held
from aerona.domain.enums.entity import EntityStatus
from aerona.engine.context import TickContext
from aerona.engine.governance.cliques import tend_cliques
from aerona.engine.governance.heads import govern
from aerona.engine.governance.insolvency import InsolvencyTally, file_case, tend_insolvency
from aerona.engine.governance.mergers import advance_merger, open_bids
from aerona.engine.governance.research import tend_research
from aerona.engine.governance.seats import seed_governance
from aerona.engine.governance.strategy import follow_strategy, set_course
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.phase import Phase


async def file_failing(ctx: TickContext, tally: InsolvencyTally) -> None:
    floor = ctx.rules.companies.collapse_wealth
    for row in list(await ctx.session.scalars(select(CompanyProfileRow).where(CompanyProfileRow.value < floor).order_by(CompanyProfileRow.faction_entity_id))):
        company = await ctx.session.get(EntityRow, row.faction_entity_id)
        if company is not None and company.status is EntityStatus.CANON and not held(company.id):
            await file_case(ctx, company, None, tally)


@reads(
    "faction.strength",
    "faction.sway",
    "faction.wealth",
    "mortal.charisma",
    "mortal.intellect",
    "mortal.wisdom",
    "table.bonds",
    "table.company_profiles",
    "table.company_shares",
    "table.entities",
    "table.faction_memberships",
    "table.faction_profiles",
    "table.holder_levels",
    "table.holder_techniques",
    "table.incident_participants",
    "table.incidents",
    "table.insolvency_cases",
    "table.issued_securities",
    "table.mortal_profiles",
    "table.name_registry",
    "table.node_births",
    "table.nodes",
    "table.org_cliques",
    "table.org_governance",
    "table.org_mergers",
    "table.org_research",
    "table.org_seats",
    "table.polity_members",
)
@writes(
    "faction.strength",
    "faction.sway",
    "faction.wealth",
    "table.applied_fixups",
    "table.bonds",
    "table.chronicle",
    "table.chronicle_entities",
    "table.entities",
    "table.faction_memberships",
    "table.faction_profiles",
    "table.incident_facts",
    "table.incident_participants",
    "table.incidents",
    "table.name_registry",
    "table.node_births",
    "table.org_cliques",
    "table.org_governance",
    "table.org_mergers",
    "table.org_seats",
)
async def governance(ctx: TickContext) -> None:
    seeded = await seed_governance(ctx)
    ctx.count("governance_bodies", seeded.bodies)
    chosen = defied = removed = formed = split = done = leaked = acted = courses = 0
    rows = list(await ctx.session.scalars(select(OrgGovernanceRow).order_by(OrgGovernanceRow.org_node_id)))
    orgs = await rows_by_id(ctx.session, EntityRow, [row.org_node_id for row in rows])
    for row in rows:
        org = orgs.get(row.org_node_id)
        if org is None or org.status is not EntityStatus.CANON or held(org.id):
            continue
        head, defiance, removal = await govern(ctx, row)
        chosen, defied, removed = chosen + head, defied + defiance, removed + removal
        made, gone = await tend_cliques(ctx, row)
        formed, split = formed + made, split + gone
        courses += await set_course(ctx, row, org)
        acted += 1 if await follow_strategy(ctx, row, org) is not None else 0
        finished, spread = await tend_research(ctx, org)
        done, leaked = done + finished, leaked + spread
    outcomes = [await advance_merger(ctx, merger) for merger in await open_bids(ctx)]
    tally = InsolvencyTally()
    await file_failing(ctx, tally)
    await tend_insolvency(ctx, tally)
    for key, value in {
        "governance_heads_chosen": chosen,
        "governance_defied": defied,
        "governance_heads_removed": removed,
        "governance_cliques_formed": formed,
        "governance_splits": split,
        "governance_strategy_acts": acted,
        "governance_courses_set": courses,
        "governance_research_done": done,
        "governance_secrets_leaked": leaked,
        "governance_mergers_closed": outcomes.count("closed"),
        "governance_mergers_blocked": outcomes.count("blocked"),
        "governance_mergers_resisted": outcomes.count("resisted"),
        **{f"insolvency_{name}": value for name, value in vars(tally).items()},
    }.items():
        ctx.count(key, value)


PHASES = (Phase("governance", governance),)
