from aerona.engine.context import TickContext
from aerona.engine.interconnect.annotations import reads, writes
from aerona.engine.kin.duties import KinTally, keep_duties
from aerona.engine.kin.groups import GroupTally, keep_groups
from aerona.engine.kin.seed import seed_kin
from aerona.engine.phase import Phase


@reads(
    "table.bonds",
    "table.community_relations",
    "table.creator",
    "table.culture_values",
    "table.dimensions",
    "table.entities",
    "table.foreign_gods",
    "table.galaxies",
    "table.galaxy_clusters",
    "table.house_members",
    "table.house_profiles",
    "table.household_members",
    "table.kin_group_members",
    "table.kin_groups",
    "table.kin_role_duties",
    "table.kinship_systems",
    "table.memories",
    "table.mortal_profiles",
    "table.node_births",
    "table.nodes",
    "table.personality_values",
    "table.relation_components",
    "table.sons",
    "table.stars",
    "table.state_changes",
    "table.title_holders",
    "table.title_profiles",
    "table.traits",
    "table.worlds",
)
@writes(
    "table.bonds",
    "table.chronicle",
    "table.chronicle_entities",
    "table.community_relations",
    "table.entities",
    "table.household_members",
    "table.incident_facts",
    "table.incident_participants",
    "table.incident_steps",
    "table.incidents",
    "table.kin_group_members",
    "table.kin_groups",
    "table.kin_role_duties",
    "table.memories",
    "table.mortal_profiles",
    "table.relation_components",
)
async def kin_duties(ctx: TickContext) -> None:
    seeded = await seed_kin(ctx)
    ctx.count("kin_seeded_duties", seeded.duties)
    ctx.count("kin_seeded_groups", seeded.groups)
    ctx.count("kin_seeded_members", seeded.members)
    tally = KinTally()
    await keep_duties(ctx, tally)
    ctx.count("kin_helped", tally.helped)
    ctx.count("kin_breached", tally.breached)
    ctx.count("kin_fostered", tally.fostered)
    ctx.count("kin_mourned", tally.mourned)
    ctx.count("kin_avenged", tally.avenged)
    ctx.count("kin_closeness", tally.closeness)
    groups = GroupTally()
    await keep_groups(ctx, groups)
    ctx.count("kin_heads", groups.heads)
    ctx.count("kin_splits", groups.splits)
    ctx.count("kin_land_shares", groups.shares)


PHASES = (Phase("kin_duties", kin_duties),)
